package com.rkfsociety.bedmesh.model

data class BedMeshData(
    val x: DoubleArray,
    val y: DoubleArray,
    val z: Array<DoubleArray>, // [y][x]
    val xCount: Int,
    val yCount: Int,
    val minX: Double,
    val maxX: Double,
    val minY: Double,
    val maxY: Double,
)

