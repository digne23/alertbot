package com.alertbot.mobile

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.BackHandler
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.res.stringResource
import com.alertbot.mobile.data.isSignedIn
import com.alertbot.mobile.data.setupSeen
import com.alertbot.mobile.ui.AlarmSetupScreen
import com.alertbot.mobile.ui.AlertsScreen
import com.alertbot.mobile.ui.IncidentDetailScreen
import com.alertbot.mobile.ui.SignInScreen
import com.alertbot.mobile.ui.SplashScreen
import com.alertbot.mobile.ui.theme.AlertBotTheme

/**
 * The whole app is four destinations, so it navigates with a `when` rather
 * than a navigation library. Adding one would be more moving parts than the
 * product has screens.
 */
private sealed interface Route {
    data object Splash : Route
    data object SignIn : Route
    data object Setup : Route
    data object Alerts : Route
    data class Detail(val incidentId: Int) : Route
}

class MainActivity : ComponentActivity() {

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()

        val openIncidentId = intent?.getIntExtra(EXTRA_INCIDENT_ID, 0) ?: 0

        setContent {
            AlertBotTheme {
                AlertBotRoot(openIncidentId)
            }
        }
    }

    companion object {
        /** Set when a recovery notification is tapped, to open that alert. */
        const val EXTRA_INCIDENT_ID = "incident_id"
    }
}

@Composable
private fun AlertBotRoot(openIncidentId: Int) {
    val context = LocalContext.current

    // Where the splash hands off to. Recomputed on use rather than captured,
    // because signing in changes the answer.
    fun landing(): Route = when {
        !context.isSignedIn -> Route.SignIn
        !context.setupSeen -> Route.Setup
        openIncidentId > 0 -> Route.Detail(openIncidentId)
        else -> Route.Alerts
    }

    var route by remember {
        mutableStateOf(
            // Tapping a notification jumps straight to the alert. Someone
            // reaching for their phone at 3am should not be shown a logo
            // first — the splash is for a cold open, not for an emergency.
            if (openIncidentId > 0 && context.isSignedIn && context.setupSeen) {
                Route.Detail(openIncidentId)
            } else {
                Route.Splash
            }
        )
    }
    var warningRes by remember { mutableStateOf<Int?>(null) }

    BackHandler(enabled = route is Route.Detail) {
        route = Route.Alerts
    }

    when (val current = route) {
        is Route.Splash -> SplashScreen(onDone = { route = landing() })

        is Route.SignIn -> SignInScreen(
            onSignedIn = { warning ->
                warningRes = warning
                route = Route.Setup
            },
        )

        is Route.Setup -> AlarmSetupScreen(
            onContinue = {
                context.setupSeen = true
                route = Route.Alerts
            },
        )

        is Route.Alerts -> AlertsScreen(
            onOpenIncident = { id -> route = Route.Detail(id) },
            onOpenSetup = { route = Route.Setup },
            onSignedOut = { route = Route.SignIn },
        )

        is Route.Detail -> IncidentDetailScreen(
            incidentId = current.incidentId,
            onBack = { route = Route.Alerts },
        )
    }

    // The app is perfectly usable with pushes off — it just cannot wake anyone,
    // which is the one thing it exists to do. Say so rather than look healthy.
    warningRes?.let { message ->
        AlertDialog(
            onDismissRequest = { warningRes = null },
            text = { Text(stringResource(message)) },
            confirmButton = {
                TextButton(onClick = { warningRes = null }) { Text("OK") }
            },
        )
    }
}
