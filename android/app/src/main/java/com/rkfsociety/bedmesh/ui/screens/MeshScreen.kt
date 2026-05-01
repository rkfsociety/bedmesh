package com.rkfsociety.bedmesh.ui.screens

import androidx.compose.foundation.layout.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import com.rkfsociety.bedmesh.ui.vm.UiState
import com.rkfsociety.bedmesh.ui.widgets.Mesh2DView
import com.rkfsociety.bedmesh.ui.widgets.Mesh3DIsometricView

@Composable
fun MeshScreen(
    state: UiState,
    onCopy: () -> Unit,
) {
    val mesh = state.mesh
    Column(verticalArrangement = Arrangement.spacedBy(10.dp)) {
        Row(horizontalArrangement = Arrangement.spacedBy(10.dp)) {
            Button(onClick = onCopy, enabled = mesh != null) {
                Text("Копировать mesh")
            }
            if (mesh == null) {
                Text("Загрузите конфиг по SSH", style = MaterialTheme.typography.bodyMedium)
            }
        }

        if (mesh != null) {
            // 2D + 3D stacked (как "side-by-side" на широких экранах будет позже)
            Mesh2DView(mesh = mesh, modifier = Modifier.fillMaxWidth().height(320.dp))
            Mesh3DIsometricView(mesh = mesh, modifier = Modifier.fillMaxWidth().height(260.dp))

            StatsPanel(state = state)
        }
    }
}

@Composable
private fun StatsPanel(state: UiState) {
    val s = state.stats
    if (s.isEmpty()) return

    Card {
        Column(modifier = Modifier.padding(12.dp), verticalArrangement = Arrangement.spacedBy(6.dp)) {
            Text("Анализ", style = MaterialTheme.typography.titleMedium)
            Text("Мин: ${s["min"]}   Макс: ${s["max"]}   Размах: ${s["range"]}")
            Text("Среднее: ${s["mean"]}   Var: ${s["var"]}   RMS: ${s["rms"]}")
            Divider()
            Text("Коррекция от среднего (мм / обороты @0.7мм)")
            Text("Передний левый: ${s["front_left_mm"]}  (${s["front_left_turns"]} об.)")
            Text("Передний правый: ${s["front_right_mm"]}  (${s["front_right_turns"]} об.)")
            Text("Задний центр: ${s["back_center_mm"]}  (${s["back_center_turns"]} об.)")
        }
    }
}

