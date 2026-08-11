package com.rkfsociety.bedmesh.ui.widgets

import androidx.compose.foundation.Canvas
import androidx.compose.foundation.background
import androidx.compose.foundation.gestures.detectTransformGestures
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableFloatStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.Path
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.input.pointer.pointerInput
import androidx.compose.ui.text.AnnotatedString
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.drawText
import androidx.compose.ui.text.rememberTextMeasurer
import androidx.compose.ui.unit.sp
import com.rkfsociety.bedmesh.model.BedMeshData
import kotlin.math.cos
import kotlin.math.max
import kotlin.math.min
import kotlin.math.sin

/**
 * Lightweight pseudo-3D bed mesh (Canvas, no OpenGL).
 * Drag to orbit; pinch to zoom.
 */
@Composable
fun Mesh3DView(mesh: BedMeshData, modifier: Modifier = Modifier) {
    val textMeasurer = rememberTextMeasurer()
    var azimuth by remember { mutableFloatStateOf(-60f) }
    var elevation by remember { mutableFloatStateOf(35f) }
    var distance by remember { mutableFloatStateOf(1.6f) }

    Box(
        modifier = modifier
            .background(Color(0xFF1E1E1E))
            .pointerInput(Unit) {
                detectTransformGestures { _, pan, zoom, _ ->
                    azimuth -= pan.x * 0.35f
                    elevation = (elevation + pan.y * 0.25f).coerceIn(5f, 85f)
                    distance = (distance / zoom).coerceIn(0.6f, 4.5f)
                }
            },
    ) {
        Canvas(modifier = Modifier.fillMaxSize()) {
            val nx = mesh.xCount
            val ny = mesh.yCount
            if (nx < 2 || ny < 2) return@Canvas

            var zMin = Double.POSITIVE_INFINITY
            var zMax = Double.NEGATIVE_INFINITY
            for (row in mesh.z) {
                for (v in row) {
                    zMin = min(zMin, v)
                    zMax = max(zMax, v)
                }
            }

            val xMean = mesh.x.average()
            val yMean = mesh.y.average()
            val span = max(
                (mesh.maxX - mesh.minX).takeIf { it > 0 } ?: 1.0,
                (mesh.maxY - mesh.minY).takeIf { it > 0 } ?: 1.0,
            ).toFloat()

            val az = Math.toRadians(azimuth.toDouble())
            val el = Math.toRadians(elevation.toDouble())
            val cosAz = cos(az)
            val sinAz = sin(az)
            val cosEl = cos(el)
            val sinEl = sin(el)

            fun project(xi: Int, yi: Int): Triple<Float, Float, Float> {
                val x = ((mesh.x[xi] - xMean) / span).toFloat()
                val y = ((mesh.y[yi] - yMean) / span).toFloat()
                val z = (Mesh3DMath.scaledZ(mesh.z[yi][xi]) / span).toFloat()
                val rx = x * cosAz.toFloat() - y * sinAz.toFloat()
                val ry = x * sinAz.toFloat() * sinEl.toFloat() +
                    y * cosAz.toFloat() * sinEl.toFloat() +
                    z * cosEl.toFloat()
                val depth = x * sinAz.toFloat() * cosEl.toFloat() +
                    y * cosAz.toFloat() * cosEl.toFloat() -
                    z * sinEl.toFloat()
                val scale = min(size.width, size.height) / (2.2f * distance)
                val sx = size.width / 2f + rx * scale
                val sy = size.height / 2f - ry * scale
                return Triple(sx, sy, depth)
            }

            data class Quad(
                val depth: Float,
                val p0: Offset,
                val p1: Offset,
                val p2: Offset,
                val p3: Offset,
                val color: Color,
            )

            val quads = ArrayList<Quad>((nx - 1) * (ny - 1))
            for (yi in 0 until ny - 1) {
                for (xi in 0 until nx - 1) {
                    val a = project(xi, yi)
                    val b = project(xi + 1, yi)
                    val c = project(xi + 1, yi + 1)
                    val d = project(xi, yi + 1)
                    val zAvg = (
                        mesh.z[yi][xi] + mesh.z[yi][xi + 1] +
                            mesh.z[yi + 1][xi + 1] + mesh.z[yi + 1][xi]
                        ) / 4.0
                    val color = Palette.lut[Mesh3DMath.colorIndex(zAvg, zMin, zMax)]
                    val depth = (a.third + b.third + c.third + d.third) / 4f
                    quads.add(
                        Quad(
                            depth = depth,
                            p0 = Offset(a.first, a.second),
                            p1 = Offset(b.first, b.second),
                            p2 = Offset(c.first, c.second),
                            p3 = Offset(d.first, d.second),
                            color = color,
                        ),
                    )
                }
            }
            quads.sortBy { it.depth }

            for (q in quads) {
                val path = Path().apply {
                    moveTo(q.p0.x, q.p0.y)
                    lineTo(q.p1.x, q.p1.y)
                    lineTo(q.p2.x, q.p2.y)
                    lineTo(q.p3.x, q.p3.y)
                    close()
                }
                drawPath(path, color = q.color)
                drawPath(path, color = Color(0xFF404040), style = Stroke(width = 1f))
            }

            // Координатная разметка повторяет Windows-вид: шаг 25 мм,
            // границы рабочей области всегда подписаны.
            val zFloor = zMin - span * 0.08
            val labelStyle = TextStyle(fontSize = 10.sp, color = Color(0xFFD6D6D6))
            fun projectFloor(xValue: Double, yValue: Double): Offset {
                val x = ((xValue - xMean) / span).toFloat()
                val y = ((yValue - yMean) / span).toFloat()
                val z = (Mesh3DMath.scaledZ(zFloor) / span).toFloat()
                val rx = x * cosAz.toFloat() - y * sinAz.toFloat()
                val ry = x * sinAz.toFloat() * sinEl.toFloat() +
                    y * cosAz.toFloat() * sinEl.toFloat() + z * cosEl.toFloat()
                val scale = min(size.width, size.height) / (2.2f * distance)
                return Offset(size.width / 2f + rx * scale, size.height / 2f - ry * scale)
            }
            fun drawCoordinateLabel(text: String, point: Offset) {
                val layout = textMeasurer.measure(AnnotatedString(text), labelStyle)
                drawText(layout, topLeft = Offset(point.x - layout.size.width / 2f, point.y - layout.size.height / 2f))
            }
            fun ticks(start: Double, end: Double): List<Double> {
                if (end <= start) return listOf(start)
                val result = mutableListOf(start)
                var value = kotlin.math.ceil(start / 25.0) * 25.0
                while (value < end - 1e-6) {
                    if (value > start + 1e-6) result += value
                    value += 25.0
                }
                if (result.last() < end - 1e-6) result += end
                return result
            }
            fun formatCoordinate(value: Double): String =
                if (kotlin.math.abs(value - kotlin.math.round(value)) < 1e-6) kotlin.math.round(value).toInt().toString()
                else "%.1f".format(value)

            ticks(mesh.minX, mesh.maxX).forEach { value ->
                drawCoordinateLabel(formatCoordinate(value), projectFloor(value, mesh.minY))
            }
            ticks(mesh.minY, mesh.maxY).forEach { value ->
                drawCoordinateLabel(formatCoordinate(value), projectFloor(mesh.minX, value))
            }
            drawCoordinateLabel("X (мм)", projectFloor(mesh.maxX, mesh.minY))
            drawCoordinateLabel("Y (мм)", projectFloor(mesh.minX, mesh.maxY))
        }
    }
}
