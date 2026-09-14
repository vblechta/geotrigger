package com.geotrigger.app.ui.theme

import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.darkColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.Color

private val Olive = Color(0xFFC4D47A)
private val Background = Color(0xFF121410)
private val Surface = Color(0xFF1C1F18)
private val OnBg = Color(0xFFE6E1D3)
private val Error = Color(0xFFC45C4A)

private val Scheme = darkColorScheme(
    primary = Olive,
    onPrimary = Background,
    background = Background,
    onBackground = OnBg,
    surface = Surface,
    onSurface = OnBg,
    error = Error,
    onError = OnBg,
    secondary = Olive,
    onSecondary = Background,
)

@Composable
fun GeoTriggerTheme(content: @Composable () -> Unit) {
    MaterialTheme(colorScheme = Scheme, content = content)
}
