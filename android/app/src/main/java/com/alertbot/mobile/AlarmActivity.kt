package com.alertbot.mobile

import android.app.KeyguardManager
import android.content.Context
import android.content.Intent
import android.os.Build
import android.os.Bundle
import android.view.WindowManager
import android.widget.Toast
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.lifecycle.lifecycleScope
import com.alertbot.mobile.data.ApiClient
import com.alertbot.mobile.ui.AlarmScreen
import com.alertbot.mobile.ui.theme.AlertBotTheme
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext

/**
 * Full-screen alarm shown over the lock screen. One job: be impossible to
 * ignore, and acknowledge the incident with one tap.
 *
 * The window flags in [showOverLockScreen] are the part that actually decides
 * whether anyone gets woken, and are unchanged from the original XML version —
 * only the surface they wrap is new.
 */
class AlarmActivity : ComponentActivity() {

    /** Held at class level so [onNewIntent] can swap in a newer incident. */
    private val payload = mutableStateOf(AlarmPayload(0, "AlertBot", ""))

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        showOverLockScreen()
        payload.value = AlarmPayload.from(intent)
        AlarmPlayer.start(this)

        setContent {
            AlertBotTheme {
                val current by payload
                var acknowledging by remember { mutableStateOf(false) }
                var ackFailed by remember { mutableStateOf(false) }

                AlarmScreen(
                    service = current.service,
                    reason = current.reason,
                    incidentId = current.incidentId,
                    acknowledging = acknowledging,
                    ackFailed = ackFailed,
                    onAcknowledge = {
                        acknowledging = true
                        ackFailed = false

                        // Silence first, ask the server second: the person in
                        // front of the phone has already made their decision.
                        AlarmPlayer.stop()
                        AlarmNotifier.clear(this, current.incidentId)

                        lifecycleScope.launch {
                            val ok = withContext(Dispatchers.IO) {
                                ApiClient.acknowledge(this@AlarmActivity, current.incidentId)
                            }
                            acknowledging = false
                            if (ok || current.incidentId <= 0) {
                                finish()
                            } else {
                                ackFailed = true
                            }
                        }
                    },
                    onSnooze = {
                        AlarmPlayer.stop()
                        AlarmNotifier.clear(this, current.incidentId)
                        SnoozeReceiver.schedule(this, current)
                        Toast.makeText(this, R.string.alarm_snoozed, Toast.LENGTH_LONG).show()
                        finish()
                    },
                )
            }
        }
    }

    /** A second incident arriving while this screen is up replaces what it shows. */
    override fun onNewIntent(intent: Intent) {
        super.onNewIntent(intent)
        setIntent(intent)
        payload.value = AlarmPayload.from(intent)
        AlarmPlayer.start(this)
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

/** Everything the alarm screen shows, and everything a snooze has to carry. */
data class AlarmPayload(
    val incidentId: Int,
    val service: String,
    val reason: String,
) {
    fun writeTo(intent: Intent): Intent = intent
        .putExtra(AlarmActivity.EXTRA_INCIDENT_ID, incidentId)
        .putExtra(AlarmActivity.EXTRA_SERVICE, service)
        .putExtra(AlarmActivity.EXTRA_REASON, reason)
        .putExtra(AlarmActivity.EXTRA_MESSAGE, reason)

    companion object {
        fun from(intent: Intent?): AlarmPayload {
            val service = intent?.getStringExtra(AlarmActivity.EXTRA_SERVICE)?.takeIf {
                it.isNotBlank()
            }
            val title = intent?.getStringExtra(AlarmActivity.EXTRA_TITLE)?.takeIf {
                it.isNotBlank()
            }
            val reason = intent?.getStringExtra(AlarmActivity.EXTRA_REASON)?.takeIf {
                it.isNotBlank()
            } ?: intent?.getStringExtra(AlarmActivity.EXTRA_MESSAGE)

            return AlarmPayload(
                incidentId = intent?.getIntExtra(AlarmActivity.EXTRA_INCIDENT_ID, 0) ?: 0,
                service = service ?: title ?: "AlertBot",
                reason = reason.orEmpty(),
            )
        }
    }
}
