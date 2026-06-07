package com.rkfsociety.bedmesh.ui.screens

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.unit.sp
import androidx.compose.ui.unit.dp
import com.rkfsociety.bedmesh.core.KlipperConfig
import com.rkfsociety.bedmesh.core.displayBedMeshPairValue
import com.rkfsociety.bedmesh.core.resolveSection
import com.rkfsociety.bedmesh.ui.vm.UiState

private data class FieldDef(val key: String, val label: String, val placeholder: String)

/** Те же поля, что в `win/pyqt6/ui/locale/ru.json` → `config.sections.bed_mesh.fields`. */
private val BED_MESH_WHITELIST = listOf(
    FieldDef("mesh_min", "Мин. координаты (X,Y)", "5,5"),
    FieldDef("mesh_max", "Макс. координаты (X,Y)", "245,245"),
    FieldDef("probe_count", "Кол-во точек (X,Y)", "10,10"),
)

/** Поля секции [leviQ3] — температуры калибровки стола. */
private val LEVI_Q3_WHITELIST = listOf(
    FieldDef("bed_temp",          "Температура стола (°C)",           "60"),
    FieldDef("extru_temp",        "Температура экструдера (°C)",       "200"),
    FieldDef("extru_end_temp",    "Конечная темп. экструдера (°C)",    "150"),
    FieldDef("preheat_leveling",  "Предпрогрев выравнивания (°C)",    "60"),
)

private val ACE_PRESETS = listOf(100, 150, 200, 250, 300)

