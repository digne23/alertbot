package com.alertbot.mobile.ui

import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.navigationBarsPadding
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.ModalBottomSheet
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.material3.TopAppBar
import androidx.compose.material3.TopAppBarDefaults
import androidx.compose.material3.pulltorefresh.PullToRefreshBox
import androidx.compose.material3.rememberModalBottomSheetState
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.unit.dp
import androidx.lifecycle.Lifecycle
import androidx.lifecycle.compose.LocalLifecycleOwner
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.lifecycle.repeatOnLifecycle
import com.alertbot.mobile.R
import com.alertbot.mobile.data.AlarmEvents
import com.alertbot.mobile.data.ApiClient
import com.alertbot.mobile.data.Incident
import com.alertbot.mobile.data.TEST_ALERT_TIMEOUT_MS
import com.alertbot.mobile.data.displayName
import com.alertbot.mobile.data.signOut
import com.alertbot.mobile.ui.components.EmptyState
import com.alertbot.mobile.ui.components.IncidentCard
import com.alertbot.mobile.ui.theme.BrandBlue
import com.alertbot.mobile.ui.theme.Critical
import com.alertbot.mobile.ui.theme.Resolved
import com.alertbot.mobile.ui.theme.TextSecondary
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext

private const val POLL_INTERVAL_MS = 30_000L

