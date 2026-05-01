package com.rkfsociety.bedmesh.core

/**
 * Текст для показа пользователю: у многих сетевых/SSH исключений [Throwable.message] бывает null,
 * тогда в UI оказывалось слово «ошибка» без смысла.
 */
fun Throwable.formatDiagnostic(maxCauses: Int = 6): String {
    val lines = mutableListOf<String>()
    var current: Throwable? = this
    var depth = 0
    while (current != null && depth < maxCauses) {
        val ex = current
        val typeName = ex.javaClass.simpleName.ifBlank { ex.javaClass.name }
        val msg = ex.message?.trim()?.takeIf { it.isNotEmpty() }
        val loc = ex.localizedMessage?.trim()?.takeIf { it.isNotEmpty() && it != msg }
        val line = buildString {
            append(typeName)
            when {
                msg != null -> append(": ").append(msg)
                loc != null -> append(": ").append(loc)
            }
        }
        lines += if (depth == 0) line else "→ $line"
        current = ex.cause
        depth++
    }
    val joined = lines.joinToString("\n").trim()
    if (joined.isNotEmpty()) return joined
    return toString().trim().ifEmpty { "Неизвестная ошибка (${javaClass.name})" }
}
