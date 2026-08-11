package com.rkfsociety.bedmesh.ui.vm

import android.app.Application
import android.content.ClipData
import android.content.ClipboardManager
import android.content.Context
import android.content.Intent
import android.net.Uri
import android.os.Build
import android.util.Log
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import androidx.core.content.FileProvider
import com.rkfsociety.bedmesh.BuildConfig
import com.rkfsociety.bedmesh.core.GithubUpdater
import com.rkfsociety.bedmesh.core.InputShaperData
import com.rkfsociety.bedmesh.core.KlipperConfig
import com.rkfsociety.bedmesh.core.MeshParser
import com.rkfsociety.bedmesh.core.MeshStatsCalculator
import com.rkfsociety.bedmesh.core.SshClient
import com.rkfsociety.bedmesh.core.SshBackups
import com.rkfsociety.bedmesh.core.SshConfig
import com.rkfsociety.bedmesh.core.SshInstaller
import com.rkfsociety.bedmesh.core.SshPrefs
import com.rkfsociety.bedmesh.core.UpdateState
import com.rkfsociety.bedmesh.core.aceProValuesForPercent
import com.rkfsociety.bedmesh.core.formatDiagnostic
import com.rkfsociety.bedmesh.core.normalizeBedMeshPairValue
import com.rkfsociety.bedmesh.core.probeCountAllowsLagrange
import com.rkfsociety.bedmesh.core.resolveSection
import com.rkfsociety.bedmesh.model.BedMeshData
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import java.io.File

data class InstallState(
    val busy: Boolean = false,
    val log: List<String> = emptyList(),
    val error: String? = null,
    val done: Boolean = false,
)

data class UiState(
    val ssh: SshConfig = SshPrefs.defaultConfig(),
    val busy: Boolean = false,
    val rawText: String = "",
    val mesh: BedMeshData? = null,
    val stats: Map<String, String> = emptyMap(),
    val shaper: InputShaperData? = null,
    val config: KlipperConfig? = null,
    val configEdits: Map<String, String> = emptyMap(),
    val backups: List<String> = emptyList(),
    val update: UpdateState = UpdateState(currentVersion = BuildConfig.VERSION_NAME),
    val lastError: String? = null,
    val installSsh: InstallState = InstallState(),
    val installPanel: InstallState = InstallState(),
)

private data class SshDownloadOutcome(
    val rawText: String,
    val mesh: BedMeshData?,
    val stats: Map<String, String>,
    val shaper: InputShaperData?,
    val config: KlipperConfig,
    val backups: List<String>,
    val parseWarning: String?,
)

class AppViewModel(application: Application) : AndroidViewModel(application) {
    private val _uiState = MutableStateFlow(
        UiState(ssh = SshPrefs.load(application)),
    )
    val uiState: StateFlow<UiState> = _uiState

    init {
        // Автопроверка обновлений при старте приложения.
        checkUpdates()
    }

    fun updateSshField(key: String, value: String) {
        _uiState.update { st ->
            val cur = st.ssh
            val next = when (key) {
                "ip" -> cur.copy(ip = value)
                "port" -> cur.copy(port = value.toIntOrNull() ?: cur.port)
                "user" -> cur.copy(user = value)
                "password" -> cur.copy(password = value)
                "path" -> cur.copy(path = value)
                else -> cur
            }
            SshPrefs.save(getApplication(), next)
            st.copy(ssh = next)
        }
    }

    fun clearError() {
        _uiState.update { it.copy(lastError = null) }
    }

