package com.alertbot.mobile.ui

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.navigationBarsPadding
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBar
import androidx.compose.material3.TopAppBarDefaults
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
import com.alertbot.mobile.R
import com.alertbot.mobile.data.ApiClient
import com.alertbot.mobile.data.Incident
import com.alertbot.mobile.ui.components.SourceChip
import com.alertbot.mobile.ui.components.relativeTime
import com.alertbot.mobile.ui.theme.BrandBlue
import com.alertbot.mobile.ui.theme.Critical
import com.alertbot.mobile.ui.theme.HairlineGrey
import com.alertbot.mobile.ui.theme.Resolved
import com.alertbot.mobile.ui.theme.TextSecondary
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun IncidentDetailScreen(incidentId: Int, onBack: () -> Unit) {
    val context = LocalContext.current
    val scope = rememberCoroutineScope()

    var incident by remember { mutableStateOf<Incident?>(null) }
    var acknowledging by remember { mutableStateOf(false) }
    var ackFailed by remember { mutableStateOf(false) }

    LaunchedEffect(incidentId) {
        incident = withContext(Dispatchers.IO) { ApiClient.incident(context, incidentId) }
    }

    Scaffold(
        containerColor = MaterialTheme.colorScheme.background,
        topBar = {
            TopAppBar(
                title = { Text(stringResource(R.string.detail_title)) },
                navigationIcon = {
                    IconButton(onClick = onBack) {
                        Icon(
                            painter = painterResource(R.drawable.ic_arrow_back),
                            contentDescription = null,
                        )
                    }
                },
                colors = TopAppBarDefaults.topAppBarColors(
                    containerColor = BrandBlue,
                    titleContentColor = Color.White,
                    navigationIconContentColor = Color.White,
                ),
            )
        },
    ) { padding ->
        val current = incident

        if (current == null) {
            Box(Modifier.fillMaxSize().padding(padding))
            return@Scaffold
        }

        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(padding),
        ) {
            Column(
                modifier = Modifier
                    .weight(1f)
                    .verticalScroll(rememberScrollState())
                    .padding(horizontal = 20.dp, vertical = 24.dp),
            ) {
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Box(
                        modifier = Modifier
                            .size(12.dp)
                            .background(
                                color = if (current.acknowledged) Resolved else Critical,
                                shape = RoundedCornerShape(6.dp),
                            ),
                    )
                    Spacer(Modifier.width(10.dp))
                    Text(
                        text = if (current.acknowledged) {
                            stringResource(R.string.detail_state_acknowledged)
                        } else {
                            stringResource(R.string.detail_state_needs_attention)
                        },
                        style = MaterialTheme.typography.labelMedium,
                        color = if (current.acknowledged) Resolved else Critical,
                    )
                }

                Spacer(Modifier.height(12.dp))

                Text(
                    text = current.service,
                    style = MaterialTheme.typography.displaySmall,
                    color = MaterialTheme.colorScheme.onSurface,
                )

                if (current.reason.isNotBlank()) {
                    Spacer(Modifier.height(12.dp))
                    Text(
                        text = current.reason,
                        style = MaterialTheme.typography.bodyLarge,
                        color = TextSecondary,
                    )
                }

                Spacer(Modifier.height(24.dp))

                Card(
                    shape = RoundedCornerShape(14.dp),
                    colors = CardDefaults.cardColors(
                        containerColor = MaterialTheme.colorScheme.surface
                    ),
                    elevation = CardDefaults.cardElevation(defaultElevation = 1.dp),
                    modifier = Modifier.fillMaxWidth(),
                ) {
                    Column(modifier = Modifier.padding(4.dp)) {
                        DetailRow(stringResource(R.string.detail_started), showDivider = false) {
                            Text(
                                text = relativeTime(current.createdAt),
                                style = MaterialTheme.typography.bodyMedium,
                                color = MaterialTheme.colorScheme.onSurface,
                            )
                        }
                        DetailRow(stringResource(R.string.detail_source)) {
                            SourceChip(current)
                        }
                        if (current.severity.isNotBlank()) {
                            DetailRow(stringResource(R.string.detail_severity)) {
                                Text(
                                    text = current.severity,
                                    style = MaterialTheme.typography.bodyMedium,
                                    color = MaterialTheme.colorScheme.onSurface,
                                )
                            }
                        }
                        if (current.eventCount > 1) {
                            DetailRow(stringResource(R.string.detail_times_fired)) {
                                Text(
                                    text = "${current.eventCount}",
                                    style = MaterialTheme.typography.bodyMedium,
                                    color = MaterialTheme.colorScheme.onSurface,
                                )
                            }
                        }
                    }
                }
            }

            // Acknowledge stays pinned: it is the only thing this screen is for.
            Column(
                modifier = Modifier
                    .fillMaxWidth()
                    .background(MaterialTheme.colorScheme.surface)
                    .navigationBarsPadding()
                    .padding(20.dp),
            ) {
                if (current.acknowledged) {
                    Row(
                        horizontalArrangement = Arrangement.Center,
                        verticalAlignment = Alignment.CenterVertically,
                        modifier = Modifier.fillMaxWidth().height(56.dp),
                    ) {
                        Icon(
                            painter = painterResource(R.drawable.ic_check_circle),
                            contentDescription = null,
                            tint = Resolved,
                            modifier = Modifier.size(24.dp),
                        )
                        Spacer(Modifier.width(10.dp))
                        Text(
                            text = stringResource(
                                R.string.acknowledged_at,
                                clockTime(current.acknowledgedAt),
                            ),
                            style = MaterialTheme.typography.titleMedium,
                            color = MaterialTheme.colorScheme.onSurface,
                        )
                    }
                } else {
                    Button(
                        onClick = {
                            scope.launch {
                                acknowledging = true
                                ackFailed = false
                                val ok = withContext(Dispatchers.IO) {
                                    ApiClient.acknowledge(context, current.id)
                                }
                                if (ok) {
                                    incident = withContext(Dispatchers.IO) {
                                        ApiClient.incident(context, current.id)
                                    }
                                } else {
                                    ackFailed = true
                                }
                                acknowledging = false
                            }
                        },
                        enabled = !acknowledging && current.id > 0,
                        shape = RoundedCornerShape(12.dp),
                        colors = ButtonDefaults.buttonColors(containerColor = BrandBlue),
                        modifier = Modifier.fillMaxWidth().height(56.dp),
                    ) {
                        if (acknowledging) {
                            CircularProgressIndicator(
                                color = Color.White,
                                strokeWidth = 2.dp,
                                modifier = Modifier.size(20.dp),
                            )
                            Spacer(Modifier.width(12.dp))
                            Text(stringResource(R.string.acknowledging))
                        } else {
                            Text(
                                text = stringResource(R.string.acknowledge),
                                style = MaterialTheme.typography.labelLarge,
                            )
                        }
                    }

                    Spacer(Modifier.height(10.dp))
                    Text(
                        text = if (ackFailed) {
                            stringResource(R.string.ack_failed)
                        } else {
                            stringResource(R.string.ack_explainer)
                        },
                        style = MaterialTheme.typography.labelMedium,
                        color = if (ackFailed) Critical else TextSecondary,
                    )
                }
            }
        }
    }
}

@Composable
private fun DetailRow(
    label: String,
    showDivider: Boolean = true,
    value: @Composable () -> Unit,
) {
    // Drawn above the row, so the last row in a card never ends in a stray line.
    if (showDivider) {
        Box(
            modifier = Modifier
                .fillMaxWidth()
                .height(1.dp)
                .background(HairlineGrey),
        )
    }
    Row(
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.SpaceBetween,
        modifier = Modifier
            .fillMaxWidth()
            .padding(horizontal = 16.dp, vertical = 14.dp),
    ) {
        Text(
            text = label,
            style = MaterialTheme.typography.bodyMedium,
            color = TextSecondary,
        )
        Spacer(Modifier.width(16.dp))
        value()
    }
}

/** Local wall-clock time, for "Acknowledged at 14:03". */
private fun clockTime(epochMillis: Long): String {
    if (epochMillis <= 0L) return ""
    return SimpleDateFormat("HH:mm", Locale.getDefault()).format(Date(epochMillis))
}
