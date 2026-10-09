package com.rkfsociety.bedmesh.core

import android.content.Context
import net.schmizz.sshj.sftp.SFTPClient
import okhttp3.OkHttpClient
import okhttp3.Request
import java.io.File
import java.util.concurrent.TimeUnit

private const val RUN_SH = "/userdata/app/kenv/run.sh"
private const val BOOT_REMOTE = "/useremain/boot.sh"
private const val SSH_PKG_SRC = "/tmp/ssh"
private const val SSH_PKG_DST = "/useremain/ssh"
private const val GKBRIDGE_REMOTE = "/useremain/gkbridge"
private const val CAMERA_REMOTE = "/useremain/camera"
private const val RUN_HOOK_LINE = "[ -f /useremain/boot.sh ] && sh /useremain/boot.sh"
private const val GKBRIDGE_URL =
    "https://raw.githubusercontent.com/rkfsociety/bedmesh/main/webpanel/gkbridge"
private val CAMERA_FILES = listOf(
    "cam-on.sh",
    "cam-off.sh",
    "input_uvc.so",
    "libjpeg.so.8.2.2",
    "mjpg_streamer",
    "output_http.so",
)

object SshInstaller {

    /**
     * Устанавливает постоянный SSH (dropbear) на принтер:
     *  1. /tmp/ssh -> /useremain/ssh
     *  2. boot.sh -> /useremain/boot.sh
     *  3. хук в /userdata/app/kenv/run.sh
     *  4. немедленный запуск boot.sh
     */
    fun installPersistentSsh(
        context: Context,
        cfg: SshConfig,
        progress: (String) -> Unit,
    ) {
        withSshTransport(cfg) { ssh ->
            val sftp = ssh.newSFTPClient()
            try {
                progress("Копирование SSH-пакета в постоянное место…")
                ssh.startSession().use { s ->
                    s.exec("[ -d '$SSH_PKG_DST' ] || cp -a '$SSH_PKG_SRC' '$SSH_PKG_DST'").join()
                }
                ssh.startSession().use { s ->
                    val cmd = s.exec("test -f '$SSH_PKG_DST/dropbear'")
                    cmd.join()
                    if (cmd.exitStatus != 0) error("dropbear не найден в $SSH_PKG_DST")
                }

                progress("Загрузка boot.sh…")
                uploadBootSh(context, ssh, sftp)

                progress("Установка файлов камеры…")
                uploadCameraFiles(context, ssh, sftp)

                progress("Прописывание автозапуска в run.sh…")
                insertRunHook(ssh, sftp)

                progress("Запуск…")
                ssh.startSession().use { s -> s.exec("sh '$BOOT_REMOTE'").join() }

                progress("SSH установлен.")
            } finally {
                sftp.close()
            }
        }
    }

    /**
     * Устанавливает веб-панель gkbridge на принтер:
     *  1. скачивает gkbridge с GitHub -> /useremain/gkbridge
     *  2. boot.sh -> /useremain/boot.sh
     *  3. хук в run.sh
     *  4. немедленный запуск
     */
    fun installWebPanel(
        context: Context,
        cfg: SshConfig,
        progress: (String) -> Unit,
    ) {
        progress("Скачивание gkbridge с GitHub…")
        val gkbridgeFile = downloadGkbridge(context)

        withSshTransport(cfg) { ssh ->
            val sftp = ssh.newSFTPClient()
            try {
                progress("Загрузка gkbridge на принтер…")
                // Загружаем во временный файл, потом атомарно переименовываем
                val tmp = "$GKBRIDGE_REMOTE.new"
                sftp.put(gkbridgeFile.absolutePath, tmp)
                ssh.startSession().use { s ->
                    s.exec("killall gkbridge 2>/dev/null; sleep 1; mv -f '$tmp' '$GKBRIDGE_REMOTE'; chmod +x '$GKBRIDGE_REMOTE'").join()
                }

                progress("Загрузка boot.sh…")
                uploadBootSh(context, ssh, sftp)

                progress("Прописывание автозапуска в run.sh…")
                insertRunHook(ssh, sftp)

                progress("Запуск веб-панели…")
                ssh.startSession().use { s ->
                    s.exec("setsid sh -c 'sleep 1; nohup $GKBRIDGE_REMOTE >/tmp/gkbridge.out 2>&1 &' >/dev/null 2>&1 &").join()
                }

                progress("Веб-панель установлена.")
            } finally {
                sftp.close()
                gkbridgeFile.delete()
            }
        }
    }

