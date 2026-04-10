package se.neo1bit.banprofil.data.model

/**
 * Route package exported from Banprofil and consumed by the Android app.
 *
 * Attributes
 * ----------
 * routeId : String
 *     Stable route identifier.
 * name : String
 *     Human-readable route name.
 * startLocation : String
 *     Start location name.
 * endLocation : String
 *     End location name.
 * totalLengthM : Double
 *     Total route length in meters.
 */
data class RouteDefinition(
    val routeId: String,
    val name: String,
    val startLocation: String,
    val endLocation: String,
    val totalLengthM: Double,
)
