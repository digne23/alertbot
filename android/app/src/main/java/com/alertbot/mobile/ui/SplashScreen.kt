package com.alertbot.mobile.ui

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.navigationBarsPadding
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.alertbot.mobile.R
import com.alertbot.mobile.ui.components.BrandMark
import com.alertbot.mobile.ui.theme.BrandBlue
import kotlinx.coroutines.delay

/** How long the mark is held before the app moves on. */
private const val SPLASH_MILLIS = 1600L

/**
 * The first thing anyone sees: the AlertBot mark on brand blue, with the
 * attribution line at the foot.
 *
 * It is a plain timed screen rather than the `core-splashscreen` library —
 * that API is built to cover the *cold-start window* and hands control back as
 * soon as the first frame is ready, which is far too quick to read a line of
 * text. It also cannot show anything below the icon, which is where the
 * attribution has to sit.
 *
 * [onDone] fires exactly once. It is deliberately not tied to any network
 * call: a phone on a dead connection must still reach the sign-in screen, so
 * nothing here can strand a user on a logo.
 */
@Composable
fun SplashScreen(onDone: () -> Unit) {
    LaunchedEffect(Unit) {
        delay(SPLASH_MILLIS)
        onDone()
    }

    Box(
        modifier = Modifier
            .fillMaxSize()
            .background(BrandBlue),
        contentAlignment = Alignment.Center,
    ) {
        Column(
            horizontalAlignment = Alignment.CenterHorizontally,
            verticalArrangement = Arrangement.Center,
        ) {
            BrandMark(size = 96)
            Spacer(Modifier.height(24.dp))
            Text(
                text = stringResource(R.string.app_name),
                style = MaterialTheme.typography.displaySmall,
                color = Color.White,
            )
            Spacer(Modifier.height(10.dp))
            Text(
                text = stringResource(R.string.splash_tagline),
                style = MaterialTheme.typography.bodyMedium,
                color = Color.White.copy(alpha = 0.75f),
                textAlign = TextAlign.Center,
            )
        }

        Text(
            text = stringResource(R.string.splash_powered_by),
            style = MaterialTheme.typography.labelLarge,
            color = Color.White.copy(alpha = 0.7f),
            letterSpacing = 1.sp,
            modifier = Modifier
                .align(Alignment.BottomCenter)
                .navigationBarsPadding()
                .padding(bottom = 40.dp),
        )
    }
}
