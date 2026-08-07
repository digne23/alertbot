package com.alertbot.mobile.data

import android.content.Context
import android.util.Base64
import android.util.Log
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody
import okhttp3.Response
import org.json.JSONArray
import org.json.JSONObject
import java.util.concurrent.TimeUnit

/**
 * Thin wrapper over the AlertBot REST API. No business logic lives here — the
 * server owns all of that. Every call blocks, so callers hop to
 * `Dispatchers.IO` (or a receiver's own thread) first.
 */
object ApiClient {

    private const val TAG = "AlertBotApi"
    private val JSON = "application/json; charset=utf-8".toMediaType()
    private val EMPTY_BODY = "".toRequestBody(JSON)

    private val client = OkHttpClient.Builder()
        .connectTimeout(15, TimeUnit.SECONDS)
        .readTimeout(20, TimeUnit.SECONDS)
        .build()

    /** Credentials for one call. Sign-in uses values not yet saved to [Prefs]. */
    data class Creds(
        val baseUrl: String,
        val username: String,
        val password: String,
        val registrationKey: String = "",
    )

    private fun Context.creds() = Creds(baseUrl, username, password, registrationKey)

    /**
     * Accepts what people actually type. "alerts.esicia.rw" and
     * "alerts.esicia.rw/" both become a URL that works.
     */
    fun normaliseUrl(raw: String): String {
        val trimmed = raw.trim().trimEnd('/')
        if (trimmed.isEmpty()) return ""
        return if (trimmed.contains("://")) trimmed else "https://$trimmed"
    }

    private fun request(creds: Creds, path: String): Request.Builder {
        val builder = Request.Builder().url("${creds.baseUrl}$path")
        if (creds.username.isNotBlank() || creds.password.isNotBlank()) {
            val raw = "${creds.username}:${creds.password}"
            builder.header(
                "Authorization",
                "Basic " + Base64.encodeToString(raw.toByteArray(), Base64.NO_WRAP),
            )
        }
        if (creds.registrationKey.isNotBlank()) {
            builder.header("X-Registration-Key", creds.registrationKey)
        }
        return builder
    }

    private fun <T> call(builder: Request.Builder, block: (Response) -> T): T? = try {
        client.newCall(builder.build()).execute().use(block)
    } catch (error: Exception) {
        Log.w(TAG, "Request failed: ${error.message}")
        null
    }

    // --- Sign in ---------------------------------------------------------

    sealed interface SignInResult {
        /** [pushEnabled] is false when the server's Firebase channel is off —
         *  the app is usable but will never ring. Worth saying out loud. */
        data class Success(val pushEnabled: Boolean) : SignInResult
        data object BadCredentials : SignInResult
        data object Unreachable : SignInResult
    }

    /**
     * One call proves the address *and* the credentials: `/api/stats` sits
     * behind the same Basic auth as the dashboard, so 200 means both are good
     * and 401 means the password is wrong.
     */
    fun signIn(creds: Creds): SignInResult {
        val response = call(request(creds, "/api/stats").get()) { response ->
            response.code to (response.body?.string() ?: "")
        } ?: return SignInResult.Unreachable

        val (code, body) = response
        if (code == 401 || code == 403) return SignInResult.BadCredentials
        if (code !in 200..299) return SignInResult.Unreachable

        return SignInResult.Success(pushEnabled = firebaseEnabled(body))
    }

    /** Reads `channels[]` out of a `/api/stats` body. */
    private fun firebaseEnabled(body: String): Boolean = try {
        val channels = JSONObject(body).optJSONArray("channels") ?: JSONArray()
        (0 until channels.length()).any { index ->
            val channel = channels.optJSONObject(index)
            channel?.optString("name") == "firebase" && channel.optBoolean("enabled", false)
        }
    } catch (error: Exception) {
        false
    }

    /**
     * Fetches the device registration key so the user never has to see it.
     * `/api/health` returns it behind the dashboard login (see
     * `app/main.py`), which is exactly the login we just completed.
     */
    fun fetchRegistrationKey(creds: Creds): String {
        val body = call(request(creds, "/api/health").get()) { response ->
            if (response.isSuccessful) response.body?.string() else null
        } ?: return ""

        return try {
            JSONObject(body).optString("ingest_key", "")
        } catch (error: Exception) {
            ""
        }
    }

    // --- Device registration ---------------------------------------------

    /** Tell the backend about this device's FCM token. Safe to call repeatedly. */
    fun registerDevice(context: Context, token: String, label: String): Boolean {
        val creds = context.creds()
        if (creds.baseUrl.isBlank() || token.isBlank()) return false

        val payload = JSONObject()
            .put("token", token)
            .put("label", label)
            .put("platform", "android")
            .toString()

        return call(request(creds, "/api/devices").post(payload.toRequestBody(JSON))) { response ->
            Log.i(TAG, "registerDevice -> HTTP ${response.code}")
            response.isSuccessful
        } ?: false
    }

    // --- Incidents --------------------------------------------------------

    /** Open incidents, newest first. Null means the server could not be reached. */
    fun openIncidents(context: Context): List<Incident>? {
        val creds = context.creds()
        if (creds.baseUrl.isBlank()) return null

        val body = call(
            request(creds, "/api/incidents?state=OPEN&limit=100").get()
        ) { response ->
            if (response.isSuccessful) response.body?.string() else null
        } ?: return null

        return try {
            val items = JSONObject(body).optJSONArray("items") ?: JSONArray()
            (0 until items.length()).mapNotNull { index ->
                items.optJSONObject(index)?.let { Incident.from(it) }
            }
        } catch (error: Exception) {
            Log.w(TAG, "Could not read incident list: ${error.message}")
            null
        }
    }

    fun incident(context: Context, incidentId: Int): Incident? {
        val creds = context.creds()
        if (incidentId <= 0 || creds.baseUrl.isBlank()) return null

        val body = call(request(creds, "/api/incidents/$incidentId").get()) { response ->
            if (response.isSuccessful) response.body?.string() else null
        } ?: return null

        return try {
            Incident.from(JSONObject(body))
        } catch (error: Exception) {
            null
        }
    }

    fun acknowledge(context: Context, incidentId: Int): Boolean {
        val creds = context.creds()
        if (incidentId <= 0 || creds.baseUrl.isBlank()) return false

        return call(
            request(creds, "/api/incidents/$incidentId/ack").post(EMPTY_BODY)
        ) { response -> response.isSuccessful } ?: false
    }

    /**
     * Raises a real incident through `IncidentService.create_incident()`, so
     * the whole notification path fires and the phone genuinely rings. This is
     * the only way to prove push delivery actually works.
     */
    fun sendTestAlert(context: Context): Boolean {
        val creds = context.creds()
        if (creds.baseUrl.isBlank()) return false

        return call(
            request(creds, "/api/test-alert").post(EMPTY_BODY)
        ) { response -> response.isSuccessful } ?: false
    }
}
