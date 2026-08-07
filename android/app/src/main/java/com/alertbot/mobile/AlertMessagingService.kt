package com.alertbot.mobile

import android.content.Context
import android.content.Intent
import android.os.Build
import android.util.Log
import com.alertbot.mobile.data.AlarmEvents
import com.alertbot.mobile.data.ApiClient
import com.alertbot.mobile.data.fcmToken
import com.google.firebase.messaging.FirebaseMessagingService
import com.google.firebase.messaging.RemoteMessage
import kotlin.concurrent.thread

/** Receives pushes from the backend and turns them into a loud alarm. */
class AlertMessagingService : FirebaseMessagingService() {

    override fun onNewToken(token: String) {
        Log.i(TAG, "New FCM token")
        fcmToken = token
        thread {
            ApiClient.registerDevice(this, token, Build.MODEL ?: "android")
        }
    }

    override fun onMessageReceived(message: RemoteMessage) {
        val data = message.data
        val title = data["title"] ?: message.notification?.title ?: "AlertBot incident"
        val body = data["message"] ?: message.notification?.body ?: ""
        val incidentId = data["incident_id"]?.toIntOrNull() ?: 0
        val isAlarm = data["alarm"] != "0"

        Log.i(TAG, "Push received: incident=$incidentId alarm=$isAlarm")

        if (isAlarm) {
            // Recorded before anything else, so "Send a test alert" can tell
            // the difference between the server accepting a test and this
            // phone actually being reached.
            AlarmEvents.recordAlarm()

            val payload = AlarmPayload(
                incidentId = incidentId,
                service = data["service"]?.takeIf { it.isNotBlank() } ?: title,
                reason = data["reason"]?.takeIf { it.isNotBlank() } ?: body,
            )
            AlarmNotifier.raise(this, payload, title, body)
        } else {
            AlarmNotifier.raiseQuiet(this, incidentId, title, body)
        }
    }

    companion object {
        private const val TAG = "AlertBotFCM"
    }
}

/** Handles the "Acknowledge" action straight from the notification shade. */
class AckReceiver : android.content.BroadcastReceiver() {

    override fun onReceive(context: Context, intent: Intent) {
        val incidentId = intent.getIntExtra(AlarmActivity.EXTRA_INCIDENT_ID, 0)
        AlarmPlayer.stop()
        AlarmNotifier.clear(context, incidentId)

        val pending = goAsync()
        thread {
            try {
                ApiClient.acknowledge(context, incidentId)
            } finally {
                pending.finish()
            }
        }
    }
}
