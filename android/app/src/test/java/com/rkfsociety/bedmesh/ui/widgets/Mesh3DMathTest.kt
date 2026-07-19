package com.rkfsociety.bedmesh.ui.widgets

import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class Mesh3DMathTest {
    @Test
    fun scaledZ_multiplies() {
        assertEquals(4.0, Mesh3DMath.scaledZ(0.1, 40.0), 1e-9)
    }

    @Test
    fun colorIndex_ends() {
        assertEquals(0, Mesh3DMath.colorIndex(-0.2, -0.2, 0.3))
        assertEquals(255, Mesh3DMath.colorIndex(0.3, -0.2, 0.3))
        val mid = Mesh3DMath.colorIndex(0.05, -0.2, 0.3)
        assertTrue(mid in 1..254)
    }
}
