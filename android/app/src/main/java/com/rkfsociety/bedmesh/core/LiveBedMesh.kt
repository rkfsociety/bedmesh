package com.rkfsociety.bedmesh.core

import android.content.Context
import com.rkfsociety.bedmesh.model.BedMeshData
import kotlinx.serialization.json.Json
import kotlinx.serialization.json.JsonObject
import kotlinx.serialization.json.JsonPrimitive
import kotlinx.serialization.json.jsonObject
import net.schmizz.sshj.SSHClient
import net.schmizz.sshj.connection.channel.direct.Session
import net.schmizz.sshj.sftp.SFTPClient
import java.io.ByteArrayOutputStream
import java.io.File
import java.security.MessageDigest
import java.util.concurrent.LinkedBlockingQueue
import java.util.concurrent.TimeUnit
import kotlin.math.abs

private val PROBE_LOG_RE = Regex(
    "probe\\s+at\\s+([+-]?\\d+(?:\\.\\d+)?),\\s*([+-]?\\d+(?:\\.\\d+)?)\\s+is\\s+z=([+-]?\\d+(?:\\.\\d+)?)",
    RegexOption.IGNORE_CASE,
)

data class BedMeshGrid(
    val xCount: Int,
    val yCount: Int,
    val minX: Double,
    val maxX: Double,
    val minY: Double,
    val maxY: Double,
) {
    val totalPoints: Int get() = xCount * yCount
    val x: DoubleArray get() = DoubleArray(xCount) { i -> minX + (maxX - minX) * i / (xCount - 1).coerceAtLeast(1) }
    val y: DoubleArray get() = DoubleArray(yCount) { i -> minY + (maxY - minY) * i / (yCount - 1).coerceAtLeast(1) }
}

data class LiveMeshProgress(
    val status: String,
    val measuredPoints: Int = 0,
    val totalPoints: Int = 0,
    val currentPoint: String? = null,
    val data: BedMeshData? = null,
)

data class LiveMeshResult(val data: BedMeshData, val measuredPoints: Int, val totalPoints: Int)

private class LiveMeshAccumulator(private val grid: BedMeshGrid) {
    private val xs = grid.x
    private val ys = grid.y
    private val values = mutableMapOf<Pair<Int, Int>, Double>()
    var current: Pair<Int, Int>? = null
        private set

    fun feed(line: String): Boolean {
        val match = PROBE_LOG_RE.find(line) ?: return false
        val xValue = match.groupValues[1].toDoubleOrNull() ?: return false
        val yValue = match.groupValues[2].toDoubleOrNull() ?: return false
        val zValue = match.groupValues[3].toDoubleOrNull() ?: return false
        val xIndex = xs.indices.minByOrNull { abs(xs[it] - xValue) } ?: return false
        val yIndex = ys.indices.minByOrNull { abs(ys[it] - yValue) } ?: return false
        if (abs(xs[xIndex] - xValue) > 1.0 || abs(ys[yIndex] - yValue) > 1.0) return false
        current = xIndex to yIndex
        values[current!!] = zValue
        return true
    }

    fun snapshot(): BedMeshData? {
        if (values.isEmpty()) return null
        val mean = values.values.average()
        val z = Array(grid.yCount) { y -> DoubleArray(grid.xCount) { x -> values[x to y] ?: mean } }
        return BedMeshData(xs, ys, z, grid.xCount, grid.yCount, grid.minX, grid.maxX, grid.minY, grid.maxY)
    }

    val measuredPoints: Int get() = values.size
}

