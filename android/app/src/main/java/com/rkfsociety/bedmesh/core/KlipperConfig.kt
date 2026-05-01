package com.rkfsociety.bedmesh.core

/**
 * Minimal Klipper cfg parser (mirrors desktop ConfigEditor parsing):
 * - keeps raw lines
 * - builds sections map: section -> key -> (value, lineIndex)
 * - supports "key: value" (most common). We keep it conservative.
 */
data class KeyRef(val value: String, val lineIndex: Int)

class KlipperConfig(
    val rawLines: MutableList<String>,
    val sections: MutableMap<String, MutableMap<String, KeyRef>>,
) {
    companion object {
        fun parse(text: String): KlipperConfig {
            val raw = text.split("\n").map { it + "\n" }.toMutableList()
            val sections = mutableMapOf<String, MutableMap<String, KeyRef>>()

            var current: String? = null
            for ((idx, line0) in raw.withIndex()) {
                val stripped = line0.trim()
                if (stripped.isEmpty() || stripped.startsWith("#")) continue

                val sec = Regex("^\\[(.+)]$").matchEntire(stripped)
                if (sec != null) {
                    current = sec.groupValues[1]
                    sections.getOrPut(current) { mutableMapOf() }
                    continue
                }

                if (current != null && stripped.contains(":")) {
                    // ignore commented out keys (#key: ...)
                    if (stripped.startsWith("#")) continue
                    val parts = stripped.split(":", limit = 2)
                    if (parts.size == 2) {
                        val key = parts[0].trim()
                        val valPart = parts[1].split("#", limit = 2)[0].trim()
                        sections.getOrPut(current) { mutableMapOf() }[key] = KeyRef(valPart, idx)
                    }
                }
            }

            return KlipperConfig(rawLines = raw, sections = sections)
        }
    }

    fun setValue(section: String, key: String, newValue: String): Boolean {
        val sec = sections[section] ?: return false
        val ref = sec[key] ?: return false
        if (ref.value == newValue) return false
        val original = rawLines[ref.lineIndex]
        val indent = original.takeWhile { it == ' ' || it == '\t' }
        rawLines[ref.lineIndex] = "$indent$key: $newValue\n"
        sec[key] = ref.copy(value = newValue)
        return true
    }

    fun toText(): String = rawLines.joinToString(separator = "")
}

