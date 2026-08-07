package com.alertbot.mobile.data

/**
 * The one value that changes between deployments.
 *
 * It is pre-filled on the sign-in screen so most staff never type a URL — they
 * enter a username and password and tap Sign in. It stays editable for testing
 * against another server.
 *
 * Change this line when AlertBot moves to its permanent home. The current value
 * is the Codespace URL from `.env` (`PUBLIC_URL`), which dies with the
 * Codespace — see the deployment note in CLAUDE.md.
 */
const val DEFAULT_SERVER_URL =
    "https://super-duper-halibut-wwwqxxpqj7jfvj97-8000.app.github.dev"

/** How long a snooze lasts before the alarm comes back. */
const val SNOOZE_MINUTES = 5L

/** How long the test-alert flow waits for the push to land before saying so. */
const val TEST_ALERT_TIMEOUT_MS = 15_000L
