package com.rkfsociety.bedmesh.ui.widgets

import androidx.compose.foundation.Canvas
import androidx.compose.foundation.background
import androidx.compose.foundation.gestures.detectDragGestures
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.Path
import androidx.compose.ui.input.pointer.pointerInput
import com.rkfsociety.bedmesh.model.BedMeshData
import kotlin.math.cos
import kotlin.math.min
import kotlin.math.sin

/**
 * Lightweight "3D" view without OpenGL:
 * - isometric projection
 * - drag rotates around Z
 * - height affects Y in projection
 *
 * This keeps the project dependency-light while still giving a 3D-ish view.
 */
@Composable
fun Mesh3DIsometricView(mesh: BedMeshData, modifier: Modifier = Modifier) {
    var angle by remember { mutableFloatStateOf(0.65f) }

    Box(
        modifier = modifier
            .background(Color(0xFF121212))
            .pointerInput(Unit) {
                detectDragGestures { change, dragAmount ->
                    change.consume()
                    angle += dragAmount.x * 0.005f
                }
            },
    ) {
        Canvas(modifier = Modifier.fillMaxSize()) {
            val zMin = mesh.z.minOf { it.minOrNull() ?: 0.0 }
            val zMax = mesh.z.maxOf { it.maxOrNull() ?: 0.0 }
            val denom = (zMax - zMin).let { if (it == 0.0) 1e-9 else it }

            val pad = 20f
            val w = size.width - pad * 2
            val h = size.height - pad * 2

            val scale = min(w, h) / (maxOf(mesh.xCount, mesh.yCount).toFloat() * 1.2f)
            val heightScale = scale * 2.0f

            val cx = size.width / 2f
            val cy = size.height / 2f + scale * 2f

            fun proj(xi: Int, yi: Int, z: Double): Offset {
                val x = (xi - mesh.xCount / 2f) * scale
                val y = (yi - mesh.yCount / 2f) * scale
                val ca = cos(angle)
                val sa = sin(angle)
                val xr = x * ca - y * sa
                val yr = x * sa + y * ca
                // isometric-ish: x contributes to x, y contributes to x and y; z lifts up
                val px = cx + (xr - yr) * 0.9f
                val py = cy + (xr + yr) * 0.45f - ((z - zMin) / denom).toFloat() * heightScale
                return Offset(px, py)
            }

            // draw quads as two triangles, painter's order: back->front by yi then xi
            for (yi in 0 until mesh.yCount - 1) {
                for (xi in 0 until mesh.xCount - 1) {
                    val z00 = mesh.z[yi][xi]
                    val z10 = mesh.z[yi][xi + 1]
                    val z01 = mesh.z[yi + 1][xi]
                    val z11 = mesh.z[yi + 1][xi + 1]
                    val zAvg = (z00 + z10 + z01 + z11) / 4.0
                    val t = ((zAvg - zMin) / denom).toFloat().coerceIn(0f, 1f)
                    val idx = (t * 255).toInt().coerceIn(0, 255)
                    val col = Palette.lut[idx].copy(alpha = 0.95f)

                    val p00 = proj(xi, yi, z00)
                    val p10 = proj(xi + 1, yi, z10)
                    val p11 = proj(xi + 1, yi + 1, z11)
                    val p01 = proj(xi, yi + 1, z01)

                    val path = Path().apply {
                        moveTo(p00.x, p00.y)
                        lineTo(p10.x, p10.y)
                        lineTo(p11.x, p11.y)
                        lineTo(p01.x, p01.y)
                        close()
                    }
                    drawPath(path, color = col)
                    drawPath(path, color = Color(0xFF2A2A2A))
                }
            }
        }
    }
}