object LiveBedMesh {
    private const val MUTABLE_PATH = "/userdata/app/gk/printer_mutable.cfg"
    private const val BRIDGE_ADDRESS = "127.0.0.1:18089"
    private const val BACKUP_TAG = "bedmesh_bak"
    private const val EOF_SENTINEL = "\u0000BEDMESH_EOF"
    private val calibrationCommands = listOf("LEVIQ2_PREHEATING", "LEVIQ2_WIPING", "G28 Z", "LEVIQ2_PROBE")
    private val cooldownCommands = listOf("M104 S0", "M140 S0")
    private val json = Json { prettyPrint = true }
    fun run(context: Context, cfg: SshConfig, onProgress: (LiveMeshProgress) -> Unit): LiveMeshResult {
        val bridgeFile = SshInstaller.downloadGkbridge(context)
        try {
            return withSshTransport(cfg) { ssh -> runConnected(ssh, bridgeFile, onProgress) }
        } finally {
            bridgeFile.delete()
        }
    }

    private fun runConnected(
        ssh: SSHClient,
        bridgeFile: File,
        onProgress: (LiveMeshProgress) -> Unit,
    ): LiveMeshResult {
        val grid = readGrid(ssh)
        val accumulator = LiveMeshAccumulator(grid)
        var monitorSession: Session? = null
        var logReader: Thread? = null
        var bridgePid: String? = null
        val bridgeRemote = "/tmp/bedmesh-gkbridge-android-${System.nanoTime()}"
        val bridgeLog = "$bridgeRemote.log"
        var calibrationStarted = false
        try {
            bridgePid = openBridge(ssh, bridgeFile, bridgeRemote, bridgeLog)
            monitorSession = ssh.startSession()
            val tail = monitorSession.exec("tail -n 0 -F /tmp/gklib.log")
            val lines = LinkedBlockingQueue<String>()
            logReader = Thread({
                try {
                    tail.inputStream.bufferedReader(Charsets.UTF_8).useLines { sequence ->
                        sequence.forEach { lines.offer(it) }
                    }
                } catch (_: Exception) {
                    // Channel closure is expected when calibration finishes.
                } finally {
                    lines.offer(EOF_SENTINEL)
                }
            }, "bedmesh-live-log-reader").apply { isDaemon = true; start() }

            calibrationCommands.forEach { command ->
                onProgress(LiveMeshProgress(commandStatus(command), totalPoints = grid.totalPoints))
                calibrationStarted = true
                sendGcode(ssh, command)
            }

            val startedAt = System.nanoTime()
            var lastPointAt = startedAt
            var sawPoint = false
            onProgress(LiveMeshProgress("Ожидание измерений…", totalPoints = grid.totalPoints))
            while (true) {
                val line = lines.poll(150, TimeUnit.MILLISECONDS)
                if (line != null && line != EOF_SENTINEL) {
                    if (accumulator.feed(line)) {
                        sawPoint = true
                        lastPointAt = System.nanoTime()
                        val current = accumulator.current!!
                        val x = grid.x[current.first]
                        val y = grid.y[current.second]
                        onProgress(
                            LiveMeshProgress(
                                status = "Измерено ${accumulator.measuredPoints}/${grid.totalPoints}: X=${"%.1f".format(java.util.Locale.US, x)} Y=${"%.1f".format(java.util.Locale.US, y)}",
                                measuredPoints = accumulator.measuredPoints,
                                totalPoints = grid.totalPoints,
                                currentPoint = "X=${"%.1f".format(java.util.Locale.US, x)}  Y=${"%.1f".format(java.util.Locale.US, y)}",
                                data = accumulator.snapshot(),
                            ),
                        )
                    } else {
                        val status = logStatus(line)
                        if (status != null) onProgress(LiveMeshProgress(status, accumulator.measuredPoints, grid.totalPoints))
                    }
                }
                val now = System.nanoTime()
                if (sawPoint && now - lastPointAt >= TimeUnit.SECONDS.toNanos(20)) break
                if (!sawPoint && now - startedAt >= TimeUnit.SECONDS.toNanos(180)) {
                    error("Принтер не передал ни одной точки за 3 минуты. Калибровка могла не начаться или журнал недоступен.")
                }
                if (line == EOF_SENTINEL && !sawPoint) error("Поток журнала принтера завершился до первого измерения.")
            }

            onProgress(LiveMeshProgress("Отключаю нагрев стола и сопла…", accumulator.measuredPoints, grid.totalPoints))
            cooldownCommands.forEach { command ->
                runCatching { sendGcode(ssh, command) }
            }
            calibrationStarted = false

            val complete = accumulator.snapshot() ?: error("Не получена карта стола.")
            if (accumulator.measuredPoints != grid.totalPoints) {
                error("Получено только ${accumulator.measuredPoints} из ${grid.totalPoints} точек. Неполная карта не сохранена.")
            }
            onProgress(LiveMeshProgress("Все точки измерены. Сохраняю карту на принтере…", grid.totalPoints, grid.totalPoints, data = complete))
            persistCompleteMesh(ssh, complete)
            return LiveMeshResult(complete, accumulator.measuredPoints, grid.totalPoints)
        } finally {
            if (calibrationStarted) {
                cooldownCommands.forEach { command -> runCatching { sendGcode(ssh, command) } }
            }
            runCatching { monitorSession?.close() }
            runCatching { stopBridge(ssh, bridgePid, bridgeRemote, bridgeLog) }
            logReader?.interrupt()
        }
    }

