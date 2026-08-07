package com.alertbot.mobile.ui.components

import android.text.format.DateUtils
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.IntrinsicSize
import androidx.compose.foundation.layout.fillMaxHeight
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import com.alertbot.mobile.R
import com.alertbot.mobile.data.Incident
import com.alertbot.mobile.data.SourceKind
import com.alertbot.mobile.ui.theme.BrandBlue
import com.alertbot.mobile.ui.theme.BrandGold
import com.alertbot.mobile.ui.theme.Critical
import com.alertbot.mobile.ui.theme.HairlineGrey
import com.alertbot.mobile.ui.theme.Resolved
import com.alertbot.mobile.ui.theme.TextSecondary

/** The AlertBot mark: white bell over a gold rule, on Esicia blue. */
@Composable
fun BrandMark(size: Int = 72, modifier: Modifier = Modifier) {
    Box(
        modifier = modifier
            .size(size.dp)
            .clip(RoundedCornerShape((size * 0.24f).dp))
            .background(BrandBlue),
        contentAlignment = Alignment.Center,
    ) {
        Icon(
            painter = painterResource(R.drawable.ic_brand_mark),
            contentDescription = null,
            tint = Color.Unspecified,
            modifier = Modifier.size((size * 0.82f).dp),
        )
    }
}

/** Which pipeline raised this — email, a watched WhatsApp chat, or a test. */
@Composable
fun SourceChip(incident: Incident) {
    // Resolved up front: stringResource is composable and cannot be called
    // from inside a plain lambda such as buildString.
    val emailLabel = stringResource(R.string.source_email)
    val whatsappLabel = stringResource(R.string.source_whatsapp)
    val testLabel = stringResource(R.string.source_test)
    val manualLabel = stringResource(R.string.source_manual)

    val (iconRes, label) = when (incident.sourceKind) {
        SourceKind.EMAIL -> R.drawable.ic_email to
            if (incident.provider.isNotBlank()) "$emailLabel · ${incident.provider}" else emailLabel
        SourceKind.WHATSAPP -> R.drawable.ic_chat to whatsappLabel
        SourceKind.TEST -> R.drawable.ic_science to testLabel
        SourceKind.MANUAL -> R.drawable.ic_science to manualLabel
        SourceKind.OTHER -> R.drawable.ic_error to incident.provider.ifBlank { "Alert" }
    }

    Row(
        verticalAlignment = Alignment.CenterVertically,
        modifier = Modifier
            .clip(RoundedCornerShape(8.dp))
            .background(MaterialTheme.colorScheme.surfaceVariant)
            .padding(horizontal = 10.dp, vertical = 6.dp),
    ) {
        Icon(
            painter = painterResource(iconRes),
            contentDescription = null,
            tint = TextSecondary,
            modifier = Modifier.size(16.dp),
        )
        Spacer(Modifier.width(6.dp))
        Text(
            text = label,
            style = MaterialTheme.typography.labelMedium,
            color = TextSecondary,
            maxLines = 1,
            overflow = TextOverflow.Ellipsis,
        )
    }
}

/**
 * One alert in the list. The left rule is the whole status language: red while
 * it still needs someone, calm green once it has been acknowledged.
 */
@Composable
fun IncidentCard(incident: Incident, onClick: () -> Unit) {
    Card(
        shape = RoundedCornerShape(14.dp),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
        elevation = CardDefaults.cardElevation(defaultElevation = 1.dp),
        modifier = Modifier
            .fillMaxWidth()
            .clickable(onClick = onClick),
    ) {
        Row(modifier = Modifier.height(IntrinsicSize.Min)) {
            Box(
                modifier = Modifier
                    .width(5.dp)
                    .fillMaxHeight()
                    .background(if (incident.acknowledged) Resolved else Critical),
            )

            Column(modifier = Modifier.padding(16.dp)) {
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Text(
                        text = incident.service,
                        style = MaterialTheme.typography.titleLarge,
                        color = MaterialTheme.colorScheme.onSurface,
                        maxLines = 2,
                        overflow = TextOverflow.Ellipsis,
                        modifier = Modifier.weight(1f),
                    )
                    Icon(
                        painter = painterResource(R.drawable.ic_chevron_right),
                        contentDescription = null,
                        tint = HairlineGrey,
                        modifier = Modifier.size(24.dp),
                    )
                }

                if (incident.reason.isNotBlank()) {
                    Spacer(Modifier.height(6.dp))
                    Text(
                        text = incident.reason,
                        style = MaterialTheme.typography.bodyMedium,
                        color = TextSecondary,
                        maxLines = 2,
                        overflow = TextOverflow.Ellipsis,
                    )
                }

                Spacer(Modifier.height(14.dp))
                Row(
                    verticalAlignment = Alignment.CenterVertically,
                    horizontalArrangement = Arrangement.SpaceBetween,
                    modifier = Modifier.fillMaxWidth(),
                ) {
                    SourceChip(incident)
                    Text(
                        text = relativeTime(incident.createdAt),
                        style = MaterialTheme.typography.labelMedium,
                        color = TextSecondary,
                    )
                }
            }
        }
    }
}

/** What almost everyone sees almost every day, so it is worth designing. */
@Composable
fun EmptyState() {
    Column(
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.Center,
        modifier = Modifier
            .fillMaxSize()
            .padding(horizontal = 40.dp),
    ) {
        Icon(
            painter = painterResource(R.drawable.ic_check_circle),
            contentDescription = null,
            tint = Resolved,
            modifier = Modifier.size(72.dp),
        )
        Spacer(Modifier.height(24.dp))
        Text(
            text = stringResource(R.string.alerts_empty_title),
            style = MaterialTheme.typography.headlineMedium,
            color = MaterialTheme.colorScheme.onSurface,
        )
        Spacer(Modifier.height(10.dp))
        Text(
            text = stringResource(R.string.alerts_empty_body),
            style = MaterialTheme.typography.bodyLarge,
            color = TextSecondary,
            textAlign = TextAlign.Center,
        )
        Spacer(Modifier.height(28.dp))
        Box(
            modifier = Modifier
                .width(48.dp)
                .height(4.dp)
                .clip(RoundedCornerShape(2.dp))
                .background(BrandGold),
        )
    }
}

/** "Just now", "8 minutes ago", "yesterday" — never a raw timestamp. */
fun relativeTime(epochMillis: Long): String {
    if (epochMillis <= 0L) return ""
    val elapsed = System.currentTimeMillis() - epochMillis
    if (elapsed < DateUtils.MINUTE_IN_MILLIS) return "Just now"
    return DateUtils.getRelativeTimeSpanString(
        epochMillis,
        System.currentTimeMillis(),
        DateUtils.MINUTE_IN_MILLIS,
    ).toString()
}
