package com.alertbot.mobile.ui

import android.Manifest
import android.content.Intent
import android.os.Build
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.navigationBarsPadding
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.statusBarsPadding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.unit.dp
import androidx.lifecycle.Lifecycle
import androidx.lifecycle.LifecycleEventObserver
import androidx.lifecycle.compose.LocalLifecycleOwner
import com.alertbot.mobile.R
import com.alertbot.mobile.data.AlarmReadiness
import com.alertbot.mobile.ui.theme.BrandBlue
import com.alertbot.mobile.ui.theme.Critical
import com.alertbot.mobile.ui.theme.Resolved
import com.alertbot.mobile.ui.theme.TextSecondary

private class Check(
    val title: String,
    val why: String,
    val satisfied: Boolean,
    val fix: () -> Unit,
)

/**
 * Three plain-language checks between the user and a phone that actually
 * rings. Re-runnable at any time from the account sheet.
 */
@Composable
fun AlarmSetupScreen(onContinue: () -> Unit) {
    val context = LocalContext.current

    // Every fix leaves the app for a system settings screen, so the state is
    // re-read on the way back in rather than cached.
    var refreshToken by remember { mutableIntStateOf(0) }
    val lifecycleOwner = LocalLifecycleOwner.current
    DisposableEffect(lifecycleOwner) {
        val observer = LifecycleEventObserver { _, event ->
            if (event == Lifecycle.Event.ON_RESUME) refreshToken++
        }
        lifecycleOwner.lifecycle.addObserver(observer)
        onDispose { lifecycleOwner.lifecycle.removeObserver(observer) }
    }

    val permissionLauncher = rememberLauncherForActivityResult(
        ActivityResultContracts.RequestPermission()
    ) { refreshToken++ }

    fun openSettings(intent: Intent) {
        runCatching { context.startActivity(intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)) }
    }

    // Keyed on refreshToken so returning from a settings screen re-reads them.
    val notificationsOk = remember(refreshToken) { AlarmReadiness.notificationsAllowed(context) }
    val batteryOk = remember(refreshToken) { AlarmReadiness.batteryUnrestricted(context) }
    val fullScreenOk = remember(refreshToken) { AlarmReadiness.fullScreenAllowed(context) }

    val checks = listOf(
        Check(
            title = stringResource(R.string.setup_notifications),
            why = stringResource(R.string.setup_notifications_why),
            satisfied = notificationsOk,
            fix = {
                if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
                    permissionLauncher.launch(Manifest.permission.POST_NOTIFICATIONS)
                } else {
                    openSettings(AlarmReadiness.notificationSettingsIntent(context))
                }
            },
        ),
        Check(
            title = stringResource(R.string.setup_battery),
            why = stringResource(R.string.setup_battery_why),
            satisfied = batteryOk,
            fix = { openSettings(AlarmReadiness.batteryIntent(context)) },
        ),
        Check(
            title = stringResource(R.string.setup_fullscreen),
            why = stringResource(R.string.setup_fullscreen_why),
            satisfied = fullScreenOk,
            fix = { openSettings(AlarmReadiness.fullScreenIntent(context)) },
        ),
    )

    Column(
        modifier = Modifier
            .fillMaxSize()
            .statusBarsPadding()
            .navigationBarsPadding()
            .verticalScroll(rememberScrollState())
            .padding(24.dp),
    ) {
        Spacer(Modifier.height(32.dp))
        Text(
            text = stringResource(R.string.setup_title),
            style = MaterialTheme.typography.headlineMedium,
            color = MaterialTheme.colorScheme.onSurface,
        )
        Spacer(Modifier.height(10.dp))
        Text(
            text = stringResource(R.string.setup_subtitle),
            style = MaterialTheme.typography.bodyLarge,
            color = TextSecondary,
        )

        Spacer(Modifier.height(28.dp))

        checks.forEach { check ->
            CheckRow(check)
            Spacer(Modifier.height(12.dp))
        }

        Spacer(Modifier.height(20.dp))

        Button(
            onClick = onContinue,
            shape = RoundedCornerShape(12.dp),
            colors = ButtonDefaults.buttonColors(containerColor = BrandBlue),
            modifier = Modifier
                .fillMaxWidth()
                .height(56.dp),
        ) {
            Text(
                text = stringResource(R.string.setup_continue),
                style = MaterialTheme.typography.labelLarge,
            )
        }
    }
}

@Composable
private fun CheckRow(check: Check) {
    Card(
        shape = RoundedCornerShape(14.dp),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
        elevation = CardDefaults.cardElevation(defaultElevation = 1.dp),
        modifier = Modifier.fillMaxWidth(),
    ) {
        Row(
            verticalAlignment = Alignment.CenterVertically,
            modifier = Modifier.padding(16.dp),
        ) {
            Icon(
                painter = painterResource(
                    if (check.satisfied) R.drawable.ic_check_circle else R.drawable.ic_error
                ),
                contentDescription = null,
                tint = if (check.satisfied) Resolved else Critical,
                modifier = Modifier.size(28.dp),
            )
            Spacer(Modifier.width(14.dp))
            Column(modifier = Modifier.weight(1f)) {
                Text(
                    text = check.title,
                    style = MaterialTheme.typography.titleMedium,
                    color = MaterialTheme.colorScheme.onSurface,
                )
                Spacer(Modifier.height(2.dp))
                Text(
                    text = check.why,
                    style = MaterialTheme.typography.bodyMedium,
                    color = TextSecondary,
                )
            }
            Spacer(Modifier.width(8.dp))
            if (check.satisfied) {
                Text(
                    text = stringResource(R.string.setup_done),
                    style = MaterialTheme.typography.labelMedium,
                    color = Resolved,
                )
            } else {
                TextButton(onClick = check.fix) {
                    Text(
                        text = stringResource(R.string.setup_fix),
                        style = MaterialTheme.typography.labelLarge,
                        color = BrandBlue,
                    )
                }
            }
        }
    }
}
