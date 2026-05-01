package com.rkfsociety.bedmesh.ui

import android.content.Intent
import android.net.Uri
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
    val tabs = listOf("Карта", "Config", "RAW", "SSH")

    Scaffold(
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
                    } else {
                        TextButton(onClick = { vm.checkUpdates() }) {
                            Text("Обновления")
                        }
                    }
                },
            )
        },
        bottomBar = {
            NavigationBar {
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
                        }
                        Button(onClick = {
                            val url = "https://github.com/rkfsociety/bedmesh/releases/latest"
                            ctx.startActivity(Intent(Intent.ACTION_VIEW, Uri.parse(url)))
                        }) {
                            Text("Открыть релиз")
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

            when (tab) {
                0 -> MeshScreen(state = state, onCopy = { vm.copyMeshToClipboard(ctx) })
                1 -> ConfigScreen(
                    state = state,
                    onUpdateField = { sec, key, v -> vm.updateConfigField(sec, key, v) },
                    onSave = { vm.saveConfigToPrinter(ctx) },
                    onRefreshBackups = { vm.refreshBackups() },
                    onCreateBackup = { vm.createBackup() },
                    onRestoreBackup = { p -> vm.restoreBackup(p) },
                    onDeleteBackup = { p -> vm.deleteBackup(p) },
                )
                2 -> RawScreen(rawText = state.rawText)
                else -> SshScreen(
                    state = state,
                    onDownload = { vm.downloadViaSsh(ctx) },
                    onUpdateField = { k, v -> vm.updateSshField(k, v) },
                    onDismissError = { vm.clearError() },
                )
            }
        }
    }
}