    fun downloadViaSsh(context: Context) {
        val cfg = _uiState.value.ssh
        val appCtx = context.applicationContext
        viewModelScope.launch {
            _uiState.update { it.copy(busy = true, lastError = null) }
            try {
                val outcome = withContext(Dispatchers.IO) {
                    val file = SshClient.downloadFile(appCtx, cfg, cfg.path)
                    val text = file.readText()

                    val parsedCfg = KlipperConfig.parse(text)
                    val backups = runCatching { SshBackups.listBackups(cfg) }.getOrDefault(emptyList())

                    // mirror Windows behavior: if no mesh points found in printer.cfg, try printer_mutable.cfg
                    var parsed = MeshParser.parseText(text)
                    var rawText = text
                    var shaper = MeshParser.parseInputShaper(text)
                    if (parsed == null && cfg.path.endsWith("printer.cfg")) {
                        val mutablePath = "/userdata/app/gk/printer_mutable.cfg"
                        val alt = SshClient.downloadFile(appCtx, cfg, mutablePath)
                        val altText = alt.readText()
                        val altParsed = MeshParser.parseText(altText)
                        if (altParsed != null) {
                            parsed = altParsed
                            rawText = altText
                        }
                        // Шейпер ищем в mutable, потом в основном файле
                        if (shaper == null) shaper = MeshParser.parseInputShaper(altText)
                    }

                    val stats = if (parsed != null) {
                        val s = MeshStatsCalculator.compute(parsed)
                        mapOf(
                            "min" to String.format("%+.3f", s.min),
                            "max" to String.format("%+.3f", s.max),
                            "range" to String.format("%.3f", s.range),
                            "mean" to String.format("%+.3f", s.mean),
                            "var" to String.format("%.3f", s.variance),
                            "rms" to String.format("%.3f", s.rms),
                            "front_left_mm" to String.format("%+.3f", s.frontLeft),
                            "front_left_turns" to String.format("%.2f", s.turnsFor(s.frontLeft)),
                            "front_left_dir" to if (s.frontLeft < 0) "ВВЕРХ" else "ВНИЗ",
                            "front_right_mm" to String.format("%+.3f", s.frontRight),
                            "front_right_turns" to String.format("%.2f", s.turnsFor(s.frontRight)),
                            "front_right_dir" to if (s.frontRight < 0) "ВВЕРХ" else "ВНИЗ",
                            "back_center_mm" to String.format("%+.3f", s.backCenter),
                            "back_center_turns" to String.format("%.2f", s.turnsFor(s.backCenter)),
                            "back_center_dir" to if (s.backCenter < 0) "ВВЕРХ" else "ВНИЗ",
                        )
                    } else {
                        emptyMap()
                    }

                    SshDownloadOutcome(
                        rawText = rawText,
                        mesh = parsed,
                        stats = stats,
                        shaper = shaper,
                        config = parsedCfg,
                        backups = backups,
                        parseWarning = if (parsed == null) "Не найден bed_mesh в файле" else null,
                    )
                }

                _uiState.update {
                    it.copy(
                        busy = false,
                        rawText = outcome.rawText,
                        mesh = outcome.mesh,
                        stats = outcome.stats,
                        shaper = outcome.shaper,
                        config = outcome.config,
                        configEdits = emptyMap(),
                        backups = outcome.backups,
                        lastError = outcome.parseWarning,
                    )
                }
            } catch (e: Exception) {
                Log.e("BedMesh", "SSH download failed: ${e.formatDiagnostic()}", e)
                _uiState.update { it.copy(busy = false, lastError = e.formatDiagnostic()) }
            }
        }
    }

    fun updateConfigField(section: String, key: String, value: String) {
        val mapKey = "$section.$key"
        _uiState.update { st ->
            var edits = st.configEdits + (mapKey to value)
            if (section == st.config?.resolveSection("bed_mesh") && key == "probe_count" &&
                !probeCountAllowsLagrange(value)
            ) {
                val algorithmKey = "$section.algorithm"
                val current = edits[algorithmKey] ?: st.config?.sections?.get(section)?.get("algorithm")?.value
                if (current?.trim()?.equals("lagrange", ignoreCase = true) == true) {
                    edits = edits + (algorithmKey to "bicubic")
                }
            }
            st.copy(configEdits = edits)
        }
    }

