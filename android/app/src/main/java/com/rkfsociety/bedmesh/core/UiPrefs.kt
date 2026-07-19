package com.rkfsociety.bedmesh.core

import android.content.Context

/** UI prefs (mesh view mode, etc.). */
object UiPrefs {
    private const val NAME = "bedmesh_ui"
    private const val K_MESH_VIEW_MODE = "mesh_view_mode"

    fun loadMeshViewMode(context: Context): String {
        val p = context.applicationContext.getSharedPreferences(NAME, Context.MODE_PRIVATE)
        return p.getString(K_MESH_VIEW_MODE, "2d") ?: "2d"
    }

    fun saveMeshViewMode(context: Context, mode: String) {
        val value = if (mode == "3d") "3d" else "2d"
        context.applicationContext.getSharedPreferences(NAME, Context.MODE_PRIVATE)
            .edit()
            .putString(K_MESH_VIEW_MODE, value)
            .apply()
    }
}
