package com.alertbot.mobile.data

/**
 * The one value that changes between deployments.
 *
 * This is the single source of truth for where the server lives, and it is
 * **never shown to the user**. Staff sign in with a name and a PIN; they are
 * not expected to know what a server address is, and a wrong one is a support
 * call nobody needs at 3am.
 *
 * Change this line when AlertBot moves to its permanent home. The current value
 * is the Codespace URL from `.env` (`PUBLIC_URL`), which dies with the
 * Codespace — and because it is compiled into the APK, every installed phone
 * needs a new build when that happens. See the deployment note in CLAUDE.md.
 */
const val DEFAULT_SERVER_URL =
    "https://super-duper-halibut-wwwqxxpqj7jfvj97-8000.app.github.dev"

/** How long a snooze lasts before the alarm comes back. */
const val SNOOZE_MINUTES = 5L

/** How long the test-alert flow waits for the push to land before saying so. */
const val TEST_ALERT_TIMEOUT_MS = 15_000L
