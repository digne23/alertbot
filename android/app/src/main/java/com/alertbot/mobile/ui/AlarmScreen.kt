package com.alertbot.mobile.ui

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
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
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.alertbot.mobile.R
import com.alertbot.mobile.ui.components.BrandMark
import com.alertbot.mobile.ui.theme.BrandGold
import com.alertbot.mobile.ui.theme.CriticalDeep
import com.alertbot.mobile.ui.theme.TextPrimary

/**
 * What someone sees at 3am, usually before they are properly awake.
 *
 * Deliberately the one screen that departs from the calm light theme: deep red,
 * no chrome, nothing to read but the name of what broke and two enormous
 * buttons. Acknowledge is gold so it is unmistakably the thing to press.
 */
@Composable
fun AlarmScreen(
    service: String,
    reason: String,
    incidentId: Int,
    acknowledging: Boolean,
    ackFailed: Boolean,
    onAcknowledge: () -> Unit,
    onSnooze: () -> Unit,
) {
    Column(
        horizontalAlignment = Alignment.CenterHorizontally,
        modifier = Modifier
            .fillMaxSize()
            .background(CriticalDeep)
            .statusBarsPadding()
            .navigationBarsPadding()
            .padding(horizontal = 24.dp),
    ) {
        Spacer(Modifier.height(32.dp))
        BrandMark(size = 48)

        Column(
            horizontalAlignment = Alignment.CenterHorizontally,
            verticalArrangement = Arrangement.Center,
            modifier = Modifier
                .weight(1f)
                .fillMaxWidth()
                .verticalScroll(rememberScrollState()),
        ) {
            Text(
                text = stringResource(R.string.alarm_heading).uppercase(),
                color = Color.White.copy(alpha = 0.7f),
                fontSize = 15.sp,
                fontWeight = FontWeight.SemiBold,
                letterSpacing = 2.sp,
            )

            Spacer(Modifier.height(20.dp))

            Text(
                text = service,
                color = Color.White,
                fontSize = 40.sp,
                lineHeight = 46.sp,
                fontWeight = FontWeight.Bold,
                textAlign = TextAlign.Center,
            )

            if (reason.isNotBlank()) {
                Spacer(Modifier.height(18.dp))
                Text(
                    text = reason,
                    color = Color.White.copy(alpha = 0.88f),
                    fontSize = 19.sp,
                    lineHeight = 27.sp,
                    textAlign = TextAlign.Center,
                )
            }

            if (incidentId > 0) {
                Spacer(Modifier.height(20.dp))
                Text(
                    text = stringResource(R.string.alarm_incident_number, incidentId),
                    color = Color.White.copy(alpha = 0.55f),
                    fontSize = 14.sp,
                )
            }
        }

        Button(
            onClick = onAcknowledge,
            enabled = !acknowledging,
            shape = RoundedCornerShape(14.dp),
            colors = ButtonDefaults.buttonColors(
                containerColor = BrandGold,
                contentColor = TextPrimary,
            ),
            modifier = Modifier
                .fillMaxWidth()
                .height(72.dp),
        ) {
            if (acknowledging) {
                CircularProgressIndicator(
                    color = TextPrimary,
                    strokeWidth = 2.dp,
                    modifier = Modifier.size(22.dp),
                )
                Spacer(Modifier.width(12.dp))
                Text(stringResource(R.string.acknowledging), fontSize = 20.sp)
            } else {
                Text(
                    text = stringResource(
                        if (ackFailed) R.string.ack_failed else R.string.acknowledge
                    ),
                    fontSize = 21.sp,
                    fontWeight = FontWeight.Bold,
                )
            }
        }

        Spacer(Modifier.height(14.dp))

        OutlinedButton(
            onClick = onSnooze,
            shape = RoundedCornerShape(14.dp),
            colors = ButtonDefaults.outlinedButtonColors(contentColor = Color.White),
            modifier = Modifier
                .fillMaxWidth()
                .height(60.dp),
        ) {
            Text(
                text = stringResource(R.string.alarm_snooze),
                fontSize = 18.sp,
                fontWeight = FontWeight.Medium,
            )
        }

        Spacer(Modifier.height(14.dp))

        Text(
            text = stringResource(R.string.ack_explainer),
            color = Color.White.copy(alpha = 0.6f),
            fontSize = 13.sp,
            lineHeight = 18.sp,
            textAlign = TextAlign.Center,
            modifier = Modifier.padding(bottom = 20.dp),
        )
    }
}
