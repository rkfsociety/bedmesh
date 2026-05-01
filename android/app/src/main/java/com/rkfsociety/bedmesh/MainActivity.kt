package com.rkfsociety.bedmesh

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import com.rkfsociety.bedmesh.ui.AppRoot
import com.rkfsociety.bedmesh.ui.theme.BedMeshTheme

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()
        setContent {
            BedMeshTheme {
                Surface(color = MaterialTheme.colorScheme.background) {
                    AppRoot()
                }
            }
        }
    }
}

