package com.rkfsociety.bedmesh.ui.screens

import android.annotation.SuppressLint
import android.webkit.WebView
import android.webkit.WebViewClient
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.unit.dp
import androidx.compose.ui.viewinterop.AndroidView
import com.rkfsociety.bedmesh.ui.vm.InstallState
import com.rkfsociety.bedmesh.ui.vm.UiState

@SuppressLint("SetJavaScriptEnabled")
@Composable
fun PrinterScreen(
    state: UiState,
    onInstallSsh: () -> Unit,
    onInstallPanel: () -> Unit,
) {
    val panelUrl = "http://${state.ssh.ip}:8088"
    var tab by remember { mutableIntStateOf(0) }

    Column(modifier = Modifier.fillMaxSize()) {
        TabRow(selectedTabIndex = tab) {
            Tab(selected = tab == 0, onClick = { tab = 0 }, text = { Text("Установка") })
            Tab(selected = tab == 1, onClick = { tab = 1 }, text = { Text("Веб-панель") })
        }

        when (tab) {
            0 -> InstallTab(
                installSsh = state.installSsh,
                installPanel = state.installPanel,
                onInstallSsh = onInstallSsh,
                onInstallPanel = onInstallPanel,
            )
            1 -> WebPanelTab(url = panelUrl)
        }
    }
}

@Composable
private fun InstallTab(
    installSsh: InstallState,
    installPanel: InstallState,
    onInstallSsh: () -> Unit,
    onInstallPanel: () -> Unit,
) {
    Column(
        modifier = Modifier
            .fillMaxSize()
            .verticalScroll(rememberScrollState())
            .padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(16.dp),
    ) {
        // Постоянный SSH
        InstallCard(
            title = "Постоянный SSH",
            description = "Копирует dropbear с флешки в /useremain/ssh и прописывает автозапуск в run.sh. " +
                    "После установки принтер будет доступен по SSH без флешки.",
            state = installSsh,
            buttonText = "Установить SSH",
            onInstall = onInstallSsh,
        )

        // Веб-панель
        InstallCard(
            title = "Веб-панель (gkbridge)",
            description = "Скачивает gkbridge с GitHub и устанавливает на принтер. " +
                    "Доступна по http://<IP>:8088 — статус печати, температуры, управление, камера.",
            state = installPanel,
            buttonText = "Установить веб-панель",
            onInstall = onInstallPanel,
        )
    }
}

@Composable
private fun InstallCard(
    title: String,
    description: String,
    state: InstallState,
    buttonText: String,
    onInstall: () -> Unit,
) {
    Card(modifier = Modifier.fillMaxWidth()) {
        Column(
            modifier = Modifier.padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(10.dp),
        ) {
            Text(title, style = MaterialTheme.typography.titleMedium)
            Text(description, style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)

            Button(
                onClick = onInstall,
                enabled = !state.busy,
                modifier = Modifier.fillMaxWidth(),
            ) {
                if (state.busy) {
                    CircularProgressIndicator(modifier = Modifier.size(18.dp), strokeWidth = 2.dp, color = MaterialTheme.colorScheme.onPrimary)
                    Spacer(Modifier.width(8.dp))
                }
                Text(if (state.busy) "Установка…" else buttonText)
            }

            if (state.log.isNotEmpty()) {
                Surface(
                    color = MaterialTheme.colorScheme.surfaceVariant,
                    shape = MaterialTheme.shapes.small,
                ) {
                    Column(modifier = Modifier.padding(10.dp), verticalArrangement = Arrangement.spacedBy(2.dp)) {
                        state.log.forEach { line ->
                            Text(
                                line,
                                style = MaterialTheme.typography.bodySmall,
                                fontFamily = FontFamily.Monospace,
                                color = if (state.done && line == state.log.last())
                                    Color(0xFF4CAF50) else MaterialTheme.colorScheme.onSurfaceVariant,
                            )
                        }
                    }
                }
            }

            if (state.error != null) {
                Text(
                    state.error,
                    style = MaterialTheme.typography.bodySmall,
                    fontFamily = FontFamily.Monospace,
                    color = MaterialTheme.colorScheme.error,
                )
            }
        }
    }
}

@SuppressLint("SetJavaScriptEnabled")
@Composable
private fun WebPanelTab(url: String) {
    AndroidView(
        factory = { ctx ->
            WebView(ctx).apply {
                settings.javaScriptEnabled = true
                settings.domStorageEnabled = true
                webViewClient = WebViewClient()
                loadUrl(url)
            }
        },
        update = { webView ->
            if (webView.url != url) webView.loadUrl(url)
        },
        modifier = Modifier.fillMaxSize(),
    )
}
