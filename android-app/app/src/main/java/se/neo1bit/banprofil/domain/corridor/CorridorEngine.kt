package se.neo1bit.banprofil.domain.corridor

/**
 * Placeholder contract for extracting a lookahead corridor from the active route.
 */
interface CorridorEngine {
    /**
     * Refresh the active corridor slice.
     */
    fun refresh()
}
