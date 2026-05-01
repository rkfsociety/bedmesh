package com.rkfsociety.bedmesh.core

import android.content.Context
import net.schmizz.sshj.sftp.SFTPClient
import java.io.File

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
        return withSshTransport(cfg) { ssh ->
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
}
