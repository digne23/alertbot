package com.alertbot.mobile.data

import android.content.Context
import android.content.SharedPreferences
import android.util.Log
import androidx.security.crypto.EncryptedSharedPreferences
import androidx.security.crypto.MasterKey

/**
 * Everything this app remembers: who this phone belongs to, the key it uses to
 * talk to the server, and the push token.
 *
 * There is no server address here — that is baked into [DEFAULT_SERVER_URL] —
 * and no password. The user types a PIN once; what gets stored is the
 * registration key the server hands back in exchange, never the PIN itself.
 *
 * That key is a real credential, so it lives in [EncryptedSharedPreferences]
 * rather than plaintext. If the device keystore is unavailable — some OEM ROMs,
 * a corrupted key after a restore — we fall back to ordinary preferences rather
 * than refusing to sign in. Being woken up matters more than the storage tier,
 * and the fallback is logged.
 *
 * `allowBackup` is off in the manifest for the same reason: a restored backup
 * would carry ciphertext this device's keystore cannot read.
 */
private const val SECURE_FILE = "alertbot_secure"
private const val FALLBACK_FILE = "alertbot"
private const val TAG = "AlertBotPrefs"

private var cachedStore: SharedPreferences? = null

@Synchronized
private fun Context.store(): SharedPreferences {
    cachedStore?.let { return it }

    val resolved = try {
        val masterKey = MasterKey.Builder(applicationContext)
            .setKeyScheme(MasterKey.KeyScheme.AES256_GCM)
            .build()
        EncryptedSharedPreferences.create(
            applicationContext,
            SECURE_FILE,
            masterKey,
            EncryptedSharedPreferences.PrefKeyEncryptionScheme.AES256_SIV,
            EncryptedSharedPreferences.PrefValueEncryptionScheme.AES256_GCM,
        )
    } catch (error: Exception) {
        Log.w(TAG, "Encrypted storage unavailable, falling back: ${error.message}")
        applicationContext.getSharedPreferences(FALLBACK_FILE, Context.MODE_PRIVATE)
    }

    cachedStore = resolved
    return resolved
}

private fun Context.read(key: String): String = store().getString(key, "") ?: ""

private fun Context.write(key: String, value: String) {
    store().edit().putString(key, value).apply()
}

/**
 * The name the user typed at sign-in. Purely a label: it identifies this phone
 * in the dashboard's device list and in the account sheet. With a shared PIN
 * there is no per-person account behind it.
 */
var Context.displayName: String
    get() = read("display_name")
    set(value) = write("display_name", value.trim())

/**
 * The server's `DEVICE_REGISTRATION_KEY`. Never typed by a user: the server
 * returns it from `POST /api/app/signin` once the PIN has been accepted. It is
 * what authenticates every subsequent call.
 */
var Context.registrationKey: String
    get() = read("registration_key")
    set(value) = write("registration_key", value.trim())

var Context.fcmToken: String
    get() = read("fcm_token")
    set(value) = write("fcm_token", value)

/** True once a sign-in has actually succeeded against the server. */
var Context.isSignedIn: Boolean
    get() = read("signed_in") == "1"
    set(value) = write("signed_in", if (value) "1" else "")

/** True once the user has been walked through the alarm-permission checks. */
var Context.setupSeen: Boolean
    get() = read("setup_seen") == "1"
    set(value) = write("setup_seen", if (value) "1" else "")

fun Context.signOut() {
    store().edit()
        .remove("display_name")
        .remove("registration_key")
        .remove("signed_in")
        .remove("setup_seen")
        .apply()
}
