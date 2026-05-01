package com.rkfsociety.bedmesh.ui.vm

import android.content.ClipData
import android.content.ClipboardManager
import android.content.Context
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.rkfsociety.bedmesh.core.GithubUpdater
import com.rkfsociety.bedmesh.core.KlipperConfig
import com.rkfsociety.bedmesh.core.MeshParser
import com.rkfsociety.bedmesh.core.MeshStatsCalculator
import com.rkfsociety.bedmesh.core.SshClient
import com.rkfsociety.bedmesh.core.SshBackups
import com.rkfsociety.bedmesh.core.SshConfig
import com.rkfsociety.bedmesh.core.UpdateState
import com.rkfsociety.bedmesh.model.BedMeshData
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch
import java.io.File

data class UiState(
    val ssh: SshConfig = SshConfig(ip = "192.168.", port = 2222, user = "root", password = "rockchip", path = "/userdata/app/gk/printer.cfg"),
    val busy: Boolean = false,
    val rawText: String = "",
    val mesh: BedMeshData? = null,
    val stats: Map<String, String> = emptyMap(),
    val config: KlipperConfig? = null,
    val configEdits: Map<String, String> = emptyMap(), // key: "section.key"
    val backups: List<String> = emptyList(),
    val update: UpdateState = UpdateState(currentVersion = "0.1.0-android"),
    val lastError: String? = null,
)

class AppViewModel : ViewModel() {
    private val _uiState = MutableStateFlow(UiState())
    val uiState: StateFlow<UiState> = _uiState

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
            st.copy(ssh = next)
        }
    }

    fun downloadViaSsh(context: Context) {
        val cfg = _uiState.value.ssh
        viewModelScope.launch {
            _uiState.update { it.copy(busy = true, lastError = null) }
            try {
                val file = SshClient.downloadFile(context, cfg, cfg.path)
                val text = file.readText()

                val parsedCfg = KlipperConfig.parse(text)
                val backups = runCatching { SshBackups.listBackups(cfg) }.getOrDefault(emptyList())

                // mirror Windows behavior: if no mesh points found in printer.cfg, try printer_mutable.cfg
                var parsed = MeshParser.parseText(text)
                var rawText = text
                if (parsed == null && cfg.path.endsWith("printer.cfg")) {
                    val mutablePath = "/userdata/app/gk/printer_mutable.cfg"
                    val alt = SshClient.downloadFile(context, cfg, mutablePath)
                    val altText = alt.readText()
                    val altParsed = MeshParser.parseText(altText)
                    if (altParsed != null) {
                        parsed = altParsed
                        rawText = altText
                    }
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
                        "front_right_mm" to String.format("%+.3f", s.frontRight),
                        "front_right_turns" to String.format("%.2f", s.turnsFor(s.frontRight)),
                        "back_center_mm" to String.format("%+.3f", s.backCenter),
                        "back_center_turns" to String.format("%.2f", s.turnsFor(s.backCenter)),
                    )
                } else {
                    emptyMap()
                }

                _uiState.update {
                    it.copy(
                        busy = false,
                        rawText = rawText,
                        mesh = parsed,
                        stats = stats,
                        config = parsedCfg,
                        configEdits = emptyMap(),
                        backups = backups,
                        lastError = if (parsed == null) "Не найден bed_mesh в файле" else null,
                    )
                }
            } catch (e: Exception) {
                _uiState.update { it.copy(busy = false, lastError = e.message ?: "ошибка") }
            }
        }
    }

    fun updateConfigField(section: String, key: String, value: String) {
        val mapKey = "$section.$key"
        _uiState.update { st ->
            st.copy(configEdits = st.configEdits + (mapKey to value))
        }
    }

    fun refreshBackups() {
        val cfg = _uiState.value.ssh
        viewModelScope.launch {
            _uiState.update { it.copy(busy = true, lastError = null) }
            try {
                val list = SshBackups.listBackups(cfg)
                _uiState.update { it.copy(busy = false, backups = list) }
            } catch (e: Exception) {
                _uiState.update { it.copy(busy = false, lastError = e.message ?: "ошибка") }
            }
        }
    }

    fun createBackup() {
        val cfg = _uiState.value.ssh
        viewModelScope.launch {
            _uiState.update { it.copy(busy = true, lastError = null) }
            try {
                SshBackups.createBackup(cfg)
                val list = SshBackups.listBackups(cfg)
                _uiState.update { it.copy(busy = false, backups = list) }
            } catch (e: Exception) {
                _uiState.update { it.copy(busy = false, lastError = e.message ?: "ошибка") }
            }
        }
    }

    fun restoreBackup(path: String) {
        val cfg = _uiState.value.ssh
        viewModelScope.launch {
            _uiState.update { it.copy(busy = true, lastError = null) }
            try {
                val ok = SshBackups.restoreBackup(cfg, path)
                _uiState.update { it.copy(busy = false, lastError = if (!ok) "restore_failed" else null) }
            } catch (e: Exception) {
                _uiState.update { it.copy(busy = false, lastError = e.message ?: "ошибка") }
            }
        }
    }

    fun deleteBackup(path: String) {
        val cfg = _uiState.value.ssh
        viewModelScope.launch {
            _uiState.update { it.copy(busy = true, lastError = null) }
            try {
                val ok = SshBackups.deleteBackup(cfg, path)
                val list = SshBackups.listBackups(cfg)
                _uiState.update { it.copy(busy = false, backups = list, lastError = if (!ok) "delete_failed" else null) }
            } catch (e: Exception) {
                _uiState.update { it.copy(busy = false, lastError = e.message ?: "ошибка") }
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
        viewModelScope.launch {
            _uiState.update { it.copy(busy = true, lastError = null) }
            try {
                // Apply edits into a copy (keep original usable until upload succeeds)
                val copy = KlipperConfig(base.rawLines.toMutableList(), base.sections.toMutableMap().mapValues { it.value.toMutableMap() }.toMutableMap())
                for ((k, v) in st.configEdits) {
                    val parts = k.split(".", limit = 2)
                    if (parts.size == 2) copy.setValue(parts[0], parts[1], v)
                }

                // Best-effort backup first (like desktop)
                SshBackups.createBackup(cfg)

                val temp = File(context.cacheDir, "printer_cfg_upload.cfg")
                temp.writeText(copy.toText())

                val ok = SshBackups.uploadWithVerify(cfg, temp, context.cacheDir)
                if (!ok) {
                    _uiState.update { it.copy(busy = false, lastError = "upload_verify_failed") }
                    return@launch
                }

                val list = runCatching { SshBackups.listBackups(cfg) }.getOrDefault(emptyList())
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
                _uiState.update { it.copy(busy = false, lastError = e.message ?: "ошибка") }
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

    fun checkUpdates() {
        val cur = _uiState.value.update.currentVersion
        viewModelScope.launch {
            _uiState.update { it.copy(update = it.update.copy(checking = true, error = null)) }
            val (tag, err) = GithubUpdater.checkLatestReleaseTag(cur)
            if (tag != null) {
                val available = GithubUpdater.isNewVersion(cur, tag)
                _uiState.update {
                    it.copy(
                        update = it.update.copy(
                            checking = false,
                            latestTag = tag,
                            updateAvailable = available,
                            error = null,
                        ),
                    )
                }
            } else {
                _uiState.update { it.copy(update = it.update.copy(checking = false, error = err ?: "error")) }
            }
        }
    }
}