    /** Как пресет Ace Pro в Windows `config_editor.py` (100%…300%). */
    fun applyAceProPreset(percent: Int) {
        val st = _uiState.value
        val base = st.config ?: return
        val sec = base.resolveSection("filament_hub") ?: return
        val values = aceProValuesForPercent(percent)
        _uiState.update { s ->
            var edits = s.configEdits
            for ((k, v) in values) {
                if (base.sections[sec]?.containsKey(k) == true) {
                    edits = edits + ("$sec.$k" to v)
                }
            }
            s.copy(configEdits = edits)
        }
    }

    fun refreshBackups() {
        val cfg = _uiState.value.ssh
        viewModelScope.launch {
            _uiState.update { it.copy(busy = true, lastError = null) }
            try {
                val list = withContext(Dispatchers.IO) { SshBackups.listBackups(cfg) }
                _uiState.update { it.copy(busy = false, backups = list) }
            } catch (e: Exception) {
                _uiState.update { it.copy(busy = false, lastError = e.formatDiagnostic()) }
            }
        }
    }

    fun createBackup() {
        val cfg = _uiState.value.ssh
        viewModelScope.launch {
            _uiState.update { it.copy(busy = true, lastError = null) }
            try {
                val list = withContext(Dispatchers.IO) {
                    SshBackups.createBackup(cfg)
                    SshBackups.listBackups(cfg)
                }
                _uiState.update { it.copy(busy = false, backups = list) }
            } catch (e: Exception) {
                _uiState.update { it.copy(busy = false, lastError = e.formatDiagnostic()) }
            }
        }
    }

    fun restoreBackup(path: String) {
        val cfg = _uiState.value.ssh
        viewModelScope.launch {
            _uiState.update { it.copy(busy = true, lastError = null) }
            try {
                val ok = withContext(Dispatchers.IO) { SshBackups.restoreBackup(cfg, path) }
                _uiState.update { it.copy(busy = false, lastError = if (!ok) "restore_failed" else null) }
            } catch (e: Exception) {
                _uiState.update { it.copy(busy = false, lastError = e.formatDiagnostic()) }
            }
        }
    }

    fun deleteBackup(path: String) {
        val cfg = _uiState.value.ssh
        viewModelScope.launch {
            _uiState.update { it.copy(busy = true, lastError = null) }
            try {
                val pair = withContext(Dispatchers.IO) {
                    val ok = SshBackups.deleteBackup(cfg, path)
                    ok to SshBackups.listBackups(cfg)
                }
                _uiState.update {
                    it.copy(busy = false, backups = pair.second, lastError = if (!pair.first) "delete_failed" else null)
                }
            } catch (e: Exception) {
                _uiState.update { it.copy(busy = false, lastError = e.formatDiagnostic()) }
            }
        }
    }

    fun saveConfigToPrinter(context: Context) {
        val st = _uiState.value
        val cfg = st.ssh
        val base = st.config ?: run {
            _uiState.update { it.copy(lastError = "config_not_loaded") }
            return
        }
        val appCtx = context.applicationContext
        viewModelScope.launch {
            _uiState.update { it.copy(busy = true, lastError = null) }
            try {
                val uploadResult = withContext(Dispatchers.IO) {
                    // Apply edits into a copy (keep original usable until upload succeeds)
                    val copy = KlipperConfig(
                        base.rawLines.toMutableList(),
                        base.sections.toMutableMap().mapValues { it.value.toMutableMap() }.toMutableMap(),
                    )
                    for ((k, v) in st.configEdits) {
                        val parts = k.split(".", limit = 2)
                        if (parts.size == 2) {
                            val key = parts[1]
                            val normalized = normalizeBedMeshPairValue(key, v)
                            copy.setValue(parts[0], key, normalized)
                        }
                    }

                    SshBackups.createBackup(cfg)

                    val temp = File(appCtx.cacheDir, "printer_cfg_upload.cfg")
                    temp.writeText(copy.toText())

                    val ok = SshBackups.uploadWithVerify(cfg, temp, appCtx.cacheDir)
                    if (!ok) return@withContext null to null

                    val list = runCatching { SshBackups.listBackups(cfg) }.getOrDefault(emptyList())
                    copy to list
                }

                if (uploadResult.first == null) {
                    _uiState.update { it.copy(busy = false, lastError = "upload_verify_failed") }
                    return@launch
                }

                val copy = uploadResult.first!!
                val list = uploadResult.second!!
                _uiState.update {
                    it.copy(
                        busy = false,
                        config = copy,
                        rawText = copy.toText(),
                        configEdits = emptyMap(),
                        backups = list,
                        lastError = null,
                    )
                }
            } catch (e: Exception) {
                _uiState.update { it.copy(busy = false, lastError = e.formatDiagnostic()) }
            }
        }
    }

