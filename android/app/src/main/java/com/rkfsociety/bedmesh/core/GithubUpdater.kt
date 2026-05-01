package com.rkfsociety.bedmesh.core

import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import okhttp3.OkHttpClient
import okhttp3.Request
import kotlinx.serialization.json.Json
import kotlinx.serialization.json.jsonObject
import kotlinx.serialization.json.jsonPrimitive

data class UpdateState(
    val checking: Boolean = false,
    val currentVersion: String,
    val latestTag: String? = null,
    val updateAvailable: Boolean = false,
    val error: String? = null,
)

object GithubUpdater {
    private const val REPO = "rkfsociety/bedmesh"
    private val http = OkHttpClient()
    private val json = Json { ignoreUnknownKeys = true; isLenient = true }

    suspend fun checkLatestReleaseTag(currentVersion: String): Pair<String?, String?> {
        return withContext(Dispatchers.IO) {
            try {
                val req = Request.Builder()
                    .url("https://api.github.com/repos/$REPO/releases/latest")
                    .header("Accept", "application/vnd.github+json")
                    .header("User-Agent", "rkfsociety-bedmesh-android")
                    .build()
                http.newCall(req).execute().use { resp ->
                    if (!resp.isSuccessful) return@withContext null to "http_${resp.code}"
                    val body = resp.body?.string().orEmpty()
                    val root = json.parseToJsonElement(body).jsonObject
                    val tag = root["tag_name"]?.jsonPrimitive?.content?.trim()
                    return@withContext tag to null
                }
            } catch (e: Exception) {
                null to (e.message ?: "error")
            }
        }
    }

    fun isNewVersion(current: String, remoteTag: String): Boolean {
        val a = parseVersionNumbers(current)
        val b = parseVersionNumbers(remoteTag)
        return compareVersions(b, a) > 0
    }

    private fun parseVersionNumbers(v: String): List<Int> {
        val s = v.trim().lowercase()
            .removePrefix("v")
            .split("-", limit = 2)[0]
        val parts = s.split(Regex("[^0-9]+")).filter { it.isNotBlank() }
        if (parts.isEmpty()) return listOf(0)
        return parts.map { it.toIntOrNull() ?: 0 }
    }

    private fun compareVersions(a: List<Int>, b: List<Int>): Int {
        val n = maxOf(a.size, b.size)
        for (i in 0 until n) {
            val ai = a.getOrNull(i) ?: 0
            val bi = b.getOrNull(i) ?: 0
            if (ai != bi) return ai.compareTo(bi)
        }
        return 0
    }
}

