package com.geotrigger.app

import android.Manifest
import android.content.pm.PackageManager
import android.os.Build
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.compose.setContent
import androidx.activity.result.contract.ActivityResultContracts
import androidx.activity.viewModels
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.ui.Modifier
import androidx.core.content.ContextCompat
import com.geotrigger.app.ui.HomeScreen
import com.geotrigger.app.ui.LoginScreen
import com.geotrigger.app.ui.theme.GeoTriggerTheme

class MainActivity : ComponentActivity() {
    private val viewModel: MainViewModel by viewModels()

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent {
            GeoTriggerTheme {
                val state by viewModel.state.collectAsState()
                val permissionLauncher = rememberLauncherForActivityResult(
                    ActivityResultContracts.RequestMultiplePermissions(),
                ) { granted ->
                    val fine = granted[Manifest.permission.ACCESS_FINE_LOCATION] == true
                    if (fine) {
                        maybeAskBackground()
                        viewModel.startTracking()
                    }
                }

                LaunchedEffect(state.session.isSignedIn) {
                    if (state.session.isSignedIn && hasFineLocation()) {
                        viewModel.startTracking()
                    }
                }

                Surface(
                    modifier = Modifier
                        .fillMaxSize()
                        .background(MaterialTheme.colorScheme.background),
                    color = MaterialTheme.colorScheme.background,
                ) {
                    if (!state.ready) return@Surface
                    if (!state.session.isSignedIn) {
                        LoginScreen(
                            state = state,
                            onServerUrl = viewModel::setServerUrl,
                            onUsername = viewModel::setUsername,
                            onPassword = viewModel::setPassword,
                            onSubmit = viewModel::signIn,
                        )
                    } else {
                        HomeScreen(
                            state = state,
                            onToggleTracking = {
                                if (state.tracking) {
                                    viewModel.stopTracking()
                                } else if (hasFineLocation()) {
                                    maybeAskBackground()
                                    viewModel.startTracking()
                                } else {
                                    permissionLauncher.launch(foregroundPermissions())
                                }
                            },
                            onRefresh = viewModel::refresh,
                            onSignOut = viewModel::signOut,
                        )
                    }
                }
            }
        }
    }

    private fun hasFineLocation(): Boolean {
        return ContextCompat.checkSelfPermission(this, Manifest.permission.ACCESS_FINE_LOCATION) ==
            PackageManager.PERMISSION_GRANTED
    }

    private fun foregroundPermissions(): Array<String> {
        val perms = mutableListOf(
            Manifest.permission.ACCESS_FINE_LOCATION,
            Manifest.permission.ACCESS_COARSE_LOCATION,
        )
        if (Build.VERSION.SDK_INT >= 33) {
            perms += Manifest.permission.POST_NOTIFICATIONS
        }
        return perms.toTypedArray()
    }

    private fun maybeAskBackground() {
        if (Build.VERSION.SDK_INT >= 29 &&
            ContextCompat.checkSelfPermission(this, Manifest.permission.ACCESS_BACKGROUND_LOCATION) !=
            PackageManager.PERMISSION_GRANTED
        ) {
            requestPermissions(arrayOf(Manifest.permission.ACCESS_BACKGROUND_LOCATION), 92)
        }
    }
}
