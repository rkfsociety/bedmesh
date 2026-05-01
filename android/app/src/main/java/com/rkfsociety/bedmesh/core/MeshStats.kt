package com.rkfsociety.bedmesh.core

import com.rkfsociety.bedmesh.model.BedMeshData
import kotlin.math.abs
import kotlin.math.sqrt

data class MeshStats(
    val min: Double,
    val max: Double,
    val range: Double,
    val mean: Double,
    val variance: Double,
    val rms: Double,
    val frontLeft: Double,
    val frontRight: Double,
    val backCenter: Double,
) {
    fun turnsFor(valMm: Double, pitchMmPerTurn: Double = 0.7): Double = abs(valMm) / pitchMmPerTurn
}

object MeshStatsCalculator {
    fun compute(data: BedMeshData): MeshStats {
        val yCount = data.yCount
        val xCount = data.xCount
        var minV = Double.POSITIVE_INFINITY
        var maxV = Double.NEGATIVE_INFINITY
        var sum = 0.0
        var sumSq = 0.0
        var n = 0

        for (y in 0 until yCount) {
            val row = data.z[y]
            for (x in 0 until xCount) {
                val v = row[x]
                if (v < minV) minV = v
                if (v > maxV) maxV = v
                sum += v
                sumSq += v * v
                n++
            }
        }
        val mean = if (n > 0) sum / n else 0.0
        val variance = if (n > 0) (sumSq / n) - (mean * mean) else 0.0
        val rms = sqrt(if (n > 0) sumSq / n else 0.0)

        val frontLeft = data.z[0][0] - mean
        val frontRight = data.z[0][xCount - 1] - mean
        val backCenter = data.z[yCount - 1][xCount / 2] - mean

        return MeshStats(
            min = minV,
            max = maxV,
            range = maxV - minV,
            mean = mean,
            variance = variance,
            rms = rms,
            frontLeft = frontLeft,
            frontRight = frontRight,
            backCenter = backCenter,
        )
    }
}

