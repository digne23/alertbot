package com.alertbot.mobile.data

import android.app.NotificationManager
import android.content.Context
import android.content.Intent
import android.net.Uri
import android.os.Build
import android.os.PowerManager
import android.provider.Settings
import androidx.core.app.NotificationManagerCompat

/**
 * The three settings that decide whether this phone can actually wake someone.
 *
 * A Galaxy A15 on One UI will happily doze an app it thinks is idle and then
 * never ring at 3am. Rather than bury that in a FAQ, the app checks each one
 * and offers to fix it.
 */
object AlarmReadiness {

    fun notificationsAllowed(context: Context): Boolean =
        NotificationManagerCompat.from(context).areNotificationsEnabled()

    fun batteryUnrestricted(context: Context): Boolean {
        val power = context.getSystemService(Context.POWER_SERVICE) as? PowerManager
            ?: return true
        return power.isIgnoringBatteryOptimizations(context.packageName)
    }

    /**
     * Android 14 made full-screen intents opt-in for apps that aren't phone or
     * clock apps. Without it, an alarm cannot turn the screen on by itself.
     */
    fun fullScreenAllowed(context: Context): Boolean {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.UPSIDE_DOWN_CAKE) return true
        val manager = context.getSystemService(NotificationManager::class.java) ?: return true
        return manager.canUseFullScreenIntent()
    }

    fun allGood(context: Context): Boolean =
        notificationsAllowed(context) &&
            batteryUnrestricted(context) &&
            fullScreenAllowed(context)

    fun notificationSettingsIntent(context: Context): Intent =
        Intent(Settings.ACTION_APP_NOTIFICATION_SETTINGS)
            .putExtra(Settings.EXTRA_APP_PACKAGE, context.packageName)

    @Suppress("BatteryLife") // The whole product is "ring at 3am".
    fun batteryIntent(context: Context): Intent =
        Intent(Settings.ACTION_REQUEST_IGNORE_BATTERY_OPTIMIZATIONS)
            .setData(Uri.parse("package:${context.packageName}"))

    fun fullScreenIntent(context: Context): Intent =
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.UPSIDE_DOWN_CAKE) {
            Intent(Settings.ACTION_MANAGE_APP_USE_FULL_SCREEN_INTENT)
                .setData(Uri.parse("package:${context.packageName}"))
        } else {
            notificationSettingsIntent(context)
        }
}
