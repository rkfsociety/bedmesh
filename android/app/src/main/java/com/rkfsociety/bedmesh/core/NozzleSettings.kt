package com.rkfsociety.bedmesh.core

import kotlinx.serialization.json.Json
import kotlinx.serialization.json.JsonObject
import kotlinx.serialization.json.JsonPrimitive
import kotlinx.serialization.json.jsonObject
import kotlinx.serialization.json.jsonPrimitive
import net.schmizz.sshj.SSHClient
import net.schmizz.sshj.sftp.SFTPClient
import java.io.File
import java.security.MessageDigest

data class NozzleSelection(val diameter: String, val material: String)

data class NozzleApplyResult(val selection: NozzleSelection, val calibrationRequested: Boolean)

object NozzleSettings {
    val diameters = listOf("0.20", "0.25", "0.30", "0.40", "0.50", "0.60", "0.80", "1.00", "1.20")
    val materials = listOf("brass", "hardened_steel")

    private const val MUTABLE_PATH = "/userdata/app/gk/printer_mutable.cfg"
    private const val METADATA_PATH = "/userdata/app/gk/config/nozzle.cfg"
    private const val BACKUP_TAG = "bedmesh_bak"

    fun readSelection(printerCfg: String, mutableCfg: String?, metadataCfg: String?): NozzleSelection {
        val mutable = mutableCfg?.let(::parseMutableNozzle)
        val metadata = metadataCfg?.let(::parseNozzleMetadata)
        val printer = parsePrinterNozzle(printerCfg)
        return NozzleSelection(
            diameter = mutable?.first ?: printer.first ?: metadata?.second ?: "0.40",
            material = mutable?.second ?: metadata?.first ?: printer.second ?: "brass",
        )
    }

    fun applyAndReboot(
        cfg: SshConfig,
        selection: NozzleSelection,
        runFullCalibration: Boolean,
    ): NozzleApplyResult {
        require(selection.diameter in diameters) { "Выберите диаметр из списка." }
        require(selection.material in materials) { "Выберите поддерживаемый материал сопла." }

        return withSshTransport(cfg) { ssh ->
            val sftp = ssh.newSFTPClient()
            val localFiles = mutableListOf<File>()
            val remoteTemps = mutableListOf<String>()
            try {
                val printerCfg = readRemoteText(sftp, cfg.path, localFiles)
                val mutableCfg = readRemoteText(sftp, MUTABLE_PATH, localFiles)
                readRemoteText(sftp, METADATA_PATH, localFiles)

                val updatedPrinter = replacePrinterDiameter(printerCfg, selection.diameter)
                val updatedMutable = replaceMutableNozzle(mutableCfg, selection)
                val updatedMetadata = Json.encodeToString(
                    JsonObject.serializer(),
                    JsonObject(
                        mapOf(
                            "material" to JsonPrimitive(selection.material),
                            "diameter" to JsonPrimitive(selection.diameter),
                            "modify" to JsonPrimitive(runFullCalibration),
                        ),
                    ),
                ) + "\n"

                // Create and verify every backup before changing any of the three files.
                val targets = listOf(cfg.path, MUTABLE_PATH, METADATA_PATH)
                val stamp = java.time.LocalDateTime.now()
                    .format(java.time.format.DateTimeFormatter.ofPattern("yyyyMMdd_HHmmss_SSS"))
                targets.forEach { path ->
                    val backup = "$path.${BACKUP_TAG}_$stamp"
                    execChecked(ssh, "cp ${shQuote(path)} ${shQuote(backup)}")
                    execChecked(ssh, "test -f ${shQuote(backup)}")
                }

                writeVerified(ssh, sftp, cfg.path, updatedPrinter, localFiles, remoteTemps)
                writeVerified(ssh, sftp, MUTABLE_PATH, updatedMutable, localFiles, remoteTemps)
                writeVerified(ssh, sftp, METADATA_PATH, updatedMetadata, localFiles, remoteTemps)

                val reboot = ssh.startSession()
                try {
                    val command = reboot.exec("nohup sh -c 'sleep 1; reboot' >/dev/null 2>&1 </dev/null &")
                    command.join()
                    check(command.exitStatus == 0) { "Не удалось запросить перезапуск принтера." }
                } finally {
                    reboot.close()
                }
                NozzleApplyResult(selection, runFullCalibration)
            } finally {
                remoteTemps.forEach { path -> runCatching { execChecked(ssh, "rm -f ${shQuote(path)}") } }
                localFiles.forEach { it.delete() }
                sftp.close()
            }
        }
    }

    private fun parsePrinterNozzle(text: String): Pair<String?, String?> {
        var inExtruder = false
        var diameter: String? = null
        var material: String? = null
        text.lineSequence().forEach { line ->
            val section = Regex("^\\s*\\[([^]]+)]\\s*$").matchEntire(line.trimEnd('\r'))
            if (section != null) {
                inExtruder = section.groupValues[1].trim().equals("extruder", ignoreCase = true)
            } else if (inExtruder) {
                val match = Regex("^\\s*(nozzle_diameter|nozzle_material)\\s*:\\s*([^#\\s]+)", RegexOption.IGNORE_CASE)
                    .find(line) ?: return@forEach
                when (match.groupValues[1].lowercase()) {
                    "nozzle_diameter" -> diameter = match.groupValues[2].toDoubleOrNull()?.let { "%.2f".format(java.util.Locale.US, it) }
                    "nozzle_material" -> material = match.groupValues[2].lowercase()
                }
            }
        }
        return diameter to material
    }

