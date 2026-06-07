package com.rkfsociety.bedmesh.core

/**
 * Данные input_shaper из printer_mutable.cfg / printer.cfg.
 */
data class InputShaperData(
    val typeX: String,
    val typeY: String,
    val freqX: Double,
    val freqY: Double,
)

/**
 * Рекомендованное максимальное ускорение:
 *   max_accel = K * f²
 * K-коэффициенты из shaper_calibrate.py Klipper (threshold=0.12, damping=0.1).
 */
object ShaperAccelCalc {

    private val K = mapOf(
        "zv"        to 2.60,
        "mzv"       to 2.15,
        "zvd"       to 2.00,
        "ei"        to 1.60,
        "2hump_ei"  to 1.11,
        "3hump_ei"  to 0.85,
    )

    data class Result(
        val maxAccel: Int,        // рекомендованное ускорение, мм/с²
        val limitAxis: String,    // "X" или "Y" — ограничивающая ось
        val accelX: Double,
        val accelY: Double,
    )

    fun compute(data: InputShaperData): Result? {
        val kx = K[data.typeX] ?: return null
        val ky = K[data.typeY] ?: return null
        val ax = kx * data.freqX * data.freqX
        val ay = ky * data.freqY * data.freqY
        val rec = (minOf(ax, ay) / 500).toInt() * 500
        val limitAxis = if (ax < ay) "X" else "Y"
        return Result(maxAccel = rec, limitAxis = limitAxis, accelX = ax, accelY = ay)
    }
}
