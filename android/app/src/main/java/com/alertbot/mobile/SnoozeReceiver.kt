package com.alertbot.mobile

import android.app.AlarmManager
import android.app.PendingIntent
import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.util.Log
import com.alertbot.mobile.data.ApiClient
import com.alertbot.mobile.data.SNOOZE_MINUTES
import kotlin.concurrent.thread

/**
 * Makes "Snooze" mean what it says.
 *
 * The previous button silenced the phone and finished the activity — nothing
 * ever came back, so a snoozed alarm was really a dismissed one. This schedules
 * a real wake-up, and when it fires it asks the server whether the incident
 * still needs anybody before making noise again.
 */
class SnoozeReceiver : BroadcastReceiver() {

    override fun onReceive(context: Context, intent: Intent) {
        val payload = AlarmPayload.from(intent)

        if (intent.action == ACTION_SNOOZE_NOW) {
            // Snoozed from the notification shade rather than the alarm screen.
            AlarmPlayer.stop()
            AlarmNotifier.clear(context, payload.incidentId)
            schedule(context, payload)
            return
        }

        // The snooze expired.
        AlarmNotifier.clear(context, payload.incidentId)

        val pending = goAsync()
        thread {
            try {
                if (stillNeedsAttention(context, payload.incidentId)) {
                    // A background receiver cannot start an activity, so this
                    // goes out as a full-screen-intent notification only.
                    AlarmNotifier.raise(
                        context = context,
                        payload = payload,
                        title = payload.service,
                        body = payload.reason,
                        attemptDirectLaunch = false,
                    )
                } else {
                    Log.i(TAG, "Snooze expired but incident ${payload.incidentId} is handled")
                }
            } finally {
                pending.finish()
            }
        }
    }

    /**
     * True unless the server says this is already resolved or acknowledged. A
     * server we cannot reach is treated as "still broken" — a false alarm is a
     * far cheaper mistake than a silent one.
     */
    private fun stillNeedsAttention(context: Context, incidentId: Int): Boolean {
        if (incidentId <= 0) return true
        val incident = ApiClient.incident(context, incidentId) ?: return true
        return incident.isOpen && !incident.acknowledged
    }

    companion object {
        private const val TAG = "AlertBotSnooze"
        const val ACTION_SNOOZE_NOW = "com.alertbot.mobile.SNOOZE_NOW"
        private const val ACTION_SNOOZE_EXPIRED = "com.alertbot.mobile.SNOOZE_EXPIRED"

        fun schedule(context: Context, payload: AlarmPayload) {
            val alarms = context.getSystemService(AlarmManager::class.java) ?: return

            val pending = PendingIntent.getBroadcast(
                context,
                payload.incidentId + 300_000,
                payload.writeTo(Intent(context, SnoozeReceiver::class.java))
                    .setAction(ACTION_SNOOZE_EXPIRED),
                PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE,
            )

            val triggerAt = System.currentTimeMillis() + SNOOZE_MINUTES * 60_000L

            // Exact where allowed, inexact where the OS refuses: a snooze that
            // returns a minute late still beats one that never returns.
            try {
                alarms.setExactAndAllowWhileIdle(AlarmManager.RTC_WAKEUP, triggerAt, pending)
            } catch (error: SecurityException) {
                Log.w(TAG, "Exact alarms not permitted, falling back: ${error.message}")
                alarms.setAndAllowWhileIdle(AlarmManager.RTC_WAKEUP, triggerAt, pending)
            }
        }
    }
}