    private fun readGrid(ssh: SSHClient): BedMeshGrid {
        val cfgFile = File.createTempFile("bedmesh-printer-", ".cfg")
        try {
            ssh.newSFTPClient().use { it.get("/userdata/app/gk/printer.cfg", cfgFile.absolutePath) }
            val parsed = KlipperConfig.parse(cfgFile.readText(Charsets.UTF_8))
            val section = parsed.resolveSection("bed_mesh") ?: error("В printer.cfg не найдена секция [bed_mesh].")
            val fields = parsed.sections[section] ?: error("Не удалось прочитать настройки bed_mesh.")
            fun pair(key: String): List<String> {
                val parts = fields[key]?.value?.split(",")?.map { it.trim() }
                    ?: error("Не удалось прочитать $key в [bed_mesh].")
                return when {
                    key == "probe_count" && parts.size == 1 -> listOf(parts[0], parts[0])
                    parts.size == 2 -> parts
                    else -> error("Не удалось прочитать $key в [bed_mesh].")
                }
            }
            val count = pair("probe_count")
            val min = pair("mesh_min")
            val max = pair("mesh_max")
            val grid = BedMeshGrid(
                xCount = count[0].toIntOrNull() ?: error("Некорректный probe_count."),
                yCount = count[1].toIntOrNull() ?: error("Некорректный probe_count."),
                minX = min[0].toDoubleOrNull() ?: error("Некорректный mesh_min."),
                maxX = max[0].toDoubleOrNull() ?: error("Некорректный mesh_max."),
                minY = min[1].toDoubleOrNull() ?: error("Некорректный mesh_min."),
                maxY = max[1].toDoubleOrNull() ?: error("Некорректный mesh_max."),
            )
            check(grid.xCount in 2..30 && grid.yCount in 2..30 && grid.maxX > grid.minX && grid.maxY > grid.minY) {
                "Размер или диапазон сетки bed_mesh некорректен."
            }
            return grid
        } finally {
            cfgFile.delete()
        }
    }

    private fun openBridge(ssh: SSHClient, localBinary: File, remote: String, log: String): String {
        var pid: String? = null
        try {
            ssh.newSFTPClient().use { it.put(localBinary.absolutePath, remote) }
            val launch = "chmod 700 ${shQuote(remote)}; ${shQuote(remote)} -addr $BRIDGE_ADDRESS >${shQuote(log)} 2>&1 & echo $!"
            val launchedPid = exec(ssh, launch).trim().lineSequence().lastOrNull().orEmpty()
            check(launchedPid.matches(Regex("\\d+"))) { "Не удалось запустить временный gkbridge." }
            pid = launchedPid
            Thread.sleep(250)
            val socket = ssh.newDirectConnection("127.0.0.1", 18089)
            try {
                check(socket.isOpen) { "Временный gkbridge не запустился." }
            } finally {
                socket.close()
            }
            return launchedPid
        } catch (error: Exception) {
            runCatching { stopBridge(ssh, pid, remote, log) }
            throw error
        }
    }