/** Outcome of "Send a test alert", shown in a dialog. */
private sealed interface TestState {
    data object Idle : TestState
    data object Confirming : TestState
    data object Sending : TestState
    data object Waiting : TestState
    data class Finished(val messageRes: Int) : TestState
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun AlertsScreen(
    onOpenIncident: (Int) -> Unit,
    onOpenSetup: () -> Unit,
    onSignedOut: () -> Unit,
) {
    val context = LocalContext.current
    val scope = rememberCoroutineScope()
    val lifecycleOwner = LocalLifecycleOwner.current

    var incidents by remember { mutableStateOf<List<Incident>>(emptyList()) }
    var loaded by remember { mutableStateOf(false) }
    var refreshing by remember { mutableStateOf(false) }
    var offline by remember { mutableStateOf(false) }
    var showAccount by remember { mutableStateOf(false) }
    var testState by remember { mutableStateOf<TestState>(TestState.Idle) }

    suspend fun load() {
        val result = withContext(Dispatchers.IO) { ApiClient.openIncidents(context) }
        if (result == null) {
            offline = true
        } else {
            offline = false
            incidents = result
        }
        loaded = true
    }

    // Poll only while the screen is actually in front of someone.
    LaunchedEffect(Unit) {
        lifecycleOwner.repeatOnLifecycle(Lifecycle.State.RESUMED) {
            while (true) {
                load()
                delay(POLL_INTERVAL_MS)
            }
        }
    }

    // A push landing means the list just went stale.
    val lastAlarmAt by AlarmEvents.lastAlarmAt.collectAsStateWithLifecycle()
    LaunchedEffect(lastAlarmAt) {
        if (lastAlarmAt > 0L) load()
    }

    Scaffold(
        containerColor = MaterialTheme.colorScheme.background,
        topBar = {
            TopAppBar(
                title = {
                    Column {
                        Text(
                            text = stringResource(R.string.alerts_title),
                            style = MaterialTheme.typography.titleLarge,
                        )
                        if (loaded && incidents.isNotEmpty()) {
                            Text(
                                text = if (incidents.size == 1) {
                                    stringResource(R.string.alerts_count_one)
                                } else {
                                    stringResource(R.string.alerts_count_other, incidents.size)
                                },
                                style = MaterialTheme.typography.labelMedium,
                                color = Color.White.copy(alpha = 0.85f),
                            )
                        }
                    }
                },
                actions = {
                    IconButton(onClick = { showAccount = true }) {
                        Icon(
                            painter = painterResource(R.drawable.ic_account),
                            contentDescription = stringResource(R.string.account_title),
                        )
                    }
                },
                colors = TopAppBarDefaults.topAppBarColors(
                    containerColor = BrandBlue,
                    titleContentColor = Color.White,
                    actionIconContentColor = Color.White,
                ),
            )
        },
    ) { padding ->
        PullToRefreshBox(
            isRefreshing = refreshing,
            onRefresh = {
                scope.launch {
                    refreshing = true
                    load()
                    refreshing = false
                }
            },
            modifier = Modifier
                .padding(padding)
                .fillMaxSize(),
        ) {
            when {
                !loaded -> Box(Modifier.fillMaxSize())

                // A LazyColumn even though there is nothing in it: the empty
                // state is the screen people see most days, and pull-to-refresh
                // needs a scrollable to hang off. fillParentMaxHeight keeps the
                // constraints bounded so EmptyState can still centre itself.
                incidents.isEmpty() -> LazyColumn(modifier = Modifier.fillMaxSize()) {
                    if (offline) item { OfflineBanner() }
                    item {
                        Box(Modifier.fillParentMaxHeight().fillMaxWidth()) {
                            EmptyState()
                        }
                    }
                }

                else -> LazyColumn(
                    contentPadding = PaddingValues(16.dp),
                    verticalArrangement = Arrangement.spacedBy(12.dp),
                    modifier = Modifier.fillMaxSize(),
                ) {
                    if (offline) item { OfflineBanner() }
                    items(incidents, key = { it.id }) { incident ->
                        IncidentCard(incident) { onOpenIncident(incident.id) }
                    }
                }
            }
        }
    }

    if (showAccount) {
        ModalBottomSheet(
            onDismissRequest = { showAccount = false },
            sheetState = rememberModalBottomSheetState(),
            containerColor = MaterialTheme.colorScheme.surface,
        ) {
            AccountSheet(
                signedInAs = context.displayName.ifBlank { "this phone" },
                onCheckSetup = {
                    showAccount = false
                    onOpenSetup()
                },
                onSendTest = {
                    showAccount = false
                    testState = TestState.Confirming
                },
                onSignOut = {
                    showAccount = false
                    context.signOut()
                    onSignedOut()
                },
            )
        }
    }

    TestAlertDialog(
        state = testState,
        onDismiss = { testState = TestState.Idle },
        onConfirm = {
            scope.launch {
                testState = TestState.Sending
                val baseline = AlarmEvents.lastAlarmAt.value
                val sent = withContext(Dispatchers.IO) { ApiClient.sendTestAlert(context) }
                if (!sent) {
                    testState = TestState.Finished(R.string.test_failed)
                    return@launch
                }

                // "The server accepted it" and "your phone rang" are different
                // claims. Only report the second one.
                testState = TestState.Waiting
                val deadline = System.currentTimeMillis() + TEST_ALERT_TIMEOUT_MS
                while (System.currentTimeMillis() < deadline &&
                    AlarmEvents.lastAlarmAt.value == baseline
                ) {
                    delay(500)
                }

                testState = if (AlarmEvents.lastAlarmAt.value != baseline) {
                    TestState.Finished(R.string.test_arrived)
                } else {
                    TestState.Finished(R.string.test_no_push)
                }
                load()
            }
        },
    )
}

@Composable
private fun OfflineBanner() {
    Row(
        verticalAlignment = Alignment.CenterVertically,
        modifier = Modifier
            .fillMaxWidth()
            .background(MaterialTheme.colorScheme.surfaceVariant)
            .padding(horizontal = 16.dp, vertical = 12.dp),
    ) {
        Icon(
            painter = painterResource(R.drawable.ic_error),
            contentDescription = null,
            tint = Critical,
            modifier = Modifier.size(20.dp),
        )
        Spacer(Modifier.width(10.dp))
        Text(
            text = stringResource(R.string.alerts_offline),
            style = MaterialTheme.typography.bodyMedium,
            color = TextSecondary,
        )
    }
}

@Composable
private fun AccountSheet(
    signedInAs: String,
    onCheckSetup: () -> Unit,
    onSendTest: () -> Unit,
    onSignOut: () -> Unit,
) {
    Column(
        modifier = Modifier
            .fillMaxWidth()
            .navigationBarsPadding()
            .padding(bottom = 16.dp),
    ) {
        Column(modifier = Modifier.padding(horizontal = 24.dp, vertical = 8.dp)) {
            Text(
                text = stringResource(R.string.account_signed_in, signedInAs),
                style = MaterialTheme.typography.titleMedium,
                color = MaterialTheme.colorScheme.onSurface,
            )
            Spacer(Modifier.height(4.dp))
            // Deliberately no server address here. Staff never see one, and a
            // URL on this sheet is the sort of thing that gets read out on a
            // support call and typed somewhere it should not be.
            Text(
                text = stringResource(R.string.account_subtitle),
                style = MaterialTheme.typography.labelMedium,
                color = TextSecondary,
            )
        }

        Spacer(Modifier.height(12.dp))

        SheetRow(R.drawable.ic_check_circle, R.string.account_check_setup, onCheckSetup)
        SheetRow(R.drawable.ic_science, R.string.account_test, onSendTest)
        SheetRow(R.drawable.ic_logout, R.string.account_sign_out, onSignOut)
    }
}

@Composable
private fun SheetRow(iconRes: Int, labelRes: Int, onClick: () -> Unit) {
    Row(
        verticalAlignment = Alignment.CenterVertically,
        modifier = Modifier
            .fillMaxWidth()
            .clickable(onClick = onClick)
            .padding(horizontal = 24.dp, vertical = 18.dp),
    ) {
        Icon(
            painter = painterResource(iconRes),
            contentDescription = null,
            tint = TextSecondary,
            modifier = Modifier.size(24.dp),
        )
        Spacer(Modifier.width(18.dp))
        Text(
            text = stringResource(labelRes),
            style = MaterialTheme.typography.bodyLarge,
            color = MaterialTheme.colorScheme.onSurface,
        )
    }
}

@Composable
private fun TestAlertDialog(
    state: TestState,
    onDismiss: () -> Unit,
    onConfirm: () -> Unit,
) {
    when (state) {
        is TestState.Idle -> Unit

        is TestState.Confirming -> AlertDialog(
            onDismissRequest = onDismiss,
            title = { Text(stringResource(R.string.test_confirm_title)) },
            text = { Text(stringResource(R.string.test_confirm_body)) },
            confirmButton = {
                TextButton(onClick = onConfirm) {
                    Text(stringResource(R.string.test_confirm_send), color = BrandBlue)
                }
            },
            dismissButton = {
                TextButton(onClick = onDismiss) {
                    Text(stringResource(R.string.test_cancel), color = TextSecondary)
                }
            },
        )

        is TestState.Sending, is TestState.Waiting -> AlertDialog(
            onDismissRequest = { },
            title = { Text(stringResource(R.string.test_confirm_title)) },
            text = {
                Text(
                    stringResource(
                        if (state is TestState.Sending) R.string.test_sending
                        else R.string.test_waiting
                    )
                )
            },
            confirmButton = { },
        )

        is TestState.Finished -> AlertDialog(
            onDismissRequest = onDismiss,
            icon = {
                Icon(
                    painter = painterResource(
                        if (state.messageRes == R.string.test_arrived) {
                            R.drawable.ic_check_circle
                        } else {
                            R.drawable.ic_error
                        }
                    ),
                    contentDescription = null,
                    tint = if (state.messageRes == R.string.test_arrived) Resolved else Critical,
                )
            },
            text = { Text(stringResource(state.messageRes)) },
            confirmButton = {
                TextButton(onClick = onDismiss) {
                    Text("OK", color = BrandBlue)
                }
            },
        )
    }
}
