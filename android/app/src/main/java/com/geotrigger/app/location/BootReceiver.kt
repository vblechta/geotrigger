package com.geotrigger.app.location

import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import androidx.core.content.ContextCompat
import com.geotrigger.app.data.SessionStore
import kotlinx.coroutines.runBlocking

class BootReceiver : BroadcastReceiver() {
    override fun onReceive(context: Context, intent: Intent?) {
        if (intent?.action != Intent.ACTION_BOOT_COMPLETED) return
        val session = runBlocking { SessionStore(context).current() }
        if (!session.isSignedIn) return
        ContextCompat.startForegroundService(context, Intent(context, TrackingService::class.java))
    }
}
