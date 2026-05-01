package com.rkfsociety.bedmesh.core

import android.content.Context
import net.schmizz.sshj.SSHClient
import net.schmizz.sshj.common.IOUtils
import net.schmizz.sshj.sftp.SFTPClient
import net.schmizz.sshj.transport.verification.PromiscuousVerifier
import java.io.File
import java.io.IOException
import java.net.Inet4Address
import java.net.InetAddress
import java.util.concurrent.TimeUnit

data class SshConfig(
    val ip: String,
    val port: Int = 2222,
    val user: String = "root",
    val password: String = "rockchip",
    val path: String = "/userdata/app/gk/printer.cfg",
)

object SshClient {
    private fun resolveAddresses(host: String): List<InetAddress> {
        val all = InetAddress.getAllByName(host).toList()
        // На Android/Java резолв может вернуть IPv6 первым. Для принтеров/роутеров часто работает только IPv4.
        return all.sortedWith(compareBy<InetAddress> { it !is Inet4Address }.thenBy { it.hostAddress })
    }

    private fun <T> withSsh(cfg: SshConfig, block: (SSHClient) -> T): T {
        val addresses = resolveAddresses(cfg.ip)
        val failures = mutableListOf<String>()

        for (addr in addresses) {
            val ssh = SSHClient()
            try {
                ssh.addHostKeyVerifier(PromiscuousVerifier())
                ssh.connect(addr, cfg.port)
                ssh.authPassword(cfg.user, cfg.password)
                ssh.connection.keepAlive.keepAliveInterval = 10
                return block(ssh)
            } catch (e: Exception) {
                failures += "${addr.hostAddress}: ${e.javaClass.simpleName}${e.message?.let { ": $it" } ?: ""}"
            } finally {
                try {
                    ssh.disconnect()
                } catch (_: Exception) {
                }
                try {
                    ssh.close()
                } catch (_: Exception) {
                }
            }
        }

        throw IOException(
            buildString {
                append("Не удалось подключиться к ").append(cfg.ip).append(":").append(cfg.port)
                append(". Попробованные адреса:\n")
                append(failures.joinToString("\n"))
            },
        )
    }

    /**
     * Downloads remote file to app cache dir and returns local File.
     * Host key verification is permissive (like AutoAddPolicy in paramiko).
     */
    fun downloadFile(context: Context, cfg: SshConfig, remotePath: String = cfg.path): File {
        return withSsh(cfg) { ssh ->
            val sftp: SFTPClient = ssh.newSFTPClient()
            try {
                val safeName = remotePath.substringAfterLast("/").ifBlank { "download.cfg" }
                val target = File(context.cacheDir, "download_$safeName")
                sftp.get(remotePath, target.absolutePath)
                target
            } finally {
                try {
                    sftp.close()
                } catch (_: Exception) {
                }
            }
        }
    }

    fun exec(context: Context, cfg: SshConfig, command: String): Pair<Int, String> {
        return withSsh(cfg) { ssh ->
            ssh.startSession().use { session ->
                val cmd = session.exec(command)
                val out = IOUtils.readFully(cmd.inputStream).toString(Charsets.UTF_8)
                cmd.join(15, TimeUnit.SECONDS)
                val status = cmd.exitStatus ?: -1
                status to out
            }
        }
    }
}

