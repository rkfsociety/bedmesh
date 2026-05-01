package com.rkfsociety.bedmesh.ui.screens

import android.content.ClipData
import android.content.ClipboardManager
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.*
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.unit.dp
import com.rkfsociety.bedmesh.ui.vm.UiState

@Composable
fun SshScreen(
    state: UiState,
    onDownload: () -> Unit,
    onUpdateField: (String, String) -> Unit,
    onDismissError: () -> Unit,
) {
    Column(verticalArrangement = Arrangement.spacedBy(10.dp)) {
        Text("SSH загрузка", style = MaterialTheme.typography.titleMedium)

        OutlinedTextField(
            value = state.ssh.ip,
            onValueChange = { onUpdateField("ip", it) },
            label = { Text("IP") },
            modifier = Modifier.fillMaxWidth(),
            singleLine = true,
        )
        OutlinedTextField(
            value = state.ssh.port.toString(),
            onValueChange = { onUpdateField("port", it) },
            label = { Text("Порт") },
            modifier = Modifier.fillMaxWidth(),
            singleLine = true,
        )
        OutlinedTextField(
            value = state.ssh.user,
            onValueChange = { onUpdateField("user", it) },
            label = { Text("Логин") },
            modifier = Modifier.fillMaxWidth(),
            singleLine = true,
        )
        OutlinedTextField(
            value = state.ssh.password,
            onValueChange = { onUpdateField("password", it) },
            label = { Text("Пароль") },
            visualTransformation = PasswordVisualTransformation(),
            modifier = Modifier.fillMaxWidth(),
            singleLine = true,
        )
        OutlinedTextField(
            value = state.ssh.path,
            onValueChange = { onUpdateField("path", it) },
            label = { Text("Путь к файлу") },
            modifier = Modifier.fillMaxWidth(),
            singleLine = true,
        )

        Button(
            onClick = onDownload,
            enabled = !state.busy,
            modifier = Modifier.fillMaxWidth(),
        ) {
            Text(if (state.busy) "Загрузка..." else "Загрузить по SSH")
        }

        val errText = state.lastError
        if (errText != null) {
            val ctx = LocalContext.current
            AlertDialog(
                onDismissRequest = onDismissError,
                confirmButton = {
                    TextButton(onClick = onDismissError) { Text("OK") }
                },
                dismissButton = {
                    TextButton(
                        onClick = {
                            val cm = ctx.getSystemService(ClipboardManager::class.java)
                            cm?.setPrimaryClip(ClipData.newPlainText("BedMesh error", errText))
                        },
                    ) { Text("Копировать") }
                },
                title = { Text("Ошибка SSH") },
                text = {
                    Text(
                        errText,
                        style = MaterialTheme.typography.bodySmall,
                        fontFamily = FontFamily.Monospace,
                        modifier = Modifier
                            .verticalScroll(rememberScrollState())
                            .heightIn(max = 320.dp),
                    )
                },
            )
        }
    }
}

