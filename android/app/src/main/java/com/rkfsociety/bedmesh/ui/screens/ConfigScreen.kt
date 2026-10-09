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
import com.rkfsociety.bedmesh.core.NozzleSettings
import com.rkfsociety.bedmesh.core.displayBedMeshPairValue
import com.rkfsociety.bedmesh.core.currentAceProLabel
import com.rkfsociety.bedmesh.core.resolveSection
import com.rkfsociety.bedmesh.core.probeCountAllowsLagrange
import com.rkfsociety.bedmesh.ui.vm.UiState

private data class FieldDef(
    val key: String,
    val label: String,
    val placeholder: String,
    val defaultValue: String,
    val hint: String,
)

/** Те же поля, что в `win/pyqt6/ui/locale/ru.json` → `config.sections.bed_mesh.fields`. */
private val BED_MESH_WHITELIST = listOf(
    FieldDef("speed", "Скорость измерения", "300", "300", "Скорость перемещения при построении bed mesh."),
    FieldDef("horizontal_move_z", "Высота горизонтального перемещения", "3", "3", "Высота подъёма сопла между точками измерения."),
    FieldDef("mesh_min", "Мин. координаты (X,Y)", "5,5", "5,5", "Левый нижний угол области."),
    FieldDef("mesh_max", "Макс. координаты (X,Y)", "245,245", "245,245", "Правый верхний угол области."),
    FieldDef("probe_count", "Кол-во точек (X,Y)", "10,10", "5,5", "Одно число применяется и к X, и к Y. При значении больше 5 используется bicubic."),
)

private val PROBE_FIELDS = listOf(
    FieldDef("speed", "Скорость измерения", "4.0", "4.0", "Скорость опускания щупа."),
    FieldDef("lift_speed", "Скорость подъёма", "4.0", "4.0", "Скорость подъёма щупа."),
    FieldDef("final_speed", "Финальная скорость", "4.0", "4.0", "Финальная скорость измерения."),
)

private val PRINTER_FIELDS = listOf(
    FieldDef("max_z_velocity", "Максимальная скорость Z", "15", "15", "Максимальная скорость оси Z."),
    FieldDef("max_z_accel", "Максимальное ускорение Z", "1000", "1000", "Максимальное ускорение оси Z."),
)

private val STEPPER_Z_FIELDS = listOf(
    FieldDef("homing_speed", "Скорость хоуминга Z", "6", "6", "Скорость первого прохода хоуминга оси Z."),
    FieldDef("second_homing_speed", "Скорость повторного хоуминга Z", "3", "3", "Скорость повторного прохода хоуминга оси Z."),
    FieldDef("homing_retract_dist", "Откат при хоуминге Z", "4", "4", "Расстояние отката перед повторным проходом хоуминга."),
)

private val SAFE_Z_HOME_FIELDS = listOf(
    FieldDef("z_hop", "Z-hop", "4.0", "4.0", "Высота подъёма перед перемещением к точке хоуминга."),
    FieldDef("z_hop_speed", "Скорость Z-hop", "8.0", "8.0", "Скорость подъёма Z перед хоумингом."),
    FieldDef("z_homed_pos", "Позиция Z после хоуминга", "10", "10", "Позиция Z после завершения хоуминга."),
    FieldDef("z_hop_finish_pos", "Финальная позиция Z-hop", "0", "0", "Позиция Z после завершения подъёма."),
)

/** Поля секции [leviQ3] — температуры калибровки стола. */
private val LEVI_Q3_WHITELIST = listOf(
    FieldDef("bed_temp",          "Температура стола (°C)",           "60", "55", "Температура стола во время снятия карты."),
    FieldDef("extru_temp",        "Температура экструдера (°C)",       "200", "200", "Температура экструдера при калибровке."),
    FieldDef("extru_end_temp",    "Конечная темп. экструдера (°C)",    "150", "150", "Температура после завершения калибровки."),
    FieldDef("preheat_leveling",  "Предпрогрев выравнивания (°C)",    "60", "60", "Температура предпрогрева перед выравниванием."),
)

