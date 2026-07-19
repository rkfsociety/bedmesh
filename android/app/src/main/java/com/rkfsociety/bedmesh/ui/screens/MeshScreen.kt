package com.rkfsociety.bedmesh.ui.screens

import androidx.compose.foundation.border
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.*
import androidx.compose.material3.HorizontalDivider
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import com.rkfsociety.bedmesh.core.InputShaperData
import com.rkfsociety.bedmesh.core.ShaperAccelCalc
import com.rkfsociety.bedmesh.core.UiPrefs
import com.rkfsociety.bedmesh.ui.vm.UiState
import com.rkfsociety.bedmesh.ui.widgets.Mesh2DView
import com.rkfsociety.bedmesh.ui.widgets.Mesh3DView

@Composable
fun MeshScreen(
    state: UiState,
    onCopy: () -> Unit,
) {
    val mesh = state.mesh
    val ctx = LocalContext.current
    var viewMode by remember { mutableStateOf(UiPrefs.loadMeshViewMode(ctx)) }
    val scroll = rememberScrollState()

    fun setMode(mode: String) {
        val m = if (mode == "3d") "3d" else "2d"
        viewMode = m
        UiPrefs.saveMeshViewMode(ctx, m)
    }

    Column(
        modifier = Modifier.fillMaxWidth(),
        verticalArrangement = Arrangement.spacedBy(10.dp),
    ) {
        Row(
            horizontalArrangement = Arrangement.spacedBy(10.dp),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            Button(onClick = onCopy, enabled = mesh != null && viewMode == "2d") {
                Text(if (viewMode == "2d") "Копировать mesh" else "Копировать (только 2D)")
            }
            FilterChip(
                selected = viewMode == "2d",
                onClick = { setMode("2d") },
                label = { Text("2D") },
            )
            FilterChip(
                selected = viewMode == "3d",
                onClick = { setMode("3d") },
                label = { Text("3D") },
            )
            if (mesh == null) {
                Text("Загрузите конфиг по SSH", style = MaterialTheme.typography.bodyMedium)
            }
        }

        if (mesh != null) {
            if (viewMode == "3d") {
                Mesh3DView(
                    mesh = mesh,
                    modifier = Modifier
                        .fillMaxWidth()
                        .aspectRatio(1f),
                )
            } else {
                Mesh2DView(
                    mesh = mesh,
                    modifier = Modifier
                        .fillMaxWidth()
                        .aspectRatio(1f),
                )
            }
            Column(
                modifier = Modifier
                    .fillMaxWidth()
                    .verticalScroll(scroll),
                verticalArrangement = Arrangement.spacedBy(10.dp),
            ) {
                ScrewRecommendationsPanel(state = state)
                ShaperPanel(shaper = state.shaper)
                StatsPanel(state = state)
            }
        }
    }
}

@Composable
private fun ScrewRecommendationsPanel(state: UiState) {
    val s = state.stats
    if (s.isEmpty()) return

    Card(
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.35f)),
    ) {
        Column(
            modifier = Modifier
                .fillMaxWidth()
                .padding(12.dp),
            verticalArrangement = Arrangement.spacedBy(10.dp),
        ) {
            Text(
                "КОРРЕКЦИЯ ОТ СРЕДНЕГО",
                style = MaterialTheme.typography.titleSmall,
                fontWeight = FontWeight.Bold,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
            Text(
                "(минимизирует кручение валов)",
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant.copy(alpha = 0.65f),
            )
            CorrectionScrewCard(
                title = "ПЕРЕДНИЙ ЛЕВЫЙ",
                mm = s["front_left_mm"].orEmpty(),
                turns = s["front_left_turns"].orEmpty(),
                direction = s["front_left_dir"].orEmpty(),
            )
            CorrectionScrewCard(
                title = "ПЕРЕДНИЙ ПРАВЫЙ",
                mm = s["front_right_mm"].orEmpty(),
                turns = s["front_right_turns"].orEmpty(),
                direction = s["front_right_dir"].orEmpty(),
            )
            CorrectionScrewCard(
                title = "ЗАДНИЙ ЦЕНТР",
                mm = s["back_center_mm"].orEmpty(),
                turns = s["back_center_turns"].orEmpty(),
                direction = s["back_center_dir"].orEmpty(),
            )
        }
    }
}

@Composable
private fun CorrectionScrewCard(
    title: String,
    mm: String,
    turns: String,
    direction: String,
) {
    val up = direction == "ВВЕРХ"
    val dirColor = if (up) Color(0xFF4ADE80) else Color(0xFFF87171)
    Surface(
        modifier = Modifier
            .fillMaxWidth()
            .border(1.dp, Color(0xFF333333), MaterialTheme.shapes.medium),
        shape = MaterialTheme.shapes.medium,
        color = MaterialTheme.colorScheme.surface,
    ) {
        Column(
            modifier = Modifier.padding(10.dp),
            verticalArrangement = Arrangement.spacedBy(6.dp),
        ) {
            Text(
                title,
                style = MaterialTheme.typography.labelLarge,
                fontWeight = FontWeight.Bold,
                color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.75f),
            )
            Row(
                modifier = Modifier.fillMaxWidth(),
                verticalAlignment = Alignment.CenterVertically,
            ) {
                Text(
                    "$mm мм",
                    style = MaterialTheme.typography.titleMedium,
                    fontWeight = FontWeight.Bold,
                )
                Spacer(modifier = Modifier.weight(1f))
                Text(
                    "($turns об. $direction)",
                    style = MaterialTheme.typography.bodyLarge,
                    fontWeight = FontWeight.Bold,
                    color = dirColor,
                )
            }
        }
    }
}

@Composable
private fun ShaperPanel(shaper: InputShaperData?) {
    if (shaper == null) return
    val result = ShaperAccelCalc.compute(shaper)

    Card(
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.35f)),
    ) {
        Column(
            modifier = Modifier
                .fillMaxWidth()
                .padding(12.dp),
            verticalArrangement = Arrangement.spacedBy(8.dp),
        ) {
            Text(
                "⚡ ШЕЙПЕР: УСКОРЕНИЯ",
                style = MaterialTheme.typography.titleSmall,
                fontWeight = FontWeight.Bold,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
            Text(
                "X: ${shaper.typeX.uppercase()}  ${shaper.freqX} Гц",
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
            Text(
                "Y: ${shaper.typeY.uppercase()}  ${shaper.freqY} Гц",
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
            if (result != null) {
                HorizontalDivider(color = MaterialTheme.colorScheme.outline.copy(alpha = 0.3f))
                Text(
                    "лимит: ось ${result.limitAxis}",
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant.copy(alpha = 0.7f),
                )
                Text(
                    "≤ ${result.maxAccel} мм/с²",
                    style = MaterialTheme.typography.titleLarge,
                    fontWeight = FontWeight.Bold,
                    color = Color(0xFF4ADE80),
                )
            } else {
                Text(
                    "Тип шейпера не распознан",
                    style = MaterialTheme.typography.bodySmall,
                    color = Color(0xFFF87171),
                )
            }
        }
    }
}

@Composable
private fun StatsPanel(state: UiState) {
    val s = state.stats
    if (s.isEmpty()) return

    Card {
        Column(modifier = Modifier.padding(12.dp), verticalArrangement = Arrangement.spacedBy(6.dp)) {
            Text("Анализ сетки", style = MaterialTheme.typography.titleMedium)
            Text("Мин: ${s["min"]}   Макс: ${s["max"]}   Размах: ${s["range"]}")
            Text("Среднее: ${s["mean"]}   Var: ${s["var"]}   RMS: ${s["rms"]}")
        }
    }
}
