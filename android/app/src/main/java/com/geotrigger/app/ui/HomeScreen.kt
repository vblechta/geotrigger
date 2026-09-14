package com.geotrigger.app.ui

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Button
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import com.geotrigger.app.UiState

@Composable
fun HomeScreen(
    state: UiState,
    onToggleTracking: () -> Unit,
    onRefresh: () -> Unit,
    onSignOut: () -> Unit,
) {
    Column(
        modifier = Modifier
            .fillMaxSize()
            .verticalScroll(rememberScrollState())
            .padding(24.dp),
        verticalArrangement = Arrangement.spacedBy(16.dp),
    ) {
        Text("FIELD CLIENT", style = MaterialTheme.typography.labelMedium, color = MaterialTheme.colorScheme.primary)
        Text("Hello, ${state.session.username}", style = MaterialTheme.typography.headlineMedium)
        Text(state.session.serverUrl.trimEnd('/'), color = MaterialTheme.colorScheme.onBackground.copy(alpha = 0.7f))
        Text("Heartbeat every ${state.intervalSeconds}s while you are inside a site radius.")

        Row(horizontalArrangement = Arrangement.spacedBy(12.dp), modifier = Modifier.fillMaxWidth()) {
            Button(onClick = onToggleTracking, modifier = Modifier.weight(1f)) {
                Text(if (state.tracking) "Stop tracking" else "Start tracking")
            }
            OutlinedButton(onClick = onRefresh) { Text("Refresh") }
        }
        state.error?.let { Text(it, color = MaterialTheme.colorScheme.error) }

        Text("SITES", style = MaterialTheme.typography.labelMedium, color = MaterialTheme.colorScheme.primary)
        if (state.sites.isEmpty()) {
            Text("No locations defined yet. An administrator adds them in the web app.")
        } else {
            state.sites.forEach { site ->
                Text("${site.name}  ·  ${site.radius_meters} m")
            }
        }

        Text("MY TIME", style = MaterialTheme.typography.labelMedium, color = MaterialTheme.colorScheme.primary)
        if (state.summary.isEmpty()) {
            Text("No time recorded yet. Start tracking and stay inside a site.")
        } else {
            state.summary.forEach { row ->
                Text("${row.name}  ·  ${row.duration_label}  ·  ${row.visits} visit(s)")
            }
        }

        TextButton(onClick = onSignOut) { Text("Sign out") }
    }
}
