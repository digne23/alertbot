package com.alertbot.mobile

import android.app.NotificationManager
import android.app.PendingIntent
import android.content.Context
import android.content.Intent
import android.os.Build
import android.util.Log
import androidx.core.app.NotificationCompat
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
            showAlarm(incidentId, title, body, data["service"] ?: "", data["reason"] ?: body)
        } else {
            showQuiet(incidentId, title, body)
        }
    }

    private fun showAlarm(incidentId: Int, title: String, body: String, service: String, reason: String) {
        val fullScreen = Intent(this, AlarmActivity::class.java).apply {
            addFlags(Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TOP)
            putExtra(AlarmActivity.EXTRA_INCIDENT_ID, incidentId)
            putExtra(AlarmActivity.EXTRA_TITLE, title)
            putExtra(AlarmActivity.EXTRA_MESSAGE, body)
            putExtra(AlarmActivity.EXTRA_SERVICE, service)
            putExtra(AlarmActivity.EXTRA_REASON, reason)
        }

        val flags = PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
        val fullScreenIntent = PendingIntent.getActivity(this, incidentId, fullScreen, flags)

        val ackIntent = PendingIntent.getBroadcast(
            this,
            incidentId + 100000,
            Intent(this, AckReceiver::class.java).putExtra(AlarmActivity.EXTRA_INCIDENT_ID, incidentId),
            flags
        )

        val notification = NotificationCompat.Builder(this, AlertBotApp.CHANNEL_ALARM)
            .setSmallIcon(android.R.drawable.stat_sys_warning)
            .setContentTitle(title)
            .setContentText(body)
            .setStyle(NotificationCompat.BigTextStyle().bigText(body))
            .setPriority(NotificationCompat.PRIORITY_MAX)
            .setCategory(NotificationCompat.CATEGORY_ALARM)
            .setVisibility(NotificationCompat.VISIBILITY_PUBLIC)
            .setOngoing(true)
            .setAutoCancel(false)
            .setFullScreenIntent(fullScreenIntent, true)
            .setContentIntent(fullScreenIntent)
            .addAction(android.R.drawable.ic_menu_send, "Acknowledge", ackIntent)
            .build()

        getSystemService(NotificationManager::class.java)
            .notify(NOTIFICATION_BASE + incidentId, notification)

        // Start the full-screen alarm directly too: on many OEM ROMs the
        // full-screen intent alone is unreliable when the screen is off.
        try {
            startActivity(fullScreen)
        } catch (error: Exception) {
            Log.w(TAG, "Could not start AlarmActivity: ${error.message}")
        }
    }

    private fun showQuiet(incidentId: Int, title: String, body: String) {
        val open = PendingIntent.getActivity(
            this,
            incidentId,
            Intent(this, MainActivity::class.java),
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
        )

        val notification = NotificationCompat.Builder(this, AlertBotApp.CHANNEL_INFO)
            .setSmallIcon(android.R.drawable.stat_notify_sync)
            .setContentTitle(title)
            .setContentText(body)
            .setStyle(NotificationCompat.BigTextStyle().bigText(body))
            .setAutoCancel(true)
            .setContentIntent(open)
            .build()

        val manager = getSystemService(NotificationManager::class.java)
        manager.cancel(NOTIFICATION_BASE + incidentId)   // stop the alarm notification
        manager.notify(NOTIFICATION_BASE + 500000 + incidentId, notification)
        AlarmPlayer.stop()
    }

    companion object {
        private const val TAG = "AlertBotFCM"
        const val NOTIFICATION_BASE = 9000
    }
}

/** Handles the "Acknowledge" action straight from the notification shade. */
class AckReceiver : android.content.BroadcastReceiver() {

    override fun onReceive(context: Context, intent: Intent) {
        val incidentId = intent.getIntExtra(AlarmActivity.EXTRA_INCIDENT_ID, 0)
        AlarmPlayer.stop()
        context.getSystemService(NotificationManager::class.java)
            .cancel(AlertMessagingService.NOTIFICATION_BASE + incidentId)

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
