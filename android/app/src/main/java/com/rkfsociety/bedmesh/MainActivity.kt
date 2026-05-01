package com.rkfsociety.bedmesh

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.runtime.SideEffect
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.toArgb
import androidx.compose.ui.platform.LocalView
import androidx.core.view.WindowCompat
import com.rkfsociety.bedmesh.ui.AppRoot
import com.rkfsociety.bedmesh.ui.theme.BedMeshTheme

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()
        setContent {
            BedMeshTheme {
                val view = LocalView.current
                val bg = MaterialTheme.colorScheme.background
                SideEffect {
                    val w = this@MainActivity.window
                    w.navigationBarColor = bg.toArgb()
                    WindowCompat.getInsetsController(w, view).apply {
                        isAppearanceLightNavigationBars = false
                        isAppearanceLightStatusBars = false
                    }
                }
                Surface(modifier = Modifier.fillMaxSize(), color = bg) {
                    AppRoot()
                }
            }
        }
    }
}

