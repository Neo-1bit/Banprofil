package se.neo1bit.banprofil.domain.positioning

/**
 * Placeholder contract for route-constrained positioning logic.
 */
interface PositioningEngine {
    /**
     * Start position tracking.
     */
    fun start()

    /**
     * Stop position tracking.
     */
    fun stop()
}