    fun copyMeshToClipboard(context: Context) {
        val mesh = _uiState.value.mesh ?: return
        val sb = StringBuilder()
        for (y in 0 until mesh.yCount) {
            for (x in 0 until mesh.xCount) {
                if (x > 0) sb.append(' ')
                sb.append(String.format("%+.3f", mesh.z[y][x]))
            }
            sb.append('\n')
        }
        val clip = ClipData.newPlainText("bed_mesh", sb.toString())
        val cm = context.getSystemService(Context.CLIPBOARD_SERVICE) as ClipboardManager
        cm.setPrimaryClip(clip)
    }

    fun installPersistentSsh(context: Context) {
        if (_uiState.value.installSsh.busy) return
        val cfg = _uiState.value.ssh
        val appCtx = context.applicationContext
        viewModelScope.launch {
            _uiState.update { it.copy(installSsh = InstallState(busy = true)) }
            try {
                withContext(Dispatchers.IO) {
                    SshInstaller.installPersistentSsh(appCtx, cfg) { msg ->
                        _uiState.update { s ->
                            s.copy(installSsh = s.installSsh.copy(log = s.installSsh.log + msg))
                        }
                    }
                }
                _uiState.update { it.copy(installSsh = it.installSsh.copy(busy = false, done = true)) }
            } catch (e: Exception) {
                _uiState.update { it.copy(installSsh = it.installSsh.copy(busy = false, error = e.formatDiagnostic())) }
            }
        }
    }

    fun installWebPanel(context: Context) {
        if (_uiState.value.installPanel.busy) return
        val cfg = _uiState.value.ssh
        val appCtx = context.applicationContext
        viewModelScope.launch {
            _uiState.update { it.copy(installPanel = InstallState(busy = true)) }
            try {
                withContext(Dispatchers.IO) {
                    SshInstaller.installWebPanel(appCtx, cfg) { msg ->
                        _uiState.update { s ->
                            s.copy(installPanel = s.installPanel.copy(log = s.installPanel.log + msg))
                        }
                    }
                }
                _uiState.update { it.copy(installPanel = it.installPanel.copy(busy = false, done = true)) }
            } catch (e: Exception) {
                _uiState.update { it.copy(installPanel = it.installPanel.copy(busy = false, error = e.formatDiagnostic())) }
            }
        }
    }

