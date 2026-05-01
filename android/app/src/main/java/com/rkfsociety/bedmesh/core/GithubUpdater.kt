package com.rkfsociety.bedmesh.core

import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import okhttp3.OkHttpClient
import okhttp3.Request
import kotlinx.serialization.json.Json
import kotlinx.serialization.json.jsonArray
import kotlinx.serialization.json.jsonObject
import kotlinx.serialization.json.jsonPrimitive

data class UpdateState(
    val checking: Boolean = false,
    val currentVersion: String,
    val latestTag: String? = null,
    val apkUrl: String? = null,
    val updateAvailable: Boolean = false,
    val downloading: Boolean = false,
    val downloadProgress: Float? = null, // 0..1, null если неизвестно
    val downloadedApkPath: String? = null,
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
                    // We need the latest *android* tag, not the global "latest" (which can be mac/win).
                    .url("https://api.github.com/repos/$REPO/releases?per_page=30")
                    .header("Accept", "application/vnd.github+json")
                    .header("User-Agent", "rkfsociety-bedmesh-android")
                    .build()
                http.newCall(req).execute().use { resp ->
                    if (!resp.isSuccessful) return@withContext null to "http_${resp.code}"
                    val body = resp.body?.string().orEmpty()
                    val arr = json.parseToJsonElement(body).jsonArray
                    val tags = arr.mapNotNull { el ->
                        el.jsonObject["tag_name"]?.jsonPrimitive?.content?.trim()
                    }

                    val androidTags = tags
                        .map { it.trim() }
                        .filter { it.lowercase().contains("-android") }

                    if (androidTags.isEmpty()) {
                        return@withContext null to "no_android_releases"
                    }

                    // Pick the highest version among android tags.
                    val latest = androidTags.maxWithOrNull { a, b ->
                        compareVersions(parseVersionNumbers(a), parseVersionNumbers(b))
                    }

                    return@withContext latest to null
                }
            } catch (e: Exception) {
                null to e.formatDiagnostic()
            }
        }
    }

    suspend fun findApkDownloadUrlForTag(tag: String): Pair<String?, String?> {
        return withContext(Dispatchers.IO) {
            try {
                val req = Request.Builder()
                    .url("https://api.github.com/repos/$REPO/releases/tags/$tag")
                    .header("Accept", "application/vnd.github+json")
                    .header("User-Agent", "rkfsociety-bedmesh-android")
                    .build()
                http.newCall(req).execute().use { resp ->
                    if (!resp.isSuccessful) return@withContext null to "http_${resp.code}"
                    val body = resp.body?.string().orEmpty()
                    val obj = json.parseToJsonElement(body).jsonObject
                    val assets = obj["assets"]?.jsonArray ?: return@withContext null to "no_assets"
                    val apkAsset = assets.firstOrNull { el ->
                        val name = el.jsonObject["name"]?.jsonPrimitive?.content?.trim().orEmpty().lowercase()
                        name.endsWith(".apk")
                    } ?: return@withContext null to "no_apk_asset"

                    val url = apkAsset.jsonObject["browser_download_url"]
                        ?.jsonPrimitive
                        ?.content
                        ?.trim()
                    return@withContext url to null
                }
            } catch (e: Exception) {
                null to e.formatDiagnostic()
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

