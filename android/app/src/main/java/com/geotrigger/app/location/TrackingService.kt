package com.geotrigger.app.location

import android.Manifest
import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.content.Intent
import android.content.pm.PackageManager
import android.content.pm.ServiceInfo
import android.os.Build
import androidx.core.app.NotificationCompat
import androidx.core.content.ContextCompat
import androidx.lifecycle.LifecycleService
import androidx.lifecycle.lifecycleScope
import com.geotrigger.app.MainActivity
import com.geotrigger.app.R
import com.geotrigger.app.data.ApiFactory
import com.geotrigger.app.data.PresenceRequest
import com.geotrigger.app.data.SessionStore
import com.google.android.gms.location.LocationServices
import com.google.android.gms.location.Priority
import java.time.Instant
import kotlin.coroutines.coroutineContext
import kotlinx.coroutines.Job
import kotlinx.coroutines.delay
import kotlinx.coroutines.isActive
import kotlinx.coroutines.launch
import kotlinx.coroutines.tasks.await

class TrackingService : LifecycleService() {
    private val store by lazy { SessionStore(applicationContext) }
    private val fused by lazy { LocationServices.getFusedLocationProviderClient(this) }
    private var loop: Job? = null

    override fun onCreate() {
        super.onCreate()
        createChannel()
        startForegroundNotification("Waiting for a defined site…")
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        super.onStartCommand(intent, flags, startId)
        if (loop?.isActive != true) {
            loop = lifecycleScope.launch { runLoop() }
        }
        return START_STICKY
    }

    private suspend fun runLoop() {
        var intervalSeconds = 300
        while (coroutineContext.isActive) {
            val session = store.current()
            if (!session.isSignedIn) {
                stopSelf()
                return
            }
            if (!hasLocationPermission()) {
                updateNotification("Location permission missing")
                delay(15_000)
                continue
            }

            try {
                val api = ApiFactory.create(session.serverUrl, session.token)
                val config = api.config()
                intervalSeconds = config.ping_interval_seconds.coerceIn(30, 3600)
                val location = fused.getCurrentLocation(Priority.PRIORITY_BALANCED_POWER_ACCURACY, null).await()
                    ?: fused.lastLocation.await()
                if (location == null) {
                    updateNotification("No GPS fix yet")
                } else {
                    val matched = sitesContaining(location.latitude, location.longitude, config.locations)
                    if (matched.isEmpty()) {
                        updateNotification("Outside every site")
                    } else {
                        val response = api.presence(
                            PresenceRequest(
                                latitude = location.latitude,
                                longitude = location.longitude,
                                accuracy_meters = location.accuracy.toDouble(),
                                recorded_at = Instant.now().toString(),
                            ),
                        )
                        intervalSeconds = response.ping_interval_seconds.coerceIn(30, 3600)
                        val names = response.matched_locations.joinToString { it.name }
                        updateNotification(if (response.inside_location) "On site: $names" else "Outside every site")
                    }
                }
            } catch (ex: Exception) {
                updateNotification(ex.message ?: "Network error")
            }
            delay(intervalSeconds * 1000L)
        }
    }

    private fun hasLocationPermission(): Boolean {
        return ContextCompat.checkSelfPermission(this, Manifest.permission.ACCESS_FINE_LOCATION) ==
            PackageManager.PERMISSION_GRANTED
    }

    private fun createChannel() {
        val manager = getSystemService(NotificationManager::class.java)
        manager.createNotificationChannel(
            NotificationChannel(
                CHANNEL_ID,
                getString(R.string.notification_channel),
                NotificationManager.IMPORTANCE_LOW,
            ),
        )
    }

    private fun startForegroundNotification(text: String) {
        if (Build.VERSION.SDK_INT >= 34) {
            startForeground(NOTIFICATION_ID, notification(text), ServiceInfo.FOREGROUND_SERVICE_TYPE_LOCATION)
        } else {
            startForeground(NOTIFICATION_ID, notification(text))
        }
    }

    private fun updateNotification(text: String) {
        getSystemService(NotificationManager::class.java).notify(NOTIFICATION_ID, notification(text))
    }

    private fun notification(text: String): Notification {
        val launch = PendingIntent.getActivity(
            this,
            0,
            Intent(this, MainActivity::class.java),
            PendingIntent.FLAG_IMMUTABLE or PendingIntent.FLAG_UPDATE_CURRENT,
        )
        return NotificationCompat.Builder(this, CHANNEL_ID)
            .setSmallIcon(R.drawable.ic_notification)
            .setContentTitle(getString(R.string.notification_title))
            .setContentText(text)
            .setOngoing(true)
            .setContentIntent(launch)
            .build()
    }

    companion object {
        const val CHANNEL_ID = "geotrigger-presence"
        const val NOTIFICATION_ID = 17
    }
}
