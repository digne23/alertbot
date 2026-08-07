package com.alertbot.mobile.data

import org.json.JSONObject
import java.text.SimpleDateFormat
import java.util.Locale
import java.util.TimeZone

/**
 * One incident, as the dashboard sees it. Mirrors `serialize()` in
 * `app/api/incidents.py` — only the fields this app actually shows.
 */
data class Incident(
    val id: Int,
    val service: String,
    val provider: String,
    val reason: String,
    val severity: String,
    val state: String,
    val source: String,
    val acknowledged: Boolean,
    val acknowledgedAt: Long,
    val eventCount: Int,
    val createdAt: Long,
) {
    val isOpen: Boolean get() = state.equals("OPEN", ignoreCase = true)

    /** What raised this, in words a non-engineer recognises. */
    val sourceKind: SourceKind
        get() = when (source.lowercase(Locale.ROOT)) {
            "email" -> SourceKind.EMAIL
            "whatsapp" -> SourceKind.WHATSAPP
            "test" -> SourceKind.TEST
            "manual" -> SourceKind.MANUAL
            else -> SourceKind.OTHER
        }

    companion object {
        fun from(json: JSONObject) = Incident(
            id = json.optInt("id", 0),
            service = json.optString("service", "").ifBlank { "Unknown service" },
            provider = json.optString("provider", ""),
            reason = json.optString("reason", ""),
            severity = json.optString("severity", ""),
            state = json.optString("state", "OPEN"),
            source = json.optString("source", ""),
            acknowledged = json.optBoolean("acknowledged", false),
            acknowledgedAt = parseUtc(json.optString("acknowledged_at")),
            eventCount = json.optInt("event_count", 1),
            createdAt = parseUtc(json.optString("created_at")),
        )
    }
}

enum class SourceKind { EMAIL, WHATSAPP, TEST, MANUAL, OTHER }

/**
 * Parses the backend's timestamps to epoch millis, or 0 when absent.
 *
 * `_iso()` in `app/api/incidents.py` emits `datetime.isoformat() + "Z"`, which
 * carries *microseconds* — six fractional digits that `SimpleDateFormat`'s
 * `SSS` would read as milliseconds and throw the time out by minutes. The
 * fraction is worthless for "4 minutes ago", so it is dropped before parsing.
 *
 * `java.time` would be tidier but needs API 26, and this app ships to
 * minSdk 24.
 */
fun parseUtc(value: String?): Long {
    if (value.isNullOrBlank() || value == "null") return 0L
    val trimmed = value.removeSuffix("Z").substringBefore('.').substringBefore('+')
    return try {
        val format = SimpleDateFormat("yyyy-MM-dd'T'HH:mm:ss", Locale.US)
        format.timeZone = TimeZone.getTimeZone("UTC")
        format.parse(trimmed)?.time ?: 0L
    } catch (error: Exception) {
        0L
    }
}
