package com.alertbot.mobile

import android.content.Context
import android.util.Base64
import android.util.Log
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody
import org.json.JSONObject
import java.util.concurrent.TimeUnit

/**
 * Thin wrapper over the AlertBot REST API.
 *
 * The app holds no business logic: it registers its push token, acknowledges
 * incidents and reads health. Everything else happens on the server.
 */
object ApiClient {

    private const val TAG = "AlertBotApi"
    private val JSON = "application/json; charset=utf-8".toMediaType()

    private val client = OkHttpClient.Builder()
        .connectTimeout(15, TimeUnit.SECONDS)
        .readTimeout(20, TimeUnit.SECONDS)
        .build()

    private fun authHeader(context: Context): String? {
        if (context.username.isBlank() || context.password.isBlank()) return null
        val raw = "${context.username}:${context.password}"
        return "Basic " + Base64.encodeToString(raw.toByteArray(), Base64.NO_WRAP)
    }

    private fun request(context: Context, path: String): Request.Builder {
        val builder = Request.Builder().url("${context.baseUrl}$path")
        authHeader(context)?.let { builder.header("Authorization", it) }
        if (context.registrationKey.isNotBlank()) {
            builder.header("X-Registration-Key", context.registrationKey)
        }
        return builder
    }

    /** Tell the backend about this device's FCM token. Safe to call repeatedly. */
    fun registerDevice(context: Context, token: String, label: String): Boolean {
        if (context.baseUrl.isBlank()) return false

        val payload = JSONObject()
            .put("token", token)
            .put("label", label)
            .put("platform", "android")
            .toString()

        return try {
            client.newCall(
                request(context, "/api/devices").post(payload.toRequestBody(JSON)).build()
            ).execute().use { response ->
                Log.i(TAG, "registerDevice -> HTTP ${response.code}")
                response.isSuccessful
            }
        } catch (error: Exception) {
            Log.w(TAG, "registerDevice failed: ${error.message}")
            false
        }
    }

    fun acknowledge(context: Context, incidentId: Int): Boolean {
        if (incidentId <= 0 || context.baseUrl.isBlank()) return false
        return try {
            client.newCall(
                request(context, "/api/incidents/$incidentId/ack")
                    .post("".toRequestBody(JSON))
                    .build()
            ).execute().use { response -> response.isSuccessful }
        } catch (error: Exception) {
            Log.w(TAG, "acknowledge failed: ${error.message}")
            false
        }
    }

    fun health(context: Context): String? {
        if (context.baseUrl.isBlank()) return null
        return try {
            client.newCall(request(context, "/api/health").get().build()).execute().use { response ->
                if (response.isSuccessful) "server reachable" else "HTTP ${response.code}"
            }
        } catch (error: Exception) {
            error.message
        }
    }
}