    private fun replacePrinterDiameter(text: String, diameter: String): String {
        val lines = text.split("\n").toMutableList()
        var inExtruder = false
        var found = false
        for (index in lines.indices) {
            val line = lines[index]
            val section = Regex("^\\s*\\[([^]]+)]\\s*$").matchEntire(line.trimEnd('\r'))
            if (section != null) {
                inExtruder = section.groupValues[1].trim().equals("extruder", ignoreCase = true)
            } else if (inExtruder && Regex("^\\s*nozzle_diameter\\s*:", RegexOption.IGNORE_CASE).containsMatchIn(line)) {
                val newline = if (line.endsWith("\r")) "\r" else ""
                val indent = line.takeWhile { it == ' ' || it == '\t' }
                lines[index] = "${indent}nozzle_diameter : $diameter$newline"
                found = true
            }
        }
        check(found) { "В секции [extruder] не найден nozzle_diameter." }
        return lines.joinToString("\n")
    }

    private fun replaceMutableNozzle(text: String, selection: NozzleSelection): String {
        val root = Json.parseToJsonElement(text).jsonObject
        val extruder = root["extruder"]?.jsonObject
            ?: error("В printer_mutable.cfg не найден объект extruder.")
        val updatedExtruder = JsonObject(
            extruder + mapOf(
                "nozzle_diameter" to JsonPrimitive(selection.diameter),
                "nozzle_material" to JsonPrimitive(selection.material),
            ),
        )
        return Json { prettyPrint = true }.encodeToString(
            JsonObject.serializer(), JsonObject(root + ("extruder" to updatedExtruder)),
        ) + "\n"
    }

    private fun parseMutableNozzle(text: String): Pair<String?, String?>? = runCatching {
        val extruder = Json.parseToJsonElement(text).jsonObject["extruder"]?.jsonObject ?: return null
        val diameter = extruder["nozzle_diameter"]?.jsonPrimitive?.content
            ?.toDoubleOrNull()?.let { "%.2f".format(java.util.Locale.US, it) }
        val material = extruder["nozzle_material"]?.jsonPrimitive?.content?.lowercase()
        diameter to material
    }.getOrNull()

    private fun parseNozzleMetadata(text: String): Pair<String?, String?>? = runCatching {
        val metadata = Json.parseToJsonElement(text).jsonObject
        val material = metadata["material"]?.jsonPrimitive?.content?.takeUnless { it == "-" }?.lowercase()
        val diameter = metadata["diameter"]?.jsonPrimitive?.content?.takeUnless { it == "-" }
        material to diameter
    }.getOrNull()

    private fun readRemoteText(sftp: SFTPClient, path: String, localFiles: MutableList<File>): String {
        val local = File.createTempFile("bedmesh-remote-", ".cfg")
        localFiles += local
        sftp.get(path, local.absolutePath)
        return local.readText(Charsets.UTF_8)
    }

    private fun writeVerified(
        ssh: SSHClient,
        sftp: SFTPClient,
        target: String,
        content: String,
        localFiles: MutableList<File>,
        remoteTemps: MutableList<String>,
    ) {
        val local = File.createTempFile("bedmesh-nozzle-", ".cfg")
        localFiles += local
        local.writeText(content, Charsets.UTF_8)
        val temp = "$target.bedmesh_upload_${System.nanoTime()}"
        remoteTemps += temp
        sftp.put(local.absolutePath, temp)
        check(sha256(local.readBytes()) == sha256(readRemoteBytes(sftp, temp, localFiles))) {
            "Проверка временного файла не пройдена: $target"
        }
        execChecked(ssh, "mv -f ${shQuote(temp)} ${shQuote(target)}")
        remoteTemps.remove(temp)
        check(sha256(local.readBytes()) == sha256(readRemoteBytes(sftp, target, localFiles))) {
            "Проверка сохранённого файла не пройдена: $target"
        }
    }

    private fun readRemoteBytes(sftp: SFTPClient, path: String, localFiles: MutableList<File>): ByteArray {
        val local = File.createTempFile("bedmesh-verify-", ".cfg")
        localFiles += local
        sftp.get(path, local.absolutePath)
        return local.readBytes()
    }

    private fun execChecked(ssh: SSHClient, commandText: String) {
        ssh.startSession().use { session ->
            val command = session.exec(commandText)
            command.join()
            check(command.exitStatus == 0) { "Команда принтера завершилась с ошибкой: $commandText" }
        }
    }

    private fun shQuote(value: String): String = "'" + value.replace("'", "'\"'\"'") + "'"

    private fun sha256(bytes: ByteArray): String = MessageDigest.getInstance("SHA-256")
        .digest(bytes).joinToString("") { "%02x".format(it) }
}