    internal fun downloadGkbridge(context: Context): File {
        val client = OkHttpClient.Builder()
            .connectTimeout(30, TimeUnit.SECONDS)
            .readTimeout(90, TimeUnit.SECONDS)
            .build()
        val req = Request.Builder().url(GKBRIDGE_URL).build()
        val out = File(context.cacheDir, "gkbridge_download")
        client.newCall(req).execute().use { resp ->
            if (!resp.isSuccessful) error("HTTP ${resp.code}")
            val body = resp.body ?: error("Пустой ответ")
            out.outputStream().use { body.byteStream().copyTo(it) }
        }
        if (out.length() < 1024 * 1024) error("gkbridge слишком маленький: ${out.length()} байт")
        return out
    }

    private fun uploadCameraFiles(
        context: Context,
        ssh: net.schmizz.sshj.SSHClient,
        sftp: SFTPClient,
    ) {
        ssh.startSession().use { session ->
            val command = session.exec("mkdir -p '$CAMERA_REMOTE'")
            command.join()
            if (command.exitStatus != 0) error("Не удалось создать каталог камеры $CAMERA_REMOTE")
        }

        for (name in CAMERA_FILES) {
            val bytes = context.assets.open(name).use { it.readBytes() }
            val content = if (name.endsWith(".sh")) {
                bytes.toString(Charsets.UTF_8).replace("\r\n", "\n").replace("\r", "\n")
                    .toByteArray(Charsets.UTF_8)
            } else {
                bytes
            }
            val remotePath = "$CAMERA_REMOTE/$name"
            sftp.open(
                remotePath,
                setOf(
                    net.schmizz.sshj.sftp.OpenMode.WRITE,
                    net.schmizz.sshj.sftp.OpenMode.CREAT,
                    net.schmizz.sshj.sftp.OpenMode.TRUNC,
                ),
            ).use { file -> file.write(0L, content, 0, content.size) }
        }

        ssh.startSession().use { session ->
            val command = session.exec(
                "set -e; cd '$CAMERA_REMOTE'; chmod +x mjpg_streamer cam-on.sh cam-off.sh " +
                    "2>/dev/null; ln -sf libjpeg.so.8.2.2 libjpeg.so.8",
            )
            command.join()
            if (command.exitStatus != 0) error("Не удалось настроить запуск камеры")
        }
    }

    private fun uploadBootSh(context: Context, ssh: net.schmizz.sshj.SSHClient, sftp: SFTPClient) {
        val content = context.assets.open("boot.sh").use { it.readBytes() }
            .toString(Charsets.UTF_8)
            .replace("\r\n", "\n")
            .replace("\r", "\n")
        val tmp = File(context.cacheDir, "boot.sh")
        tmp.writeText(content, Charsets.UTF_8)
        sftp.put(tmp.absolutePath, BOOT_REMOTE)
        ssh.startSession().use { s -> s.exec("chmod +x '$BOOT_REMOTE'").join() }
        tmp.delete()
    }

    private fun insertRunHook(ssh: net.schmizz.sshj.SSHClient, sftp: SFTPClient) {
        val text = sftp.open(RUN_SH).use { f ->
            val buf = ByteArray(f.length().toInt())
            f.read(0L, buf, 0, buf.size)
            buf.toString(Charsets.UTF_8)
        }

        if ("/useremain/boot.sh" in text) return // уже есть

        // Бэкап
        ssh.startSession().use { s ->
            s.exec("cp -a '$RUN_SH' '${RUN_SH}.bedmesh_bak'").join()
        }

        val lines = text.replace("\r\n", "\n").replace("\r", "\n").lines().toMutableList()
        var inserted = false
        val result = mutableListOf<String>()
        for (line in lines) {
            if (!inserted && (line.trim() == "./start.sh" || ("start.sh" in line && !line.trim().startsWith("#")))) {
                result.add(RUN_HOOK_LINE)
                inserted = true
            }
            result.add(line)
        }
        if (!inserted) error("Якорь start.sh не найден в $RUN_SH")

        val newText = result.joinToString("\n")
        sftp.open(RUN_SH, setOf(net.schmizz.sshj.sftp.OpenMode.WRITE, net.schmizz.sshj.sftp.OpenMode.CREAT, net.schmizz.sshj.sftp.OpenMode.TRUNC)).use { f ->
            val bytes = newText.toByteArray(Charsets.UTF_8)
            f.write(0L, bytes, 0, bytes.size)
        }
    }
}