    fun checkUpdates() {
        if (_uiState.value.update.checking) return
        val cur = _uiState.value.update.currentVersion
        viewModelScope.launch {
            _uiState.update {
                it.copy(
                    update = it.update.copy(
                        checking = true,
                        error = null,
                        // Сбрасываем данные загрузки при новой проверке
                        downloading = false,
                        downloadProgress = null,
                        downloadedApkPath = null,
                        apkUrl = null,
                    ),
                )
            }
            val (tag, err) = withContext(Dispatchers.IO) { GithubUpdater.checkLatestReleaseTag(cur) }
            if (tag != null) {
                val available = GithubUpdater.isNewVersion(cur, tag)
                val (apkUrl, apkErr) = if (available) {
                    withContext(Dispatchers.IO) { GithubUpdater.findApkDownloadUrlForTag(tag) }
                } else {
                    null to null
                }
                _uiState.update {
                    it.copy(
                        update = it.update.copy(
                            checking = false,
                            latestTag = tag,
                            updateAvailable = available,
                            apkUrl = apkUrl,
                            error = apkErr,
                        ),
                    )
                }
            } else {
                _uiState.update { it.copy(update = it.update.copy(checking = false, error = err ?: "error")) }
            }
        }
    }

    fun downloadAndInstallUpdate(context: Context) {
        val st = _uiState.value.update
        if (st.downloading) return

        val appCtx = context.applicationContext

        // Если APK уже скачан (возврат из настроек разрешений) — сразу устанавливаем
        val cachedPath = st.downloadedApkPath
        if (cachedPath != null) {
            val cachedFile = File(cachedPath)
            if (cachedFile.exists()) {
                launchInstallIntent(appCtx, cachedFile)
                return
            }
        }

        val url = st.apkUrl
        if (url.isNullOrBlank()) return

        viewModelScope.launch {
            _uiState.update { it.copy(update = it.update.copy(downloading = true, downloadProgress = 0f, error = null)) }
            try {
                val outFile = withContext(Dispatchers.IO) {
                    val req = okhttp3.Request.Builder()
                        .url(url)
                        .header("User-Agent", "rkfsociety-bedmesh-android")
                        .build()
                    val client = okhttp3.OkHttpClient()
                    client.newCall(req).execute().use { resp ->
                        if (!resp.isSuccessful) throw IllegalStateException("http_${resp.code}")
                        val body = resp.body ?: throw IllegalStateException("empty_body")
                        val total = body.contentLength().takeIf { it > 0 }

                        val name = "bedmesh-${st.latestTag ?: "update"}.apk"
                        val out = File(appCtx.cacheDir, name)
                        body.byteStream().use { input ->
                            out.outputStream().use { output ->
                                val buf = ByteArray(64 * 1024)
                                var read: Int
                                var done = 0L
                                while (true) {
                                    read = input.read(buf)
                                    if (read <= 0) break
                                    output.write(buf, 0, read)
                                    done += read.toLong()
                                    if (total != null) {
                                        val p = (done.toDouble() / total.toDouble()).toFloat().coerceIn(0f, 1f)
                                        _uiState.update { s ->
                                            s.copy(update = s.update.copy(downloadProgress = p))
                                        }
                                    }
                                }
                                output.flush()
                            }
                        }
                        out
                    }
                }

                _uiState.update {
                    it.copy(update = it.update.copy(downloading = false, downloadProgress = 1f, downloadedApkPath = outFile.absolutePath))
                }

                launchInstallIntent(appCtx, outFile)
            } catch (e: Exception) {
                _uiState.update {
                    it.copy(update = it.update.copy(downloading = false, downloadProgress = null, error = e.formatDiagnostic()))
                }
            }
        }
    }

    private fun launchInstallIntent(context: Context, apkFile: File) {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            if (!context.packageManager.canRequestPackageInstalls()) {
                val intent = Intent(android.provider.Settings.ACTION_MANAGE_UNKNOWN_APP_SOURCES).apply {
                    data = Uri.parse("package:${context.packageName}")
                    addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
                }
                context.startActivity(intent)
                return // пользователь вернётся и нажмёт кнопку снова — файл уже есть, идём сразу на установку
            }
        }
        val apkUri = FileProvider.getUriForFile(context, "${context.packageName}.fileprovider", apkFile)
        val installIntent = Intent(Intent.ACTION_VIEW).apply {
            setDataAndType(apkUri, "application/vnd.android.package-archive")
            addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
            addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
        }
        context.startActivity(installIntent)
    }
}

