package com.rkfsociety.bedmesh.core

import android.content.Context
import net.schmizz.sshj.SSHClient
import net.schmizz.sshj.common.IOUtils
import net.schmizz.sshj.sftp.SFTPClient
import net.schmizz.sshj.transport.verification.PromiscuousVerifier
import java.io.File
import java.util.concurrent.TimeUnit

data class SshConfig(
    val ip: String,
    val port: Int = 2222,
    val user: String = "root",
    val password: String = "rockchip",
    val path: String = "/userdata/app/gk/printer.cfg",
)

object SshClient {
    /**
     * Downloads remote file to app cache dir and returns local File.
     * Host key verification is permissive (like AutoAddPolicy in paramiko).
     */
    fun downloadFile(context: Context, cfg: SshConfig, remotePath: String = cfg.path): File {
        val ssh = SSHClient()
        ssh.addHostKeyVerifier(PromiscuousVerifier())
        ssh.connect(cfg.ip, cfg.port)
        try {
            ssh.authPassword(cfg.user, cfg.password)
            ssh.connection.keepAlive.keepAliveInterval = 10

            val sftp: SFTPClient = ssh.newSFTPClient()
            try {
                val safeName = remotePath.substringAfterLast("/").ifBlank { "download.cfg" }
                val target = File(context.cacheDir, "download_$safeName")
                sftp.get(remotePath, target.absolutePath)
                return target
            } finally {
                try {
                    sftp.close()
                } catch (_: Exception) {
                }
            }
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

    fun exec(context: Context, cfg: SshConfig, command: String): Pair<Int, String> {
        val ssh = SSHClient()
        ssh.addHostKeyVerifier(PromiscuousVerifier())
        ssh.connect(cfg.ip, cfg.port)
        try {
            ssh.authPassword(cfg.user, cfg.password)
            ssh.connection.keepAlive.keepAliveInterval = 10
            ssh.startSession().use { session ->
                val cmd = session.exec(command)
                val out = IOUtils.readFully(cmd.inputStream).toString(Charsets.UTF_8)
                cmd.join(15, TimeUnit.SECONDS)
                val status = cmd.exitStatus ?: -1
                return status to out
            }
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
}