private val ACE_PRESETS = listOf(100, 150, 200, 250, 300, 400, 500)

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
    onNozzleDiameter: (String) -> Unit,
    onNozzleMaterial: (String) -> Unit,
    onNozzleFullCalibration: (Boolean) -> Unit,
    onApplyNozzle: () -> Unit,
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
                busy = state.busy || state.nozzleBusy || state.liveCalibration.running,
                onRefresh = onRefreshBackups,
                onCreate = onCreateBackup,
                onRestore = onRestoreBackup,
                onDelete = onDeleteBackup,
            )

            Row(horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                Button(onClick = onSave, enabled = !state.busy && !state.nozzleBusy && !state.liveCalibration.running) {
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

            listOf(
                Triple("probe", "🔎 Настройки измерительного щупа", PROBE_FIELDS),
                Triple("printer", "🖨️ Ограничения движения Z", PRINTER_FIELDS),
                Triple("stepper_z", "🧭 Хоуминг оси Z", STEPPER_Z_FIELDS),
                Triple("safe_z_home", "🏠 Z-hop и безопасный хоуминг", SAFE_Z_HOME_FIELDS),
            ).forEach { (name, title, fields) ->
                val section = cfg.resolveSection(name) ?: return@forEach
                ConfigFieldsCard(
                    title = title,
                    cfg = cfg,
                    section = section,
                    fields = fields,
                    edits = state.configEdits,
                    onFieldChange = { key, value -> onUpdateField(section, key, value) },
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
                val section = cfg.resolveSection("filament_hub")!!
                val (currentPercent, currentLabel) = currentAceProLabel(cfg.sections[section].orEmpty())
                FilamentHubAceProCard(
                    currentPercent = currentPercent,
                    currentLabel = currentLabel,
                    onPreset = onAceProPreset,
                )
            }

            NozzleSettingsCard(
                diameter = state.nozzleDiameter,
                material = state.nozzleMaterial,
                runFullCalibration = state.nozzleFullCalibration,
                busy = state.nozzleBusy || state.busy || state.liveCalibration.running || state.installPanel.busy || state.installSsh.busy,
                loaded = state.loadedNozzle != null,
                status = state.nozzleStatus,
                onDiameter = onNozzleDiameter,
                onMaterial = onNozzleMaterial,
                onFullCalibration = onNozzleFullCalibration,
                onApply = onApplyNozzle,
            )
        }
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun NozzleSettingsCard(
    diameter: String,
    material: String,
    runFullCalibration: Boolean,
    busy: Boolean,
    loaded: Boolean,
    status: String?,
    onDiameter: (String) -> Unit,
    onMaterial: (String) -> Unit,
    onFullCalibration: (Boolean) -> Unit,
    onApply: () -> Unit,
) {
    var diameterMenu by remember { mutableStateOf(false) }
    var materialMenu by remember { mutableStateOf(false) }
    var confirm by remember { mutableStateOf(false) }

    Card {
        Column(
            modifier = Modifier.padding(12.dp),
            verticalArrangement = Arrangement.spacedBy(8.dp),
        ) {
            Text("🧩 Сопло", style = MaterialTheme.typography.titleSmall)
            Text(
                "Сохраняются диаметр и материал. Применение создаёт резервные копии и полностью перезапускает принтер.",
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
            ExposedDropdownMenuBox(expanded = diameterMenu, onExpandedChange = { diameterMenu = !diameterMenu }) {
                OutlinedTextField(
                    value = "$diameter мм",
                    onValueChange = {},
                    readOnly = true,
                    enabled = !busy,
                    label = { Text("Диаметр сопла") },
                    modifier = Modifier.fillMaxWidth().menuAnchor(MenuAnchorType.PrimaryNotEditable, enabled = true),
                    trailingIcon = { ExposedDropdownMenuDefaults.TrailingIcon(expanded = diameterMenu) },
                )
                ExposedDropdownMenu(expanded = diameterMenu, onDismissRequest = { diameterMenu = false }) {
                    NozzleSettings.diameters.forEach { option ->
                        DropdownMenuItem(
                            text = { Text("$option мм") },
                            onClick = { onDiameter(option); diameterMenu = false },
                        )
                    }
                }
            }
            ExposedDropdownMenuBox(expanded = materialMenu, onExpandedChange = { materialMenu = !materialMenu }) {
                OutlinedTextField(
                    value = if (material == "hardened_steel") "Hardened Steel" else if (material == "brass") "Brass" else material,
                    onValueChange = {},
                    readOnly = true,
                    enabled = !busy,
                    label = { Text("Материал сопла") },
                    modifier = Modifier.fillMaxWidth().menuAnchor(MenuAnchorType.PrimaryNotEditable, enabled = true),
                    trailingIcon = { ExposedDropdownMenuDefaults.TrailingIcon(expanded = materialMenu) },
                )
                ExposedDropdownMenu(expanded = materialMenu, onDismissRequest = { materialMenu = false }) {
                    NozzleSettings.materials.forEach { option ->
                        DropdownMenuItem(
                            text = { Text(if (option == "hardened_steel") "Hardened Steel" else "Brass") },
                            onClick = { onMaterial(option); materialMenu = false },
                        )
                    }
                }
            }
            Row(verticalAlignment = androidx.compose.ui.Alignment.CenterVertically) {
                Checkbox(checked = runFullCalibration, onCheckedChange = onFullCalibration, enabled = !busy)
                Text("Полная калибровка после перезапуска")
            }
            if (!loaded) {
                Text("Сначала загрузите конфигурацию по SSH.", style = MaterialTheme.typography.bodySmall)
            }
            if (status != null) Text(status, style = MaterialTheme.typography.bodySmall)
            Button(
                onClick = { confirm = true },
                enabled = loaded && !busy,
                modifier = Modifier.fillMaxWidth(),
            ) {
                Text(if (busy) "Сохранение…" else "Сохранить и перезапустить")
            }
        }
    }

    if (confirm) {
        AlertDialog(
            onDismissRequest = { confirm = false },
            title = { Text("Применить сопло?") },
            text = {
                Text(
                    "Будет установлен вариант $material-$diameter мм, созданы резервные копии и выполнен полный перезапуск принтера. " +
                        if (runFullCalibration) "После загрузки запустится полная калибровка PID, шейперов и стола. Не выполнять во время печати."
                        else "Полная калибровка после загрузки запускаться не будет. Не выполнять во время печати.",
                )
            },
            confirmButton = {
                TextButton(onClick = { confirm = false; onApply() }) { Text("Продолжить") }
            },
            dismissButton = { TextButton(onClick = { confirm = false }) { Text("Отмена") } },
        )
    }
}

@Composable
private fun ConfigFieldsCard(
    title: String,
    cfg: KlipperConfig,
    section: String,
    fields: List<FieldDef>,
    edits: Map<String, String>,
    onFieldChange: (String, String) -> Unit,
) {
    val secMap = cfg.sections[section] ?: return
    val visibleFields = fields.filter { it.key in secMap }
    if (visibleFields.isEmpty()) return
    Card {
        Column(
            modifier = Modifier.padding(12.dp),
            verticalArrangement = Arrangement.spacedBy(10.dp),
        ) {
            Text(title, style = MaterialTheme.typography.titleSmall)
            visibleFields.forEach { def ->
                val mapKey = "$section.${def.key}"
                OutlinedTextField(
                    value = edits[mapKey] ?: secMap[def.key]?.value.orEmpty(),
                    onValueChange = { onFieldChange(def.key, it) },
                    label = { Text(def.label) },
                    placeholder = { Text(def.placeholder) },
                    modifier = Modifier.fillMaxWidth(),
                    singleLine = true,
                    supportingText = { Text("${def.hint} По умолчанию: ${def.defaultValue}.") },
                )
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
                    supportingText = { Text("${def.hint} По умолчанию в версии 2.7.2.7: ${def.defaultValue}.") },
                )
            }

            if ("algorithm" in secMap) {
                val rawAlg = secMap["algorithm"]?.value.orEmpty().trim()
                val mapKey = "$section.algorithm"
                val probeRaw = edits["$section.probe_count"] ?: secMap["probe_count"]?.value.orEmpty()
                val allowLagrange = probeCountAllowsLagrange(probeRaw)
                val current = (edits[mapKey] ?: rawAlg).trim().ifEmpty { "lagrange" }
                val displayedCurrent = if (!allowLagrange && current == "lagrange") "bicubic" else current
                var expanded by remember { mutableStateOf(false) }
                val options = if (allowLagrange) listOf("lagrange", "bicubic") else listOf("bicubic")
                ExposedDropdownMenuBox(expanded = expanded, onExpandedChange = { expanded = !expanded }) {
                    OutlinedTextField(
                        value = displayedCurrent,
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
                Text(
                    "Метод интерполяции. Lagrange доступен только для 5×5 и меньше. По умолчанию в версии 2.7.2.7: lagrange.",
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )
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
                    supportingText = { Text("${def.hint} По умолчанию в версии 2.7.2.7: ${def.defaultValue}.") },
                )
            }
        }
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun FilamentHubAceProCard(
    currentPercent: Int?,
    currentLabel: String?,
    onPreset: (Int) -> Unit,
) {
    var expanded by remember { mutableStateOf(false) }
    var selectedPct by remember(currentPercent, currentLabel) { mutableIntStateOf(currentPercent ?: 100) }
    var observedLabel by remember(currentPercent, currentLabel) { mutableStateOf(currentLabel) }

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
                    value = observedLabel ?: "$selectedPct%",
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
                                observedLabel = null
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
