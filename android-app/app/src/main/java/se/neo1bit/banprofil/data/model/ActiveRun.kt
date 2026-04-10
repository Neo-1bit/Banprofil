package se.neo1bit.banprofil.data.model

/**
 * Active run state for the current driving session.
 *
 * Attributes
 * ----------
 * routeId : String
 *     Identifier for the active route.
 * currentProgressM : Double
 *     Estimated current progress along the selected route.
 * selectedLookaheadM : Int
 *     Active lookahead window in meters.
 * positionConfidence : String
 *     Coarse position confidence label.
 */
data class ActiveRun(
    val routeId: String,
    val currentProgressM: Double,
    val selectedLookaheadM: Int,
    val positionConfidence: String,
)
