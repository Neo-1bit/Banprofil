package se.neo1bit.banprofil.data.model

/**
 * Basic train parameters used by the Android driver-support app.
 *
 * Attributes
 * ----------
 * maxSpeedKmh : Int
 *     Maximum allowed speed in kilometers per hour.
 * lengthM : Int
 *     Train length in meters.
 * weightTon : Int
 *     Train weight in metric tons.
 */
data class TrainProfile(
    val maxSpeedKmh: Int,
    val lengthM: Int,
    val weightTon: Int,
)
