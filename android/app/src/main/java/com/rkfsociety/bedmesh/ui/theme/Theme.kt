package com.rkfsociety.bedmesh.ui.theme

import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.darkColorScheme
import androidx.compose.runtime.Composable

private val DarkScheme = darkColorScheme()

@Composable
fun BedMeshTheme(content: @Composable () -> Unit) {
    MaterialTheme(
        colorScheme = DarkScheme,
        content = content,
    )
}

