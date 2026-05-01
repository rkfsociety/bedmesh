package com.rkfsociety.bedmesh.core

import net.schmizz.sshj.SSHClient
import net.schmizz.sshj.transport.verification.PromiscuousVerifier
import java.io.IOException
import java.net.Inet4Address
import java.net.InetAddress

internal fun <T> withSshTransport(cfg: SshConfig, block: (SSHClient) -> T): T {
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

private fun resolveAddresses(host: String): List<InetAddress> {
    val all = InetAddress.getAllByName(host).toList()
    return all.sortedWith(compareBy<InetAddress> { it !is Inet4Address }.thenBy { it.hostAddress })
}
