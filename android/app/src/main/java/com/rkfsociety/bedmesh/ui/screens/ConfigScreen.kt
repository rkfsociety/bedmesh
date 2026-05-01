package com.rkfsociety.bedmesh.ui.screens

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.unit.dp
import com.rkfsociety.bedmesh.core.KlipperConfig
import com.rkfsociety.bedmesh.ui.vm.UiState

@Composable
fun ConfigScreen(
    state: UiState,
    onUpdateField: (String, String, String) -> Unit,
    onSave: () -> Unit,
    onRefreshBackups: () -> Unit,
    onCreateBackup: () -> Unit,
    onRestoreBackup: (String) -> Unit,
    onDeleteBackup: (String) -> Unit,
) {
    val cfg = state.config
    Column(verticalArrangement = Arrangement.spacedBy(10.dp)) {
        Text("Настройки принтера", style = MaterialTheme.typography.titleMedium)

        if (cfg == null) {
            Text("Сначала загрузите printer.cfg по SSH.", style = MaterialTheme.typography.bodyMedium)
            return
        }

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

        Divider()
        Text("Редактируемые секции: [bed_mesh], [filament_hub]", style = MaterialTheme.typography.bodySmall)

        SectionEditor(
            cfg = cfg,
            section = "bed_mesh",
            edits = state.configEdits,
            onUpdateField = onUpdateField,
        )
        SectionEditor(
            cfg = cfg,
            section = "filament_hub",
            edits = state.configEdits,
            onUpdateField = onUpdateField,
        )
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
                Button(onClick = onCreate, enabled = !busy) { Text("Создать") }
                Button(onClick = { selected?.let(onRestore) }, enabled = !busy && selected != null) { Text("Восстановить") }
                OutlinedButton(onClick = { selected?.let(onDelete) }, enabled = !busy && selected != null) { Text("Удалить") }
            }
            if (backups.isEmpty()) {
                Text("Бекапов нет.", style = MaterialTheme.typography.bodySmall)
            } else {
                // Keep it simple: dropdown selector
                var expanded by remember { mutableStateOf(false) }
                ExposedDropdownMenuBox(expanded = expanded, onExpandedChange = { expanded = !expanded }) {
                    OutlinedTextField(
                        value = selected ?: "",
                        onValueChange = {},
                        readOnly = true,
                        label = { Text("Выбранный бекап") },
                        modifier = Modifier
                            .fillMaxWidth()
                            .menuAnchor(),
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

@Composable
private fun SectionEditor(
    cfg: KlipperConfig,
    section: String,
    edits: Map<String, String>,
    onUpdateField: (String, String, String) -> Unit,
) {
    val sec = cfg.sections.keys.firstOrNull { it == section || it.startsWith("$section ") } ?: return
    val keys = cfg.sections[sec]?.keys?.toList()?.sorted() ?: return
    if (keys.isEmpty()) return

    Card {
        Column(modifier = Modifier.padding(12.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
            Text("[$sec]", style = MaterialTheme.typography.titleSmall)

            LazyColumn(
                modifier = Modifier.fillMaxWidth().heightIn(max = 380.dp),
                verticalArrangement = Arrangement.spacedBy(8.dp),
            ) {
                items(keys) { key ->
                    val mapKey = "$sec.$key"
                    val current = edits[mapKey] ?: cfg.sections[sec]?.get(key)?.value.orEmpty()
                    OutlinedTextField(
                        value = current,
                        onValueChange = { onUpdateField(sec, key, it) },
                        label = { Text(key) },
                        modifier = Modifier.fillMaxWidth(),
                        singleLine = true,
                    )
                }
            }
        }
    }
}

