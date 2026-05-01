package com.rkfsociety.bedmesh.core

import android.content.Context

/**
 * Локальное сохранение настроек SSH (SharedPreferences), чтобы не вводить их при каждом запуске.
 */
object SshPrefs {
    private const val NAME = "bedmesh_ssh"
    private const val K_IP = "ip"
    private const val K_PORT = "port"
    private const val K_USER = "user"
    private const val K_PASSWORD = "password"
    private const val K_PATH = "path"

    fun defaultConfig(): SshConfig = SshConfig(
        ip = "192.168.",
        port = 2222,
        user = "root",
        password = "rockchip",
        path = "/userdata/app/gk/printer.cfg",
    )

    fun load(context: Context): SshConfig {
        val app = context.applicationContext
        val p = app.getSharedPreferences(NAME, Context.MODE_PRIVATE)
        val d = defaultConfig()
        return SshConfig(
            ip = p.getString(K_IP, null) ?: d.ip,
            port = p.getInt(K_PORT, d.port).takeIf { it > 0 } ?: d.port,
            user = p.getString(K_USER, null) ?: d.user,
            password = p.getString(K_PASSWORD, null) ?: d.password,
            path = p.getString(K_PATH, null) ?: d.path,
        )
    }

    fun save(context: Context, cfg: SshConfig) {
        val app = context.applicationContext
        app.getSharedPreferences(NAME, Context.MODE_PRIVATE).edit().apply {
            putString(K_IP, cfg.ip)
            putInt(K_PORT, cfg.port)
            putString(K_USER, cfg.user)
            putString(K_PASSWORD, cfg.password)
            putString(K_PATH, cfg.path)
            apply()
        }
    }
}
