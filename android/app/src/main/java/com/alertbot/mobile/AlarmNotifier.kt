package com.alertbot.mobile

import android.app.NotificationManager
import android.app.PendingIntent
import android.content.Context
import android.content.Intent
import android.util.Log
import androidx.core.app.NotificationCompat

/**
 * Turns an incident into the loud, un-dismissable notification that carries a
 * full-screen intent.
 *
 * Shared by the push path ([AlertMessagingService]) and the snooze path
 * ([SnoozeReceiver]) so a snoozed alarm comes back looking exactly like the
 * original — and, more importantly, so it comes back at all. A broadcast
 * receiver cannot start an activity in the background on Android 10+; a
 * full-screen-intent notification is the supported way to get the screen on.
 */
object AlarmNotifier {

    private const val TAG = "AlertBotAlarm"
    const val NOTIFICATION_BASE = 9000

    private fun flags() = PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE

    fun alarmIntent(context: Context, payload: AlarmPayload): Intent =
        payload.writeTo(Intent(context, AlarmActivity::class.java)).apply {
            addFlags(Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TOP)
        }

    /** Raise the alarm for [payload]. [attemptDirectLaunch] is false from a
     *  background receiver, where an activity start would be blocked anyway. */
    fun raise(
        context: Context,
        payload: AlarmPayload,
        title: String,
        body: String,
        attemptDirectLaunch: Boolean = true,
    ) {
        val fullScreen = alarmIntent(context, payload)
        val fullScreenPending =
            PendingIntent.getActivity(context, payload.incidentId, fullScreen, flags())

        val ackPending = PendingIntent.getBroadcast(
            context,
            payload.incidentId + 100_000,
            Intent(context, AckReceiver::class.java)
                .putExtra(AlarmActivity.EXTRA_INCIDENT_ID, payload.incidentId),
            flags(),
        )

        val snoozePending = PendingIntent.getBroadcast(
            context,
            payload.incidentId + 200_000,
            payload.writeTo(Intent(context, SnoozeReceiver::class.java))
                .setAction(SnoozeReceiver.ACTION_SNOOZE_NOW),
            flags(),
        )

        val notification = NotificationCompat.Builder(context, AlertBotApp.CHANNEL_ALARM)
            .setSmallIcon(R.drawable.ic_stat_alert)
            .setContentTitle(title)
            .setContentText(body)
            .setStyle(NotificationCompat.BigTextStyle().bigText(body))
            .setPriority(NotificationCompat.PRIORITY_MAX)
            .setCategory(NotificationCompat.CATEGORY_ALARM)
            .setVisibility(NotificationCompat.VISIBILITY_PUBLIC)
            .setOngoing(true)
            .setAutoCancel(false)
            .setFullScreenIntent(fullScreenPending, true)
            .setContentIntent(fullScreenPending)
            .addAction(R.drawable.ic_check_circle, context.getString(R.string.notify_ack), ackPending)
            .addAction(R.drawable.ic_refresh, context.getString(R.string.notify_snooze), snoozePending)
            .build()

        manager(context).notify(NOTIFICATION_BASE + payload.incidentId, notification)

        // On many OEM ROMs the full-screen intent alone is unreliable when the
        // screen is off, so the push path also starts the activity directly.
        if (attemptDirectLaunch) {
            try {
                context.startActivity(fullScreen)
            } catch (error: Exception) {
                Log.w(TAG, "Could not start AlarmActivity: ${error.message}")
            }
        }
    }

    /** Quiet notice — a service came back up. Cancels any alarm for the same id. */
    fun raiseQuiet(context: Context, incidentId: Int, title: String, body: String) {
        val open = PendingIntent.getActivity(
            context,
            incidentId,
            Intent(context, MainActivity::class.java)
                .putExtra(MainActivity.EXTRA_INCIDENT_ID, incidentId),
            flags(),
        )

        val notification = NotificationCompat.Builder(context, AlertBotApp.CHANNEL_INFO)
            .setSmallIcon(R.drawable.ic_stat_alert)
            .setContentTitle(title)
            .setContentText(body)
            .setStyle(NotificationCompat.BigTextStyle().bigText(body))
            .setAutoCancel(true)
            .setContentIntent(open)
            .build()

        clear(context, incidentId)
        manager(context).notify(NOTIFICATION_BASE + 500_000 + incidentId, notification)
        AlarmPlayer.stop()
    }

    fun clear(context: Context, incidentId: Int) {
        manager(context).cancel(NOTIFICATION_BASE + incidentId)
    }

    private fun manager(context: Context): NotificationManager =
        context.getSystemService(NotificationManager::class.java)
}