@Composable
fun ConfigScreen(
    state: UiState,
    onUpdateField: (String, String, String) -> Unit,
    onSave: () -> Unit,
    onRefreshBackups: () -> Unit,
    onCreateBackup: () -> Unit,
    onRestoreBackup: (String) -> Unit,
    onDeleteBackup: (String) -> Unit,
    onAceProPreset: (Int) -> Unit,
    modifier: Modifier = Modifier,
) {
    val cfg = state.config
    val scroll = rememberScrollState()
    Column(
        modifier
            .fillMaxWidth()
            .verticalScroll(scroll),
        verticalArrangement = Arrangement.spacedBy(10.dp),
    ) {
        Text("Настройки принтера", style = MaterialTheme.typography.titleMedium)

        if (cfg == null) {
            Text("Сначала загрузите printer.cfg по SSH.", style = MaterialTheme.typography.bodyMedium)
        } else {
            BackupPanel(
                backups = state.backups,
                busy = state.busy,
                onRefresh = onRefreshBackups,
                onCreate = onCreateBackup,
                onRestore = onRestoreBackup,
                onDelete = onDeleteBackup,
            )

            Row(horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                Button(onClick = onSave, enabled = !state.busy) {
                    Text(if (state.busy) "Сохранение..." else "Сохранить на принтер")
                }
                Text(
                    "Будет создан бекап перед загрузкой.",
                    style = MaterialTheme.typography.bodySmall,
                    fontFamily = FontFamily.Monospace,
                )
            }

            val bedSec = cfg.resolveSection("bed_mesh")
            if (bedSec != null) {
                BedMeshSectionCard(
                    cfg = cfg,
                    section = bedSec,
                    edits = state.configEdits,
                    onFieldChange = { key, value -> onUpdateField(bedSec, key, value) },
                )
            }

            val leviSec = cfg.resolveSection("leviQ3")
            if (leviSec != null) {
                LeviQ3SectionCard(
                    cfg = cfg,
                    section = leviSec,
                    edits = state.configEdits,
                    onFieldChange = { key, value -> onUpdateField(leviSec, key, value) },
                )
            }

            if (cfg.resolveSection("filament_hub") != null) {
                FilamentHubAceProCard(onPreset = onAceProPreset)
            }
        }
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun BedMeshSectionCard(
    cfg: KlipperConfig,
    section: String,
    edits: Map<String, String>,
    onFieldChange: (String, String) -> Unit,
) {
    val secMap = cfg.sections[section] ?: return
    var hasAny = false
    for (def in BED_MESH_WHITELIST) {
        if (def.key in secMap) {
            hasAny = true
            break
        }
    }
    if ("algorithm" in secMap) hasAny = true
    if (!hasAny) return

    Card {
        Column(
            modifier = Modifier.padding(12.dp),
            verticalArrangement = Arrangement.spacedBy(10.dp),
        ) {
            Text("📦 Настройки снятия карты стола", style = MaterialTheme.typography.titleSmall)

            for (def in BED_MESH_WHITELIST) {
                if (def.key !in secMap) continue
                val raw = secMap[def.key]?.value.orEmpty()
                val mapKey = "$section.${def.key}"
                val shown = edits[mapKey] ?: displayBedMeshPairValue(def.key, raw)
                OutlinedTextField(
                    value = shown,
                    onValueChange = { onFieldChange(def.key, it) },
                    label = { Text(def.label) },
                    placeholder = { Text(def.placeholder) },
                    modifier = Modifier.fillMaxWidth(),
                    singleLine = true,
                )
            }

            if ("algorithm" in secMap) {
                val rawAlg = secMap["algorithm"]?.value.orEmpty().trim()
                val mapKey = "$section.algorithm"
                val current = (edits[mapKey] ?: rawAlg).trim().ifEmpty { "lagrange" }
                var expanded by remember { mutableStateOf(false) }
                val options = listOf("lagrange", "bicubic")
                ExposedDropdownMenuBox(expanded = expanded, onExpandedChange = { expanded = !expanded }) {
                    OutlinedTextField(
                        value = current,
                        onValueChange = {},
                        readOnly = true,
                        label = { Text("Алгоритм") },
                        modifier = Modifier
                            .fillMaxWidth()
                            .menuAnchor(MenuAnchorType.PrimaryNotEditable, enabled = true),
                        trailingIcon = { ExposedDropdownMenuDefaults.TrailingIcon(expanded = expanded) },
                    )
                    ExposedDropdownMenu(expanded = expanded, onDismissRequest = { expanded = false }) {
                        options.forEach { opt ->
                            DropdownMenuItem(
                                text = { Text(opt) },
                                onClick = {
                                    onFieldChange("algorithm", opt)
                                    expanded = false
                                },
                            )
                        }
                    }
                }
            }
        }
    }
}

@Composable
private fun LeviQ3SectionCard(
    cfg: KlipperConfig,
    section: String,
    edits: Map<String, String>,
    onFieldChange: (String, String) -> Unit,
) {
    val secMap = cfg.sections[section] ?: return
    val visibleFields = LEVI_Q3_WHITELIST.filter { it.key in secMap }
    if (visibleFields.isEmpty()) return

    Card {
        Column(
            modifier = Modifier.padding(12.dp),
            verticalArrangement = Arrangement.spacedBy(10.dp),
        ) {
            Text("🌡️ Температуры калибровки стола", style = MaterialTheme.typography.titleSmall)
            for (def in visibleFields) {
                val raw = secMap[def.key]?.value.orEmpty()
                val mapKey = "$section.${def.key}"
                val shown = edits[mapKey] ?: raw
                OutlinedTextField(
                    value = shown,
                    onValueChange = { onFieldChange(def.key, it) },
                    label = { Text(def.label) },
                    placeholder = { Text(def.placeholder) },
                    modifier = Modifier.fillMaxWidth(),
                    singleLine = true,
                )
            }
        }
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun FilamentHubAceProCard(onPreset: (Int) -> Unit) {
    var expanded by remember { mutableStateOf(false) }
    var selectedPct by remember { mutableIntStateOf(100) }

    Card {
        Column(
            modifier = Modifier.padding(12.dp),
            verticalArrangement = Arrangement.spacedBy(8.dp),
        ) {
            Text("🚀 Ace Pro (скорости подачи/отката)", style = MaterialTheme.typography.titleSmall)
            Text(
                "Ускорение относительно базовых скоростей (как в Windows). Записываются только ключи, уже есть в [filament_hub].",
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
            ExposedDropdownMenuBox(expanded = expanded, onExpandedChange = { expanded = !expanded }) {
                OutlinedTextField(
                    value = "$selectedPct%",
                    onValueChange = {},
                    readOnly = true,
                    label = { Text("Ускорение Ace Pro") },
                    modifier = Modifier
                        .fillMaxWidth()
                        .menuAnchor(MenuAnchorType.PrimaryNotEditable, enabled = true),
                    trailingIcon = { ExposedDropdownMenuDefaults.TrailingIcon(expanded = expanded) },
                )
                ExposedDropdownMenu(expanded = expanded, onDismissRequest = { expanded = false }) {
                    ACE_PRESETS.forEach { pct ->
                        DropdownMenuItem(
                            text = { Text("$pct%") },
                            onClick = {
                                selectedPct = pct
                                onPreset(pct)
                                expanded = false
                            },
                        )
                    }
                }
            }
        }
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun BackupPanel(
    backups: List<String>,
    busy: Boolean,
    onRefresh: () -> Unit,
    onCreate: () -> Unit,
    onRestore: (String) -> Unit,
    onDelete: (String) -> Unit,
) {
    var selected by remember(backups) { mutableStateOf(backups.firstOrNull()) }

    Card {
        Column(modifier = Modifier.padding(12.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
            Row {
                Text("Бекапы printer.cfg", style = MaterialTheme.typography.titleSmall, modifier = Modifier.weight(1f))
                TextButton(onClick = onRefresh, enabled = !busy) { Text("Обновить") }
            }
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                val buttonText = MaterialTheme.typography.labelLarge.copy(fontSize = 12.sp)
                val tightPadding = PaddingValues(horizontal = 10.dp, vertical = 8.dp)

                Button(
                    onClick = onCreate,
                    enabled = !busy,
                    contentPadding = tightPadding,
                ) {
                    Text("Создать", style = buttonText, maxLines = 1, softWrap = false, overflow = TextOverflow.Ellipsis)
                }
                Button(
                    onClick = { selected?.let(onRestore) },
                    enabled = !busy && selected != null,
                    contentPadding = tightPadding,
                ) {
                    Text("Восстановить", style = buttonText, maxLines = 1, softWrap = false, overflow = TextOverflow.Ellipsis)
                }
                OutlinedButton(
                    onClick = { selected?.let(onDelete) },
                    enabled = !busy && selected != null,
                    contentPadding = tightPadding,
                ) {
                    Text("Удалить", style = buttonText, maxLines = 1, softWrap = false, overflow = TextOverflow.Ellipsis)
                }
            }
            if (backups.isEmpty()) {
                Text("Бекапов нет.", style = MaterialTheme.typography.bodySmall)
            } else {
                var expanded by remember { mutableStateOf(false) }
                ExposedDropdownMenuBox(expanded = expanded, onExpandedChange = { expanded = !expanded }) {
                    OutlinedTextField(
                        value = selected ?: "",
                        onValueChange = {},
                        readOnly = true,
                        label = { Text("Выбранный бекап") },
                        modifier = Modifier
                            .fillMaxWidth()
                            .menuAnchor(MenuAnchorType.PrimaryNotEditable, enabled = true),
                        trailingIcon = { ExposedDropdownMenuDefaults.TrailingIcon(expanded = expanded) },
                    )
                    ExposedDropdownMenu(expanded = expanded, onDismissRequest = { expanded = false }) {
                        backups.forEach { p ->
                            DropdownMenuItem(
                                text = { Text(p) },
                                onClick = {
                                    selected = p
                                    expanded = false
                                },
                            )
                        }
                    }
                }
            }
        }
    }
}
