package com.alertbot.mobile.data

import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow

/**
 * A single bit of shared state: when a push last actually arrived on this
 * phone.
 *
 * The "Send a test alert" flow uses it to tell the difference between "the
 * server accepted the test" and "the alarm reached you" — which are very
 * different things, and only the second one is worth trusting.
 */
object AlarmEvents {

    private val _lastAlarmAt = MutableStateFlow(0L)
    val lastAlarmAt: StateFlow<Long> = _lastAlarmAt

    fun recordAlarm() {
        _lastAlarmAt.value = System.currentTimeMillis()
    }
}
