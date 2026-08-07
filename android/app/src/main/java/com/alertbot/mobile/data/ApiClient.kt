package com.alertbot.mobile.data

import android.content.Context
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
 *
 * Authentication is one header, `X-Registration-Key`, holding the key the
 * server returned at sign-in. There is no Basic auth and no dashboard password
 * anywhere in this app any more.
 */
object ApiClient {

    private const val TAG = "AlertBotApi"
    private val JSON = "application/json; charset=utf-8".toMediaType()
    private val EMPTY_BODY = "".toRequestBody(JSON)

    private val client = OkHttpClient.Builder()
        .connectTimeout(15, TimeUnit.SECONDS)
        .readTimeout(20, TimeUnit.SECONDS)
        .build()

    /** The server address, compiled in. Never user-supplied. */
    private val baseUrl: String = DEFAULT_SERVER_URL.trim().trimEnd('/')

    private fun request(path: String, key: String): Request.Builder {
        val builder = Request.Builder().url("$baseUrl$path")
        if (key.isNotBlank()) {
            builder.header("X-Registration-Key", key)
        }
        return builder
    }

    private fun Context.request(path: String) = request(path, registrationKey)

    private fun <T> call(builder: Request.Builder, block: (Response) -> T): T? = try {
        client.newCall(builder.build()).execute().use(block)
    } catch (error: Exception) {
        Log.w(TAG, "Request failed: ${error.message}")
        null
    }

    // --- Sign in ---------------------------------------------------------

    sealed interface SignInResult {
        /**
         * [pushEnabled] is false when the server's Firebase channel is off —
         * the app is usable but will never ring. Worth saying out loud.
         */
        data class Success(val key: String, val name: String, val pushEnabled: Boolean) : SignInResult

        data object WrongPin : SignInResult

        /** Too many wrong PINs from this phone; the server is making us wait. */
        data class TooManyAttempts(val message: String) : SignInResult

        /** The server has no PIN configured, so nobody can sign in yet. */
        data object NotConfigured : SignInResult

        data object Unreachable : SignInResult
    }

    /**
     * Exchanges a name and PIN for the registration key.
     *
     * The key is what every later call uses, so the PIN is typed once and never
     * stored. See `app/api/app_auth.py`.
     */
    fun signIn(name: String, pin: String): SignInResult {
        val payload = JSONObject()
            .put("name", name)
            .put("pin", pin)
            .toString()

        val response = call(
            request("/api/app/signin", key = "").post(payload.toRequestBody(JSON))
        ) { response ->
            response.code to (response.body?.string() ?: "")
        } ?: return SignInResult.Unreachable

        val (code, body) = response
        return when (code) {
            in 200..299 -> parseSignIn(body, name)
            401, 403 -> SignInResult.WrongPin
            429 -> SignInResult.TooManyAttempts(detailOf(body))
            503 -> SignInResult.NotConfigured
            else -> SignInResult.Unreachable
        }
    }

    private fun parseSignIn(body: String, typedName: String): SignInResult = try {
        val json = JSONObject(body)
        val key = json.optString("key", "")
        SignInResult.Success(
            key = key,
            name = json.optString("name", typedName),
            pushEnabled = json.optBoolean("push_enabled", false),
        )
    } catch (error: Exception) {
        Log.w(TAG, "Could not read sign-in reply: ${error.message}")
        SignInResult.Unreachable
    }

    /** FastAPI puts human-readable errors in `detail`. */
    private fun detailOf(body: String): String = try {
        JSONObject(body).optString("detail", "")
    } catch (error: Exception) {
        ""
    }

    // --- Device registration ---------------------------------------------

    /** Tell the backend about this device's FCM token. Safe to call repeatedly. */
    fun registerDevice(context: Context, token: String, label: String): Boolean {
        if (token.isBlank()) return false

        val payload = JSONObject()
            .put("token", token)
            .put("label", label)
            .put("platform", "android")
            .toString()

        return call(
            context.request("/api/devices").post(payload.toRequestBody(JSON))
        ) { response ->
            Log.i(TAG, "registerDevice -> HTTP ${response.code}")
            response.isSuccessful
        } ?: false
    }

    // --- Incidents --------------------------------------------------------

    /** Open incidents, newest first. Null means the server could not be reached. */
    fun openIncidents(context: Context): List<Incident>? {
        val body = call(
            context.request("/api/incidents?state=OPEN&limit=100").get()
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
        if (incidentId <= 0) return null

        val body = call(context.request("/api/incidents/$incidentId").get()) { response ->
            if (response.isSuccessful) response.body?.string() else null
        } ?: return null

        return try {
            Incident.from(JSONObject(body))
        } catch (error: Exception) {
            null
        }
    }

    fun acknowledge(context: Context, incidentId: Int): Boolean {
        if (incidentId <= 0) return false

        return call(
            context.request("/api/incidents/$incidentId/ack").post(EMPTY_BODY)
        ) { response -> response.isSuccessful } ?: false
    }

    /**
     * Raises a real incident through `IncidentService.create_incident()`, so
     * the whole notification path fires and the phone genuinely rings. This is
     * the only way to prove push delivery actually works.
     */
    fun sendTestAlert(context: Context): Boolean =
        call(context.request("/api/test-alert").post(EMPTY_BODY)) { response ->
            response.isSuccessful
        } ?: false
}
