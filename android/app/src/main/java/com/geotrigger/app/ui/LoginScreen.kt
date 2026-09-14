package com.geotrigger.app.ui

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Button
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.unit.dp
import com.geotrigger.app.UiState

@Composable
fun LoginScreen(
    state: UiState,
    onServerUrl: (String) -> Unit,
    onUsername: (String) -> Unit,
    onPassword: (String) -> Unit,
    onSubmit: () -> Unit,
) {
    Column(
        modifier = Modifier
            .fillMaxSize()
            .verticalScroll(rememberScrollState())
            .padding(24.dp),
        verticalArrangement = Arrangement.spacedBy(16.dp),
    ) {
        Text("PRESENCE TIMEKEEPING", style = MaterialTheme.typography.labelMedium, color = MaterialTheme.colorScheme.primary)
        Text("GeoTrigger", style = MaterialTheme.typography.headlineLarge)
        Text(
            "Sign in with the public URL of your GeoTrigger server, plus the account created in the web app.",
            color = MaterialTheme.colorScheme.onBackground.copy(alpha = 0.7f),
        )
        OutlinedTextField(
            value = state.serverUrl,
            onValueChange = onServerUrl,
            label = { Text("Server URL") },
            placeholder = { Text("https://geotrigger.example.com") },
            singleLine = true,
            modifier = Modifier.fillMaxWidth(),
            keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Uri),
        )
        OutlinedTextField(
            value = state.username,
            onValueChange = onUsername,
            label = { Text("Username") },
            singleLine = true,
            modifier = Modifier.fillMaxWidth(),
        )
        OutlinedTextField(
            value = state.password,
            onValueChange = onPassword,
            label = { Text("Password") },
            singleLine = true,
            visualTransformation = PasswordVisualTransformation(),
            keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Password),
            modifier = Modifier.fillMaxWidth(),
        )
        state.error?.let { Text(it, color = MaterialTheme.colorScheme.error) }
        Button(onClick = onSubmit, enabled = !state.busy, modifier = Modifier.fillMaxWidth()) {
            Text(if (state.busy) "Signing in…" else "Sign in")
        }
    }
}
