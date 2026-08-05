package com.alertbot.mobile

import android.content.Context
import android.media.AudioAttributes
import android.media.AudioManager
import android.media.MediaPlayer
import android.media.RingtoneManager
import android.os.Build
import android.os.VibrationEffect
import android.os.Vibrator
import android.os.VibratorManager
import android.util.Log

/**
 * Plays the alarm at full volume on the alarm stream and vibrates until
 * somebody acknowledges. Deliberately global so the notification action, the
 * alarm screen and a recovery push can all stop it.
 */
object AlarmPlayer {

    private const val TAG = "AlertBotAlarm"

    private var player: MediaPlayer? = null
    private var vibrator: Vibrator? = null
    private var previousVolume: Int? = null

    @Synchronized
    fun start(context: Context) {
        if (player?.isPlaying == true) return

        val audio = context.getSystemService(Context.AUDIO_SERVICE) as AudioManager
        try {
            previousVolume = audio.getStreamVolume(AudioManager.STREAM_ALARM)
            audio.setStreamVolume(
                AudioManager.STREAM_ALARM,
                audio.getStreamMaxVolume(AudioManager.STREAM_ALARM),
                0
            )
        } catch (error: Exception) {
            Log.w(TAG, "Could not raise alarm volume: ${error.message}")
        }

        val uri = RingtoneManager.getDefaultUri(RingtoneManager.TYPE_ALARM)
            ?: RingtoneManager.getDefaultUri(RingtoneManager.TYPE_RINGTONE)

        try {
            player = MediaPlayer().apply {
                setDataSource(context, uri)
                setAudioAttributes(
                    AudioAttributes.Builder()
                        .setUsage(AudioAttributes.USAGE_ALARM)
                        .setContentType(AudioAttributes.CONTENT_TYPE_SONIFICATION)
                        .build()
                )
                isLooping = true
                prepare()
                start()
            }
        } catch (error: Exception) {
            Log.w(TAG, "Could not play alarm: ${error.message}")
        }

        vibrator = vibratorOf(context).also { device ->
            val pattern = longArrayOf(0, 800, 400, 800, 400)
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                device?.vibrate(VibrationEffect.createWaveform(pattern, 0))
            } else {
                @Suppress("DEPRECATION")
                device?.vibrate(pattern, 0)
            }
        }
    }

    @Synchronized
    fun stop() {
        try {
            player?.stop()
            player?.release()
        } catch (error: Exception) {
            Log.w(TAG, "Could not stop alarm: ${error.message}")
        }
        player = null

        vibrator?.cancel()
        vibrator = null
    }

    private fun vibratorOf(context: Context): Vibrator? =
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
            (context.getSystemService(Context.VIBRATOR_MANAGER_SERVICE) as? VibratorManager)?.defaultVibrator
        } else {
            @Suppress("DEPRECATION")
            context.getSystemService(Context.VIBRATOR_SERVICE) as? Vibrator
        }
}
