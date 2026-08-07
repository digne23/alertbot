package com.alertbot.mobile.ui.theme

import androidx.compose.ui.graphics.Color

/**
 * Esicia's brand palette.
 *
 * These are the real values, read out of esicia.rw's own assets rather than
 * matched by eye:
 *
 *  - [BrandBlue] `#0F5C92` — the stroke on the accent rule in
 *    `images/esicia-logo-compressor.svg`, and the section background used
 *    throughout `css/style.css`.
 *  - [BrandGold] `#CCAE3A` — the most-used colour in `css/style.css`, always
 *    sitting on top of the blue.
 *
 * [Critical] and [Resolved] also appear in that stylesheet but are incidental
 * rather than brand colours; they are used only for state, never for chrome.
 *
 * Mirrored in `res/values/colors.xml` for the bits Android needs in XML.
 */
val BrandBlue = Color(0xFF0F5C92)
val BrandBlueDark = Color(0xFF0B4670)
val BrandBlueTint = Color(0xFFE7EFF5)

val BrandGold = Color(0xFFCCAE3A)
val BrandGoldDark = Color(0xFFC6A838)

val Critical = Color(0xFFF45E58)
val CriticalDeep = Color(0xFF8E1F1B)
val Resolved = Color(0xFF33D685)

val PageSurface = Color(0xFFF7F7F7)
val CardSurface = Color(0xFFFFFFFF)
val TextPrimary = Color(0xFF333333)
val TextSecondary = Color(0xFF666666)
val HairlineGrey = Color(0xFFE2E5E9)
