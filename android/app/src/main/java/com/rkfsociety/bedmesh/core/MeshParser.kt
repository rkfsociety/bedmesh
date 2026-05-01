package com.rkfsociety.bedmesh.core

import com.rkfsociety.bedmesh.model.BedMeshData
import kotlinx.serialization.json.Json
import kotlinx.serialization.json.JsonElement
import kotlinx.serialization.json.JsonObject
import kotlinx.serialization.json.jsonObject
import kotlinx.serialization.json.jsonPrimitive

object MeshParser {
    private val json = Json {
        ignoreUnknownKeys = true
        isLenient = true
    }

    fun parseText(text: String): BedMeshData? {
        val trimmed = text.trim()
        if (trimmed.startsWith("{") && trimmed.endsWith("}")) {
            try {
                val root = json.parseToJsonElement(trimmed)
                return parseJsonRoot(root)
            } catch (_: Exception) {
                // fall through to cfg parser
            }
        }
        return parseConfig(trimmed)
    }

    private fun parseJsonRoot(root: JsonElement): BedMeshData? {
        val obj = root.jsonObject
        val mesh = obj["bed_mesh default"]?.jsonObject ?: return null

        val xCount = mesh["x_count"]?.jsonPrimitive?.content?.toIntOrNull() ?: return null
        val yCount = mesh["y_count"]?.jsonPrimitive?.content?.toIntOrNull() ?: return null
        if (xCount <= 0 || yCount <= 0) return null

        val minX = mesh["min_x"]?.jsonPrimitive?.content?.toDoubleOrNull() ?: 0.0
        val maxX = mesh["max_x"]?.jsonPrimitive?.content?.toDoubleOrNull() ?: 0.0
        val minY = mesh["min_y"]?.jsonPrimitive?.content?.toDoubleOrNull() ?: 0.0
        val maxY = mesh["max_y"]?.jsonPrimitive?.content?.toDoubleOrNull() ?: 0.0

        val pointsStr = mesh["points"]?.jsonPrimitive?.content ?: return null
        val flat = pointsStr
            .replace(",", " ")
            .split(Regex("\\s+"))
            .filter { it.isNotBlank() }
            .mapNotNull { it.toDoubleOrNull() }
        if (flat.size != xCount * yCount) return null

        val z = Array(yCount) { yi ->
            DoubleArray(xCount) { xi ->
                flat[yi * xCount + xi]
            }
        }

        return BedMeshData(
            x = linspace(minX, maxX, xCount),
            y = linspace(minY, maxY, yCount),
            z = z,
            xCount = xCount,
            yCount = yCount,
            minX = minX,
            maxX = maxX,
            minY = minY,
            maxY = maxY,
        )
    }

