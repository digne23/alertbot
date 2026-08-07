package com.alertbot.mobile.data

import android.content.Context
import android.os.Build
import android.util.Log
import com.google.firebase.messaging.FirebaseMessaging
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.suspendCancellableCoroutine
import kotlinx.coroutines.withContext
import kotlin.coroutines.resume

private const val TAG = "AlertBotPush"

/** This device's FCM registration token, or null if Firebase could not issue one. */
suspend fun currentPushToken(): String? = suspendCancellableCoroutine { continuation ->
    FirebaseMessaging.getInstance().token.addOnCompleteListener { task ->
        if (task.isSuccessful) {
            continuation.resume(task.result)
        } else {
            Log.w(TAG, "No FCM token: ${task.exception?.message}")
            continuation.resume(null)
        }
    }
}

/**
 * Hands this phone's push token to the server so it can be alarmed.
 *
 * Returns false when there is no token or the server rejected it — the caller
 * should say so rather than pretend the phone is covered.
 */
suspend fun registerThisDevice(context: Context): Boolean = withContext(Dispatchers.IO) {
    val token = currentPushToken() ?: return@withContext false
    context.fcmToken = token
    ApiClient.registerDevice(context, token, Build.MODEL ?: "android")
}
