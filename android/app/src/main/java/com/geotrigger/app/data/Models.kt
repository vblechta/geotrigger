package com.geotrigger.app.data

import kotlinx.serialization.Serializable

@Serializable
data class LoginRequest(
    val username: String,
    val password: String,
)

@Serializable
data class LoginResponse(
    val token: String,
    val user: PublicUser,
    val ping_interval_seconds: Int,
)

@Serializable
data class PublicUser(
    val id: Int,
    val username: String,
    val is_admin: Boolean,
)

@Serializable
data class ConfigResponse(
    val ping_interval_seconds: Int,
    val locations: List<Site>,
)

@Serializable
data class Site(
    val id: Int,
    val name: String,
    val latitude: Double,
    val longitude: Double,
    val radius_meters: Int,
)

@Serializable
data class PresenceRequest(
    val latitude: Double,
    val longitude: Double,
    val accuracy_meters: Double? = null,
    val recorded_at: String? = null,
)

@Serializable
data class PresenceResponse(
    val matched_locations: List<Site> = emptyList(),
    val inside_location: Boolean = false,
    val ping_interval_seconds: Int = 300,
)

@Serializable
data class SummaryResponse(
    val ping_interval_seconds: Int = 300,
    val locations: List<SummaryRow> = emptyList(),
)

@Serializable
data class SummaryRow(
    val id: Int,
    val name: String,
    val seconds: Int,
    val visits: Int,
    val duration_label: String,
)

@Serializable
data class OkResponse(
    val ok: Boolean = true,
)

@Serializable
data class ErrorResponse(
    val error: String? = null,
)
