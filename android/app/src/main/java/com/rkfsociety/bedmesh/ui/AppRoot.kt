package com.rkfsociety.bedmesh.ui

import androidx.compose.foundation.layout.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.unit.dp
import androidx.lifecycle.viewmodel.compose.viewModel
import com.rkfsociety.bedmesh.ui.screens.MeshScreen
import com.rkfsociety.bedmesh.ui.screens.ConfigScreen
import com.rkfsociety.bedmesh.ui.screens.RawScreen
import com.rkfsociety.bedmesh.ui.screens.SshScreen
import com.rkfsociety.bedmesh.ui.vm.AppViewModel

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun AppRoot(vm: AppViewModel = viewModel()) {
    val state by vm.uiState.collectAsState()
    val ctx = LocalContext.current

    var tab by remember { mutableIntStateOf(0) }
    val tabs = listOf("SSH", "Карта", "Config", "RAW")

    Scaffold(
        modifier = Modifier.fillMaxSize(),
        containerColor = MaterialTheme.colorScheme.background,
        contentColor = MaterialTheme.colorScheme.onBackground,
        topBar = {
            TopAppBar(
                title = { Text("BedMesh Visualizer") },
                actions = {
                    if (state.update.checking) {
                        CircularProgressIndicator(
                            modifier = Modifier
                                .padding(end = 12.dp)
                                .size(18.dp),
                            strokeWidth = 2.dp,
                        )
                    } else if (state.update.downloading) {
                        CircularProgressIndicator(
                            modifier = Modifier
                                .padding(end = 12.dp)
                                .size(18.dp),
                            strokeWidth = 2.dp,
                        )
                    } else if (state.update.updateAvailable && state.update.latestTag != null) {
                        TextButton(onClick = { vm.downloadAndInstallUpdate(ctx) }) {
                            Text("Обновить")
                        }
                    }
                },
            )
        },
        bottomBar = {
            NavigationBar(
                containerColor = MaterialTheme.colorScheme.surface,
            ) {
                tabs.forEachIndexed { i, label ->
                    NavigationBarItem(
                        selected = tab == i,
                        onClick = { tab = i },
                        icon = {},
                        label = { Text(label) },
                    )
                }
            }
        },
    ) { padding ->
        Column(
            modifier = Modifier
                .padding(padding)
                .fillMaxSize()
                .padding(12.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp),
        ) {
            if (state.update.updateAvailable && state.update.latestTag != null) {
                Card(colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.secondaryContainer)) {
                    Row(
                        modifier = Modifier
                            .fillMaxWidth()
                            .padding(12.dp),
                        verticalAlignment = Alignment.CenterVertically,
                    ) {
                        Column(modifier = Modifier.weight(1f)) {
                            Text("Требуется обновление", style = MaterialTheme.typography.titleMedium)
                            Text(
                                "Доступна ${state.update.latestTag} (сейчас ${state.update.currentVersion})",
                                style = MaterialTheme.typography.bodyMedium,
                            )
                            if (state.update.downloading) {
                                Spacer(Modifier.height(8.dp))
                                val p = state.update.downloadProgress
                                if (p != null) {
                                    LinearProgressIndicator(progress = { p }, modifier = Modifier.fillMaxWidth())
                                } else {
                                    LinearProgressIndicator(modifier = Modifier.fillMaxWidth())
                                }
                            }
                        }
                        Button(
                            enabled = !state.update.downloading && state.update.apkUrl != null,
                            onClick = { vm.downloadAndInstallUpdate(ctx) },
                        ) {
                            Text(if (state.update.downloading) "Загрузка..." else "Скачать APK")
                        }
                    }
                }
            } else if (state.update.error != null) {
                Text(
                    "Не удалось проверить обновления: ${state.update.error}",
                    style = MaterialTheme.typography.bodySmall,
                    fontFamily = FontFamily.Monospace,
                )
            }

            Box(
                modifier = Modifier
                    .weight(1f)
                    .fillMaxWidth(),
            ) {
                when (tab) {
                    0 -> SshScreen(
                        state = state,
                        onDownload = { vm.downloadViaSsh(ctx) },
                        onUpdateField = { k, v -> vm.updateSshField(k, v) },
                        onDismissError = { vm.clearError() },
                    )
                    1 -> MeshScreen(state = state, onCopy = { vm.copyMeshToClipboard(ctx) })
                    2 -> ConfigScreen(
                        modifier = Modifier.fillMaxWidth(),
                        state = state,
                        onUpdateField = { sec, key, v -> vm.updateConfigField(sec, key, v) },
                        onSave = { vm.saveConfigToPrinter(ctx) },
                        onRefreshBackups = { vm.refreshBackups() },
                        onCreateBackup = { vm.createBackup() },
                        onRestoreBackup = { p -> vm.restoreBackup(p) },
                        onDeleteBackup = { p -> vm.deleteBackup(p) },
                        onAceProPreset = { vm.applyAceProPreset(it) },
                    )
                    3 -> RawScreen(rawText = state.rawText)
                }
            }
        }
    }
}

