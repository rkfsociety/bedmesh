package com.rkfsociety.bedmesh.core

import net.schmizz.sshj.SSHClient
import net.schmizz.sshj.sftp.RemoteResourceInfo
import net.schmizz.sshj.transport.verification.PromiscuousVerifier
import java.io.File
import java.security.MessageDigest

object SshBackups {
    private const val BACKUP_TAG = "bedmesh_bak"

    private fun shQuote(s: String): String = "'" + s.replace("'", "'\"'\"'") + "'"

    fun listBackups(cfg: SshConfig): List<String> {
        val ssh = SSHClient()
        ssh.addHostKeyVerifier(PromiscuousVerifier())
        ssh.connect(cfg.ip, cfg.port)
        try {
            ssh.authPassword(cfg.user, cfg.password)
            val dir = cfg.path.substringBeforeLast("/", missingDelimiterValue = "")
                .ifBlank { "/" }
            val base = cfg.path.substringAfterLast("/")
            val prefix = "${base}.${BACKUP_TAG}_"

            ssh.newSFTPClient().use { sftp ->
                val items: List<RemoteResourceInfo> = sftp.ls(dir)
                val candidates = items
                    .filter { it.name.startsWith(prefix) }
                    .map {
                        val full = dir.trimEnd('/') + "/" + it.name
                        val mtime = it.attributes.mtime
                        full to mtime
                    }
                    .sortedByDescending { it.second }
                    .map { it.first }
                return candidates
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

    fun createBackup(cfg: SshConfig): String? {
        val ssh = SSHClient()
        ssh.addHostKeyVerifier(PromiscuousVerifier())
        ssh.connect(cfg.ip, cfg.port)
        try {
            ssh.authPassword(cfg.user, cfg.password)
            val ts = java.time.LocalDateTime.now()
                .format(java.time.format.DateTimeFormatter.ofPattern("yyyyMMdd_HHmmss"))
            val backupPath = "${cfg.path}.${BACKUP_TAG}_$ts"
            ssh.startSession().use { session ->
                val cmd = session.exec("cp ${shQuote(cfg.path)} ${shQuote(backupPath)}")
                cmd.join()
                val status = cmd.exitStatus ?: -1
                if (status != 0) return null
            }
            return backupPath
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

    fun restoreBackup(cfg: SshConfig, backupPath: String): Boolean {
        val ssh = SSHClient()
        ssh.addHostKeyVerifier(PromiscuousVerifier())
        ssh.connect(cfg.ip, cfg.port)
        try {
            ssh.authPassword(cfg.user, cfg.password)
            ssh.startSession().use { session ->
                val cmd = session.exec("cp ${shQuote(backupPath)} ${shQuote(cfg.path)}")
                cmd.join()
                return (cmd.exitStatus ?: -1) == 0
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

    fun deleteBackup(cfg: SshConfig, backupPath: String): Boolean {
        val ssh = SSHClient()
        ssh.addHostKeyVerifier(PromiscuousVerifier())
        ssh.connect(cfg.ip, cfg.port)
        try {
            ssh.authPassword(cfg.user, cfg.password)
            ssh.startSession().use { session ->
                val cmd = session.exec("rm -f ${shQuote(backupPath)}")
                cmd.join()
                return (cmd.exitStatus ?: -1) == 0
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

    fun uploadWithVerify(cfg: SshConfig, localFile: File, tempDir: File): Boolean {
        val localSha = sha256(localFile.readBytes())

        val ssh = SSHClient()
        ssh.addHostKeyVerifier(PromiscuousVerifier())
        ssh.connect(cfg.ip, cfg.port)
        try {
            ssh.authPassword(cfg.user, cfg.password)
            ssh.newSFTPClient().use { sftp ->
                sftp.put(localFile.absolutePath, cfg.path)
                val tmp = File(tempDir, "remote_verify.cfg")
                sftp.get(cfg.path, tmp.absolutePath)
                val remoteSha = sha256(tmp.readBytes())
                return remoteSha == localSha
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

    private fun sha256(bytes: ByteArray): String {
        val md = MessageDigest.getInstance("SHA-256")
        val digest = md.digest(bytes)
        return digest.joinToString("") { "%02x".format(it) }
    }
}

