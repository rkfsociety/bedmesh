package com.rkfsociety.bedmesh.ui.widgets

/**
 * Visual Z scale for 3D mesh (same idea as desktop Z_VISUAL_SCALE).
 */
object Mesh3DMath {
    const val Z_VISUAL_SCALE = 40.0

    fun scaledZ(z: Double, scale: Double = Z_VISUAL_SCALE): Double = z * scale

    fun colorIndex(z: Double, zMin: Double, zMax: Double): Int {
        val denom = (zMax - zMin).let { if (it == 0.0) 1e-9 else it }
        val t = ((z - zMin) / denom).toFloat().coerceIn(0f, 1f)
        return (t * 255).toInt().coerceIn(0, 255)
    }
}
