package com.rkfsociety.bedmesh.ui.widgets

import androidx.compose.foundation.Canvas
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.text.AnnotatedString
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.drawText
import androidx.compose.ui.text.rememberTextMeasurer
import androidx.compose.ui.unit.sp
import com.rkfsociety.bedmesh.model.BedMeshData
import kotlin.math.max
import kotlin.math.min

@Composable
fun Mesh2DView(mesh: BedMeshData, modifier: Modifier = Modifier) {
    val textMeasurer = rememberTextMeasurer()
    Box(modifier = modifier.background(Color(0xFF1E1E1E))) {
        Canvas(modifier = Modifier.fillMaxSize()) {
            val zMin = mesh.z.minOf { it.minOrNull() ?: 0.0 }
            val zMax = mesh.z.maxOf { it.maxOrNull() ?: 0.0 }
            val denom = (zMax - zMin).let { if (it == 0.0) 1e-9 else it }

            val cellW = size.width / mesh.xCount.toFloat()
            val cellH = size.height / mesh.yCount.toFloat()

            for (yi in 0 until mesh.yCount) {
                // invert Y like desktop (0,0 bottom-left in printer coords)
                val yDraw = (mesh.yCount - 1 - yi) * cellH
                val row = mesh.z[yi]
                for (xi in 0 until mesh.xCount) {
                    val v = row[xi]
                    val t = ((v - zMin) / denom).toFloat().coerceIn(0f, 1f)
                    val idx = (t * 255).toInt().coerceIn(0, 255)
                    val color = Palette.lut[idx]

                    drawRect(
                        color = color,
                        topLeft = Offset(xi * cellW, yDraw),
                        size = Size(cellW, cellH),
                    )
                    drawRect(
                        color = Color(0xFF505050),
                        topLeft = Offset(xi * cellW, yDraw),
                        size = Size(cellW, cellH),
                        style = Stroke(width = 1f),
                    )

                    val txt = String.format("%+.3f", v)
                    val ratio = (v - zMin) / denom
                    val txtColor = if (ratio in 0.25..0.75) Color.Black else Color.White

                    val layout = textMeasurer.measure(
                        text = AnnotatedString(txt),
                        style = TextStyle(fontSize = 11.sp, color = txtColor),
                    )
                    val tx = xi * cellW + (cellW - layout.size.width) / 2f
                    val ty = yDraw + (cellH - layout.size.height) / 2f
                    drawText(layout, topLeft = Offset(tx, ty))
                }
            }
        }
    }
}

