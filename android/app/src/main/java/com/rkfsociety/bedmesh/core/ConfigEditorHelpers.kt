package com.rkfsociety.bedmesh.core

import kotlin.math.roundToInt

/** Как в win/pyqt6 `config_editor.py`: только пересечение ключей из файла и whitelist метаданных. */

fun KlipperConfig.resolveSection(baseName: String): String? =
    sections.keys.firstOrNull { it == baseName || it.startsWith("$baseName ") }

/** Показ одного числа, если оба совпадают: "5,5" → "5" */
fun displayBedMeshPairValue(key: String, raw: String): String {
    if (key !in setOf("mesh_min", "mesh_max", "probe_count")) return raw
    val parts = raw.split(",").map { it.trim() }
    if (parts.size != 2) return raw
    val a = parts[0]
    val b = parts[1]
    if (a.isEmpty() || b.isEmpty()) return raw
    return if (a == b) a else raw
}

/**
 * Одно число без запятой дублируется: "5" → "5,5" (как в Windows).
 * probe_count — целые.
 */
fun normalizeBedMeshPairValue(key: String, value: String): String {
    if (key !in setOf("mesh_min", "mesh_max", "probe_count")) return value
    val v = value.trim()
    if (v.isEmpty() || "," in v) return v
    val numRe = if (key == "probe_count") Regex("^\\d+$") else Regex("^[+-]?(?:\\d+(?:\\.\\d*)?|\\.\\d+)$")
    return if (numRe.matches(v)) "$v,$v" else v
}

/** Lagrange в Klipper допустим только для сеток не больше 5x5. */
fun probeCountAllowsLagrange(value: String): Boolean {
    val parts = value.trim().split(Regex("[,\\s]+" )).filter { it.isNotEmpty() }
    if (parts.isEmpty() || parts.size > 2 || parts.any { it.toIntOrNull() == null }) return true
    val counts = if (parts.size == 1) listOf(parts[0].toInt()) else parts.take(2).map { it.toInt() }
    return counts.all { it > 0 } && counts.maxOrNull()!! <= 5
}

/**
 * Те же коэффициенты и ключи, что `_apply_preset` в `config_editor.py`.
 */
fun aceProValuesForPercent(percent: Int): Map<String, String> {
    val pct = percent.coerceIn(100, 300)
    val factor = pct / 100.0
    val useOptimized = pct != 100

    val standard = mapOf(
        "v2_unwind_speed" to "20",
        "v1_unwind_speed" to "20",
        "v2_feed_speed" to "30",
        "v1_feed_speed" to "30",
        "unwind_speed_old_ace" to "15",
        "unwind_length_after_triggered" to "1300",
    )
    val optimized = mapOf("unwind_length_after_triggered" to "1220")

    fun scaleInt(s: String): String {
        val n = s.toDoubleOrNull() ?: return s
        return n.times(factor).roundToInt().toString()
    }

    return mapOf(
        "v2_unwind_speed" to scaleInt(standard.getValue("v2_unwind_speed")),
        "v1_unwind_speed" to scaleInt(standard.getValue("v1_unwind_speed")),
        "v2_feed_speed" to scaleInt(standard.getValue("v2_feed_speed")),
        "v1_feed_speed" to scaleInt(standard.getValue("v1_feed_speed")),
        "unwind_speed_old_ace" to scaleInt(standard.getValue("unwind_speed_old_ace")),
        "unwind_length_after_triggered" to (
            if (useOptimized) optimized.getValue("unwind_length_after_triggered")
            else standard.getValue("unwind_length_after_triggered")
        ),
    )
}
