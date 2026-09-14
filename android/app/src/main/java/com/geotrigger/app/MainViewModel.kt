package com.geotrigger.app

import android.app.Application
import android.content.Intent
import androidx.core.content.ContextCompat
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import com.geotrigger.app.data.ApiFactory
import com.geotrigger.app.data.LoginRequest
import com.geotrigger.app.data.Session
import com.geotrigger.app.data.SessionStore
import com.geotrigger.app.data.Site
import com.geotrigger.app.data.SummaryRow
import com.geotrigger.app.location.TrackingService
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch
import retrofit2.HttpException

data class UiState(
    val ready: Boolean = false,
    val session: Session = Session(),
    val serverUrl: String = "",
    val username: String = "",
    val password: String = "",
    val busy: Boolean = false,
    val error: String? = null,
    val tracking: Boolean = false,
    val sites: List<Site> = emptyList(),
    val summary: List<SummaryRow> = emptyList(),
    val intervalSeconds: Int = 300,
)

class MainViewModel(application: Application) : AndroidViewModel(application) {
    private val store = SessionStore(application)
    private val _state = MutableStateFlow(UiState())
    val state: StateFlow<UiState> = _state.asStateFlow()

    init {
        viewModelScope.launch {
            store.session.collect { session ->
                _state.update {
                    it.copy(
                        ready = true,
                        session = session,
                        serverUrl = if (it.serverUrl.isBlank()) session.serverUrl else it.serverUrl,
                        username = if (it.username.isBlank()) session.username else it.username,
                    )
                }
                if (session.isSignedIn) {
                    refresh()
                }
            }
        }
    }

    fun setServerUrl(value: String) = _state.update { it.copy(serverUrl = value, error = null) }
    fun setUsername(value: String) = _state.update { it.copy(username = value, error = null) }
    fun setPassword(value: String) = _state.update { it.copy(password = value, error = null) }

    fun signIn() {
        val snapshot = _state.value
        if (snapshot.serverUrl.isBlank() || snapshot.username.isBlank() || snapshot.password.isBlank()) {
            _state.update { it.copy(error = "Server URL, username, and password are required.") }
            return
        }
        viewModelScope.launch {
            _state.update { it.copy(busy = true, error = null) }
            try {
                val api = ApiFactory.create(snapshot.serverUrl)
                val response = api.login(LoginRequest(snapshot.username.trim(), snapshot.password))
                store.save(snapshot.serverUrl, response.token, response.user.username)
                _state.update { it.copy(busy = false, password = "", intervalSeconds = response.ping_interval_seconds) }
            } catch (ex: HttpException) {
                val detail = ex.response()?.errorBody()?.string()
                _state.update { it.copy(busy = false, error = parseError(detail) ?: "Sign-in failed (${ex.code()}).") }
            } catch (ex: Exception) {
                _state.update { it.copy(busy = false, error = ex.message ?: "Could not reach the server.") }
            }
        }
    }

    fun signOut() {
        viewModelScope.launch {
            val session = store.current()
            runCatching {
                if (session.isSignedIn) {
                    ApiFactory.create(session.serverUrl, session.token).logout()
                }
            }
            getApplication<Application>().stopService(Intent(getApplication(), TrackingService::class.java))
            store.clear()
            _state.update { it.copy(tracking = false, sites = emptyList(), summary = emptyList(), error = null) }
        }
    }

    fun refresh() {
        viewModelScope.launch {
            val session = store.current()
            if (!session.isSignedIn) return@launch
            try {
                val api = ApiFactory.create(session.serverUrl, session.token)
                val config = api.config()
                val summary = api.summary()
                _state.update {
                    it.copy(
                        sites = config.locations,
                        summary = summary.locations,
                        intervalSeconds = config.ping_interval_seconds,
                        error = null,
                    )
                }
            } catch (ex: Exception) {
                _state.update { it.copy(error = ex.message ?: "Could not refresh.") }
            }
        }
    }

    fun startTracking() {
        val app = getApplication<Application>()
        ContextCompat.startForegroundService(app, Intent(app, TrackingService::class.java))
        _state.update { it.copy(tracking = true) }
    }

    fun stopTracking() {
        getApplication<Application>().stopService(Intent(getApplication(), TrackingService::class.java))
        _state.update { it.copy(tracking = false) }
    }

    private fun parseError(body: String?): String? {
        if (body.isNullOrBlank()) return null
        val marker = "\"error\":"
        val start = body.indexOf(marker)
        if (start < 0) return null
        val quote = body.indexOf('"', start + marker.length)
        val end = body.indexOf('"', quote + 1)
        if (quote < 0 || end < 0) return null
        return body.substring(quote + 1, end)
    }
}
