package com.alertbot.mobile

import android.Manifest
import android.content.pm.PackageManager
import android.os.Build
import android.os.Bundle
import android.widget.Button
import android.widget.EditText
import android.widget.TextView
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import androidx.core.content.ContextCompat
import com.google.firebase.messaging.FirebaseMessaging
import kotlin.concurrent.thread

/**
 * Setup screen. Point the app at an AlertBot server, register the push token,
 * and prove the whole path works with a test alarm.
 */
class MainActivity : AppCompatActivity() {

    private lateinit var status: TextView

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)

        status = findViewById(R.id.status)

        findViewById<EditText>(R.id.input_url).setText(baseUrl)
        findViewById<EditText>(R.id.input_user).setText(username)
        findViewById<EditText>(R.id.input_password).setText(password)
        findViewById<EditText>(R.id.input_key).setText(registrationKey)

        findViewById<Button>(R.id.button_save).setOnClickListener { saveAndRegister() }
        findViewById<Button>(R.id.button_test).setOnClickListener { previewAlarm() }

        requestNotificationPermission()
        refreshStatus()
    }

    private fun requestNotificationPermission() {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.TIRAMISU) return
        val granted = ContextCompat.checkSelfPermission(this, Manifest.permission.POST_NOTIFICATIONS)
        if (granted != PackageManager.PERMISSION_GRANTED) {
            requestPermissions(arrayOf(Manifest.permission.POST_NOTIFICATIONS), 1)
        }
    }

    private fun saveAndRegister() {
        baseUrl = findViewById<EditText>(R.id.input_url).text.toString().trim()
        username = findViewById<EditText>(R.id.input_user).text.toString().trim()
        password = findViewById<EditText>(R.id.input_password).text.toString()
        registrationKey = findViewById<EditText>(R.id.input_key).text.toString().trim()

        if (baseUrl.isBlank()) {
            Toast.makeText(this, R.string.url_required, Toast.LENGTH_SHORT).show()
            return
        }

        status.text = getString(R.string.registering)

        FirebaseMessaging.getInstance().token.addOnCompleteListener { task ->
            if (!task.isSuccessful) {
                status.text = getString(R.string.token_failed, task.exception?.message ?: "")
                return@addOnCompleteListener
            }

            val token = task.result
            fcmToken = token

            thread {
                val registered = ApiClient.registerDevice(this, token, Build.MODEL ?: "android")
                val health = ApiClient.health(this)
                runOnUiThread {
                    status.text = if (registered) {
                        getString(R.string.registered, health ?: "")
                    } else {
                        getString(R.string.register_failed, health ?: "")
                    }
                }
            }
        }
    }

    /** Shows the alarm screen locally so you can hear it without waiting for
     *  a real incident. Nothing is sent to the server. */
    private fun previewAlarm() {
        startActivity(
            android.content.Intent(this, AlarmActivity::class.java)
                .putExtra(AlarmActivity.EXTRA_INCIDENT_ID, 0)
                .putExtra(AlarmActivity.EXTRA_TITLE, getString(R.string.preview_title))
                .putExtra(AlarmActivity.EXTRA_SERVICE, "portal.esicia.rw")
                .putExtra(AlarmActivity.EXTRA_MESSAGE, getString(R.string.preview_message))
        )
    }

    private fun refreshStatus() {
        status.text = when {
            baseUrl.isBlank() -> getString(R.string.not_configured)
            fcmToken.isBlank() -> getString(R.string.no_token)
            else -> getString(R.string.configured, baseUrl)
        }
    }
}