    /**
     * Cfg parser mirrors the Python logic:
     * - find section [bed_mesh ...]
     * - support probe_count + mesh_min/mesh_max
     * - capture multiline points: stop when next key starts or next section begins
     */
    fun parseConfig(configText: String): BedMeshData? {
        val lines = configText.split("\n")
        val sectionLines = mutableListOf<String>()
        var inSection = false

        for (raw in lines) {
            val stripped = raw.trim()
            if (stripped.startsWith("[") && stripped.contains("bed_mesh")) {
                inSection = true
                sectionLines.clear()
                continue
            }
            if (inSection) {
                if (stripped.startsWith("[")) break
                sectionLines.add(raw)
            }
        }
        if (sectionLines.isEmpty()) return null

        fun get(key: String): String? {
            for (l0 in sectionLines) {
                val l = l0.split("#", limit = 2)[0].trim()
                if (l.startsWith("$key:") || l.startsWith("$key :")) return l.split(":", limit = 2).getOrNull(1)?.trim()
                if (l.startsWith("$key=") || l.startsWith("$key =")) return l.split("=", limit = 2).getOrNull(1)?.trim()
            }
            return null
        }

        fun parsePair(raw: String?): Pair<Double, Double>? {
            if (raw == null) return null
            val parts = raw.replace(" ", "")
                .split(",")
                .filter { it.isNotBlank() }
            if (parts.size != 2) return null
            val a = parts[0].toDoubleOrNull() ?: return null
            val b = parts[1].toDoubleOrNull() ?: return null
            return a to b
        }

        fun parseIntPair(raw: String?): Pair<Int, Int>? {
            val p = parsePair(raw) ?: return null
            return p.first.toInt() to p.second.toInt()
        }

        var xCount = get("x_count")?.toIntOrNull() ?: 0
        var yCount = get("y_count")?.toIntOrNull() ?: 0

        val probeCount = parseIntPair(get("probe_count"))
        if ((xCount <= 0 || yCount <= 0) && probeCount != null) {
            xCount = probeCount.first
            yCount = probeCount.second
        }
        if (xCount <= 0 || yCount <= 0) return null

        val meshMin = parsePair(get("mesh_min"))
        val meshMax = parsePair(get("mesh_max"))

        val (minX, minY, maxX, maxY) = if (meshMin != null && meshMax != null) {
            listOf(meshMin.first, meshMin.second, meshMax.first, meshMax.second)
        } else {
            val minX0 = get("min_x")?.toDoubleOrNull() ?: 0.0
            val maxX0 = get("max_x")?.toDoubleOrNull() ?: 0.0
            val minY0 = get("min_y")?.toDoubleOrNull() ?: 0.0
            val maxY0 = get("max_y")?.toDoubleOrNull() ?: 0.0
            listOf(minX0, minY0, maxX0, maxY0)
        }

        val pts = mutableListOf<String>()
        var capture = false
        val keyStart = Regex("^[A-Za-z_][A-Za-z0-9_]*\\s*[:=].*")

        for (rawLine0 in sectionLines) {
            val noComment = rawLine0.split("#", limit = 2)[0].trimEnd('\r', '\n')
            val stripped = noComment.trim()
            if (stripped.startsWith("points") && (stripped.contains(":") || stripped.contains("="))) {
                capture = true
                val after = if (stripped.contains(":")) stripped.substringAfter(":", "").trim() else stripped.substringAfter("=", "").trim()
                if (after.isNotBlank()) pts.add(after)
                continue
            }
            if (capture) {
                if (stripped.startsWith("[")) break
                if (keyStart.matches(stripped)) break
                if (stripped.isNotBlank()) pts.add(stripped)
            }
        }
        if (pts.isEmpty()) return null

        val rows = mutableListOf<DoubleArray>()
        for (line in pts) {
            val cleaned = line.trim().trim('[', ']', '(', ')')
            val parts = cleaned.split(Regex("[,\\s]+")).filter { it.isNotBlank() }
            val nums = parts.mapNotNull { it.toDoubleOrNull() }
            if (nums.isNotEmpty()) rows.add(nums.toDoubleArray())
        }
        if (rows.isEmpty()) return null

        val z = if (rows.size == yCount && rows.all { it.size == xCount }) {
            Array(yCount) { i -> rows[i] }
        } else {
            val flat = rows.flatMap { it.asList() }
            if (flat.size != xCount * yCount) return null
            Array(yCount) { yi ->
                DoubleArray(xCount) { xi ->
                    flat[yi * xCount + xi]
                }
            }
        }

        return BedMeshData(
            x = linspace(minX, maxX, xCount),
            y = linspace(minY, maxY, yCount),
            z = z,
            xCount = xCount,
            yCount = yCount,
            minX = minX,
            maxX = maxX,
            minY = minY,
            maxY = maxY,
        )
    }

    private fun linspace(a: Double, b: Double, n: Int): DoubleArray {
        if (n <= 1) return doubleArrayOf(a)
        val step = (b - a) / (n - 1)
        return DoubleArray(n) { i -> a + i * step }
    }
}