    private fun sendGcode(ssh: SSHClient, script: String) {
        val body = Json.encodeToString(
            JsonObject.serializer(), JsonObject(mapOf("script" to JsonPrimitive(script))),
        ).toByteArray(Charsets.UTF_8)
        val request = buildString {
            append("POST /gcode HTTP/1.0\r\nHost: localhost\r\nContent-Type: application/json\r\n")
            append("Content-Length: ${body.size}\r\n\r\n")
        }.toByteArray(Charsets.US_ASCII) + body
        val socket = ssh.newDirectConnection("127.0.0.1", 18089)
        try {
            socket.getOutputStream().apply { write(request); flush() }
            val response = java.util.concurrent.FutureTask {
                val bytes = ByteArrayOutputStream()
                val buffer = ByteArray(4096)
                while (bytes.size() < 16_384) {
                    val read = socket.inputStream.read(buffer)
                    if (read < 0) break
                    bytes.write(buffer, 0, read)
                }
                bytes.toByteArray()
            }
            Thread(response, "bedmesh-gcode-response").apply { isDaemon = true; start() }
            val text = try {
                String(response.get(8, TimeUnit.SECONDS), Charsets.UTF_8)
            } catch (timeout: java.util.concurrent.TimeoutException) {
                socket.close()
                throw java.io.IOException("Ответ gkbridge не получен за 8 секунд после отправки $script.", timeout)
            }
            val statusLine = text.lineSequence().firstOrNull().orEmpty()
            val acceptedTimeout = statusLine.contains(" 502 ") && "i/o timeout" in text.lowercase()
            check(statusLine.contains(" 200 ") || acceptedTimeout) {
                "Не удалось отправить штатную команду $script через gkbridge: ${text.takeLast(500)}"
            }
        } finally {
            socket.close()
        }
    }

    private fun persistCompleteMesh(ssh: SSHClient, data: BedMeshData) {
            val sftp = ssh.newSFTPClient()
            val files = mutableListOf<File>()
            val temps = mutableListOf<String>()
            try {
                val current = readRemoteText(sftp, MUTABLE_PATH, files)
                val updated = updateMutableMesh(current, data).toByteArray(Charsets.UTF_8)
                val backup = "$MUTABLE_PATH.${BACKUP_TAG}_" + java.time.LocalDateTime.now()
                    .format(java.time.format.DateTimeFormatter.ofPattern("yyyyMMdd_HHmmss_SSS"))
                execChecked(ssh, "cp ${shQuote(MUTABLE_PATH)} ${shQuote(backup)}")
                execChecked(ssh, "test -f ${shQuote(backup)}")

                val local = File.createTempFile("bedmesh-live-", ".json")
                files += local
                local.writeBytes(updated)
                val temp = "$MUTABLE_PATH.bedmesh_upload_${System.nanoTime()}"
                temps += temp
                sftp.put(local.absolutePath, temp)
                check(sha256(updated) == sha256(readRemoteBytes(sftp, temp, files))) {
                    "Проверка временной карты не пройдена."
                }
                execChecked(ssh, "mv -f ${shQuote(temp)} ${shQuote(MUTABLE_PATH)}")
                temps.remove(temp)
                check(sha256(updated) == sha256(readRemoteBytes(sftp, MUTABLE_PATH, files))) {
                    "Проверка сохранённой карты не пройдена."
                }
            } finally {
                temps.forEach { runCatching { execChecked(ssh, "rm -f ${shQuote(it)}") } }
                files.forEach { it.delete() }
                sftp.close()
            }
    }

