package com.rkfsociety.bedmesh.core

import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class ConfigEditorHelpersTest {
    @Test
    fun lagrangeAllowedForSmallProbeCount() {
        assertTrue(probeCountAllowsLagrange("5"))
        assertTrue(probeCountAllowsLagrange("5,4"))
    }

    @Test
    fun lagrangeDisabledForLargeProbeCount() {
        assertFalse(probeCountAllowsLagrange("6"))
        assertFalse(probeCountAllowsLagrange("5,6"))
    }

    @Test
    fun malformedProbeCountDoesNotBlockEditing() {
        assertTrue(probeCountAllowsLagrange(""))
        assertTrue(probeCountAllowsLagrange("5,"))
    }
}
