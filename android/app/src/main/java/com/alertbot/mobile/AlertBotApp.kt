package com.alertbot.mobile

import android.app.Application
import android.app.NotificationChannel
import android.app.NotificationManager
import android.media.AudioAttributes
import android.media.RingtoneManager
import android.os.Build

class AlertBotApp : Application() {

    override fun onCreate() {
        super.onCreate()
        createChannels()
    }

    /**
     * Two channels: one that behaves like an alarm (max importance, alarm
     * sound, bypasses Do Not Disturb) and a quiet one for recovery notices.
     */
    private fun createChannels() {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.O) return

        val manager = getSystemService(NotificationManager::class.java)

        val alarmSound = RingtoneManager.getDefaultUri(RingtoneManager.TYPE_ALARM)
        val audioAttributes = AudioAttributes.Builder()
            .setUsage(AudioAttributes.USAGE_ALARM)
            .setContentType(AudioAttributes.CONTENT_TYPE_SONIFICATION)
            .build()

        val alarm = NotificationChannel(
            CHANNEL_ALARM,
            "Incident alarms",
            NotificationManager.IMPORTANCE_HIGH
        ).apply {
            description = "Wakes you up when a service goes down."
            enableVibration(true)
            vibrationPattern = longArrayOf(0, 600, 300, 600, 300, 600)
            setSound(alarmSound, audioAttributes)
            setBypassDnd(true)
            lockscreenVisibility = android.app.Notification.VISIBILITY_PUBLIC
        }

        val info = NotificationChannel(
            CHANNEL_INFO,
            "Recovery notices",
            NotificationManager.IMPORTANCE_DEFAULT
        ).apply {
            description = "Sent when a service comes back up."
        }

        manager.createNotificationChannel(alarm)
        manager.createNotificationChannel(info)
    }

    companion object {
        const val CHANNEL_ALARM = "alertbot_alarm"
        const val CHANNEL_INFO = "alertbot_info"
    }
}
