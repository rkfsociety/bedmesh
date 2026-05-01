package com.rkfsociety.bedmesh.core

import net.schmizz.sshj.sftp.RemoteResourceInfo
import java.io.File
import java.security.MessageDigest

object SshBackups {
    private const val BACKUP_TAG = "bedmesh_bak"

    private fun shQuote(s: String): String = "'" + s.replace("'", "'\"'\"'") + "'"

    fun listBackups(cfg: SshConfig): List<String> {
        return withSshTransport(cfg) { ssh ->
            val dir = cfg.path.substringBeforeLast("/", missingDelimiterValue = "")
                .ifBlank { "/" }
            val base = cfg.path.substringAfterLast("/")
            val prefix = "${base}.${BACKUP_TAG}_"

            ssh.newSFTPClient().use { sftp ->
                val items: List<RemoteResourceInfo> = sftp.ls(dir)
                items
                    .filter { it.name.startsWith(prefix) }
                    .map {
                        val full = dir.trimEnd('/') + "/" + it.name
                        val mtime = it.attributes.mtime
                        full to mtime
                    }
                    .sortedByDescending { it.second }
                    .map { it.first }
            }
        }
    }

    fun createBackup(cfg: SshConfig): String? {
        return withSshTransport(cfg) { ssh ->
            val ts = java.time.LocalDateTime.now()
                .format(java.time.format.DateTimeFormatter.ofPattern("yyyyMMdd_HHmmss"))
            val backupPath = "${cfg.path}.${BACKUP_TAG}_$ts"
            ssh.startSession().use { session ->
                val cmd = session.exec("cp ${shQuote(cfg.path)} ${shQuote(backupPath)}")
                cmd.join()
                val status = cmd.exitStatus ?: -1
                if (status != 0) return@withSshTransport null
            }
            backupPath
        }
    }

    fun restoreBackup(cfg: SshConfig, backupPath: String): Boolean {
        return withSshTransport(cfg) { ssh ->
            ssh.startSession().use { session ->
                val cmd = session.exec("cp ${shQuote(backupPath)} ${shQuote(cfg.path)}")
                cmd.join()
                (cmd.exitStatus ?: -1) == 0
            }
        }
    }

    fun deleteBackup(cfg: SshConfig, backupPath: String): Boolean {
        return withSshTransport(cfg) { ssh ->
            ssh.startSession().use { session ->
                val cmd = session.exec("rm -f ${shQuote(backupPath)}")
                cmd.join()
                (cmd.exitStatus ?: -1) == 0
            }
        }
    }

    fun uploadWithVerify(cfg: SshConfig, localFile: File, tempDir: File): Boolean {
        val localSha = sha256(localFile.readBytes())
        return withSshTransport(cfg) { ssh ->
            ssh.newSFTPClient().use { sftp ->
                sftp.put(localFile.absolutePath, cfg.path)
                val tmp = File(tempDir, "remote_verify.cfg")
                sftp.get(cfg.path, tmp.absolutePath)
                val remoteSha = sha256(tmp.readBytes())
                remoteSha == localSha
            }
        }
    }

    private fun sha256(bytes: ByteArray): String {
        val md = MessageDigest.getInstance("SHA-256")
        val digest = md.digest(bytes)
        return digest.joinToString("") { "%02x".format(it) }
    }
}
