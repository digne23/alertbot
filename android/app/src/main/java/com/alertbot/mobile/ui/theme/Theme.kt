package com.alertbot.mobile.ui.theme

import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable

/**
 * Light only, on purpose.
 *
 * A single high-contrast scheme is easier to trust and easier to maintain than
 * two, and dark mode would fight the brand blue. The alarm screen is the one
 * place that departs from this, and it does so deliberately.
 *
 * Dynamic colour is off: the whole point is that this looks like Esicia on
 * every phone, not like each user's wallpaper.
 */
private val AlertBotColors = lightColorScheme(
    primary = BrandBlue,
    onPrimary = CardSurface,
    primaryContainer = BrandBlueTint,
    onPrimaryContainer = BrandBlueDark,

    secondary = BrandGold,
    onSecondary = TextPrimary,

    error = Critical,
    onError = CardSurface,

    background = PageSurface,
    onBackground = TextPrimary,
    surface = CardSurface,
    onSurface = TextPrimary,
    surfaceVariant = PageSurface,
    onSurfaceVariant = TextSecondary,
    outline = HairlineGrey,
    outlineVariant = HairlineGrey,
)

@Composable
fun AlertBotTheme(content: @Composable () -> Unit) {
    MaterialTheme(
        colorScheme = AlertBotColors,
        typography = AlertBotTypography,
        content = content,
    )
}
