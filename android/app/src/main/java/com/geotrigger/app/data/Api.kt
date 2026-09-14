package com.geotrigger.app.data

import com.jakewharton.retrofit2.converter.kotlinx.serialization.asConverterFactory
import kotlinx.serialization.json.Json
import okhttp3.Interceptor
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import retrofit2.Retrofit
import retrofit2.http.Body
import retrofit2.http.GET
import retrofit2.http.POST
import java.util.concurrent.TimeUnit

interface GeoTriggerApi {
    @POST("api/auth/login")
    suspend fun login(@Body body: LoginRequest): LoginResponse

    @POST("api/auth/logout")
    suspend fun logout(): OkResponse

    @GET("api/config")
    suspend fun config(): ConfigResponse

    @POST("api/presence")
    suspend fun presence(@Body body: PresenceRequest): PresenceResponse

    @GET("api/summary")
    suspend fun summary(): SummaryResponse
}

object ApiFactory {
    private val json = Json {
        ignoreUnknownKeys = true
        isLenient = true
    }

    fun create(baseUrl: String, token: String? = null): GeoTriggerApi {
        val client = OkHttpClient.Builder()
            .connectTimeout(20, TimeUnit.SECONDS)
            .readTimeout(20, TimeUnit.SECONDS)
            .addInterceptor(Interceptor { chain ->
                val original = chain.request()
                val builder = original.newBuilder()
                    .header("Accept", "application/json")
                    .header("Content-Type", "application/json")
                if (!token.isNullOrBlank()) {
                    builder.header("Authorization", "Bearer $token")
                }
                chain.proceed(builder.build())
            })
            .build()

        return Retrofit.Builder()
            .baseUrl(normalizeBaseUrl(baseUrl))
            .client(client)
            .addConverterFactory(json.asConverterFactory("application/json".toMediaType()))
            .build()
            .create(GeoTriggerApi::class.java)
    }
}

suspend fun apiErrorMessage(errorBody: String?): String {
    if (errorBody.isNullOrBlank()) return "Request failed."
    return runCatching { Json { ignoreUnknownKeys = true }.decodeFromString<ErrorResponse>(errorBody).error }
        .getOrNull()
        ?: errorBody
}
