package com.alertbot.mobile

import android.app.KeyguardManager
import android.app.NotificationManager
import android.content.Context
import android.os.Build
import android.os.Bundle
import android.view.WindowManager
import android.widget.Button
import android.widget.TextView
import androidx.appcompat.app.AppCompatActivity
import kotlin.concurrent.thread

/**
 * Full-screen alarm shown over the lock screen. One job: be impossible to
 * ignore, and acknowledge the incident with one tap.
 */
class AlarmActivity : AppCompatActivity() {

    private var incidentId = 0

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        showOverLockScreen()
        setContentView(R.layout.activity_alarm)

        incidentId = intent.getIntExtra(EXTRA_INCIDENT_ID, 0)
        val title = intent.getStringExtra(EXTRA_TITLE) ?: "Incident"
        val message = intent.getStringExtra(EXTRA_MESSAGE) ?: ""
        val service = intent.getStringExtra(EXTRA_SERVICE) ?: ""

        findViewById<TextView>(R.id.alarm_title).text = title
        findViewById<TextView>(R.id.alarm_service).text = service.ifBlank { "AlertBot" }
        findViewById<TextView>(R.id.alarm_message).text = message
        findViewById<TextView>(R.id.alarm_incident).text =
            if (incidentId > 0) "Incident #$incidentId" else ""

        AlarmPlayer.start(this)

        findViewById<Button>(R.id.alarm_ack).setOnClickListener { acknowledge() }
        findViewById<Button>(R.id.alarm_snooze).setOnClickListener { dismissWithoutAck() }
    }

    private fun showOverLockScreen() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O_MR1) {
            setShowWhenLocked(true)
            setTurnScreenOn(true)
            (getSystemService(Context.KEYGUARD_SERVICE) as KeyguardManager)
                .requestDismissKeyguard(this, null)
        } else {
            @Suppress("DEPRECATION")
            window.addFlags(
                WindowManager.LayoutParams.FLAG_SHOW_WHEN_LOCKED or
                    WindowManager.LayoutParams.FLAG_TURN_SCREEN_ON or
                    WindowManager.LayoutParams.FLAG_DISMISS_KEYGUARD
            )
        }
        window.addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON)
    }

    private fun acknowledge() {
        val button = findViewById<Button>(R.id.alarm_ack)
        button.isEnabled = false
        button.text = getString(R.string.acknowledging)

        AlarmPlayer.stop()
        clearNotification()

        thread {
            val ok = ApiClient.acknowledge(this, incidentId)
            runOnUiThread {
                if (ok) {
                    finish()
                } else {
                    button.isEnabled = true
                    button.text = getString(R.string.ack_retry)
                }
            }
        }
    }

    /** Stops the noise on this phone but leaves the incident unacknowledged,
     *  so the backend keeps escalating. */
    private fun dismissWithoutAck() {
        AlarmPlayer.stop()
        clearNotification()
        finish()
    }

    private fun clearNotification() {
        getSystemService(NotificationManager::class.java)
            .cancel(AlertMessagingService.NOTIFICATION_BASE + incidentId)
    }

    override fun onDestroy() {
        super.onDestroy()
        AlarmPlayer.stop()
    }

    companion object {
        const val EXTRA_INCIDENT_ID = "incident_id"
        const val EXTRA_TITLE = "title"
        const val EXTRA_MESSAGE = "message"
        const val EXTRA_SERVICE = "service"
        const val EXTRA_REASON = "reason"
    }
}
