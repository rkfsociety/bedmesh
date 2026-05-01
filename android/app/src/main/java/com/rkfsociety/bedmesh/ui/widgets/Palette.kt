package com.rkfsociety.bedmesh.ui.widgets

import androidx.compose.ui.graphics.Color

/**
 * Simple LUT similar to desktop palettes.
 * We keep it lightweight: 256 colors from blue->cyan->green->yellow->red.
 */
object Palette {
    val lut: List<Color> = buildList(256) {
        for (i in 0..255) {
            val t = i / 255f
            // piecewise gradient
            val c = when {
                t < 0.25f -> lerp(Color(0xFF1D4ED8), Color(0xFF06B6D4), t / 0.25f) // blue->cyan
                t < 0.50f -> lerp(Color(0xFF06B6D4), Color(0xFF22C55E), (t - 0.25f) / 0.25f) // cyan->green
                t < 0.75f -> lerp(Color(0xFF22C55E), Color(0xFFF59E0B), (t - 0.50f) / 0.25f) // green->amber
                else -> lerp(Color(0xFFF59E0B), Color(0xFFEF4444), (t - 0.75f) / 0.25f) // amber->red
            }
            add(c)
        }
    }

    private fun lerp(a: Color, b: Color, t: Float): Color {
        val clamped = t.coerceIn(0f, 1f)
        return Color(
            red = a.red + (b.red - a.red) * clamped,
            green = a.green + (b.green - a.green) * clamped,
            blue = a.blue + (b.blue - a.blue) * clamped,
            alpha = 1f,
        )
    }
}

