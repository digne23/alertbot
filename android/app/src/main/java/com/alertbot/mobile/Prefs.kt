package com.alertbot.mobile

import android.content.Context
import android.content.SharedPreferences

/** Where the app stores which AlertBot server it talks to. */
private const val PREFS_FILE = "alertbot"

private fun Context.prefs(): SharedPreferences =
    getSharedPreferences(PREFS_FILE, Context.MODE_PRIVATE)

private fun Context.read(key: String): String = prefs().getString(key, "") ?: ""

private fun Context.write(key: String, value: String) {
    prefs().edit().putString(key, value).apply()
}

var Context.baseUrl: String
    get() = read("base_url").trimEnd('/')
    set(value) = write("base_url", value.trim().trimEnd('/'))

var Context.username: String
    get() = read("username")
    set(value) = write("username", value.trim())

var Context.password: String
    get() = read("password")
    set(value) = write("password", value)

var Context.registrationKey: String
    get() = read("registration_key")
    set(value) = write("registration_key", value.trim())

var Context.fcmToken: String
    get() = read("fcm_token")
    set(value) = write("fcm_token", value)

val Context.isConfigured: Boolean
    get() = baseUrl.isNotBlank()