    private fun updateMutableMesh(text: String, data: BedMeshData): String {
        val root = Json.parseToJsonElement(text).jsonObject
        val key = root.keys.firstOrNull { it == "bed_mesh default" || it.startsWith("bed_mesh default ") }
            ?: error("В printer_mutable.cfg не найден объект bed_mesh default.")
        val mesh = root[key]?.jsonObject ?: error("Объект bed_mesh default имеет неверный формат.")
        check(data.z.size == data.yCount && data.z.all { it.size == data.xCount && it.all(Double::isFinite) }) {
            "Live-карта имеет неполный размер или некорректные значения."
        }
        val points = data.z.joinToString("\n") { row -> row.joinToString(", ") { "%.6f".format(java.util.Locale.US, it) } }
        val updatedMesh = JsonObject(
            mesh + mapOf(
                "min_x" to JsonPrimitive(numberString(data.minX)),
                "max_x" to JsonPrimitive(numberString(data.maxX)),
                "min_y" to JsonPrimitive(numberString(data.minY)),
                "max_y" to JsonPrimitive(numberString(data.maxY)),
                "x_count" to JsonPrimitive(data.xCount.toString()),
                "y_count" to JsonPrimitive(data.yCount.toString()),
                "points" to JsonPrimitive(points),
            ),
        )
        return json.encodeToString(JsonObject.serializer(), JsonObject(root + (key to updatedMesh))) + "\n"
    }

    private fun commandStatus(command: String): String = when (command) {
        "LEVIQ2_PREHEATING" -> "Прогрев стола и сопла…"
        "LEVIQ2_WIPING" -> "Очистка сопла…"
        "G28 Z" -> "Хоуминг оси Z…"
        else -> "Измерение стола тензодатчиком…"
    }

    private fun logStatus(line: String): String? {
        val text = line.uppercase()
        return when {
            "LEVIQ2_PREHEATING" in text || "CMD_LEVIQ3_PREHEATING" in text -> "Принтер прогревает стол и сопло…"
            "LEVIQ2_WIPING" in text || "WIPING" in text -> "Принтер очищает сопло…"
            "CMD_G28" in text || "G28 Z" in text -> "Принтер выполняет хоуминг Z…"
            "LEVIQ2_PROBE" in text -> "Принтер измеряет стол тензодатчиком…"
            "SAVE_CONFIG" in text -> "Принтер сохраняет карту…"
            else -> null
        }
    }

    private fun stopBridge(ssh: SSHClient, pid: String?, remote: String, log: String) {
        val pidArg = pid?.takeIf { it.matches(Regex("\\d+")) }
        val command = if (pidArg != null) "kill $pidArg 2>/dev/null; " else ""
        exec(ssh, "${command}rm -f ${shQuote(remote)} ${shQuote(log)}")
    }

    private fun readRemoteText(sftp: SFTPClient, path: String, files: MutableList<File>): String =
        readRemoteBytes(sftp, path, files).toString(Charsets.UTF_8)

    private fun readRemoteBytes(sftp: SFTPClient, path: String, files: MutableList<File>): ByteArray {
        val local = File.createTempFile("bedmesh-remote-", ".cfg")
        files += local
        sftp.get(path, local.absolutePath)
        return local.readBytes()
    }

    private fun exec(ssh: SSHClient, commandText: String): String = ssh.startSession().use { session ->
        val command = session.exec(commandText)
        command.join()
        check(command.exitStatus == 0) { "Команда принтера завершилась с ошибкой: $commandText" }
        command.inputStream.bufferedReader(Charsets.UTF_8).readText()
    }

    private fun execChecked(ssh: SSHClient, commandText: String) { exec(ssh, commandText) }

    private fun shQuote(value: String): String = "'" + value.replace("'", "'\"'\"'") + "'"

    private fun sha256(bytes: ByteArray): String = MessageDigest.getInstance("SHA-256")
        .digest(bytes).joinToString("") { "%02x".format(it) }

    private fun numberString(value: Double): String =
        java.math.BigDecimal.valueOf(value).stripTrailingZeros().toPlainString()
}
