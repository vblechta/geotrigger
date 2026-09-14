package com.geotrigger.app.data

import android.content.Context
import androidx.datastore.preferences.core.edit
import androidx.datastore.preferences.core.stringPreferencesKey
import androidx.datastore.preferences.preferencesDataStore
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.flow.map

private val Context.dataStore by preferencesDataStore("geotrigger_session")

data class Session(
    val serverUrl: String = "",
    val token: String = "",
    val username: String = "",
) {
    val isSignedIn: Boolean get() = token.isNotBlank() && serverUrl.isNotBlank()
}

class SessionStore(private val context: Context) {
    private val serverKey = stringPreferencesKey("server_url")
    private val tokenKey = stringPreferencesKey("token")
    private val usernameKey = stringPreferencesKey("username")

    val session: Flow<Session> = context.dataStore.data.map { prefs ->
        Session(
            serverUrl = prefs[serverKey].orEmpty(),
            token = prefs[tokenKey].orEmpty(),
            username = prefs[usernameKey].orEmpty(),
        )
    }

    suspend fun current(): Session = session.first()

    suspend fun save(serverUrl: String, token: String, username: String) {
        context.dataStore.edit { prefs ->
            prefs[serverKey] = normalizeBaseUrl(serverUrl)
            prefs[tokenKey] = token
            prefs[usernameKey] = username
        }
    }

    suspend fun clear() {
        context.dataStore.edit { it.clear() }
    }
}

fun normalizeBaseUrl(raw: String): String {
    var url = raw.trim().trimEnd('/')
    if (url.isNotEmpty() && !url.startsWith("http://") && !url.startsWith("https://")) {
        url = "https://$url"
    }
    return if (url.endsWith("/")) url else "$url/"
}
