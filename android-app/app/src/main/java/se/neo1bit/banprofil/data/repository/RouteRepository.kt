package se.neo1bit.banprofil.data.repository

import se.neo1bit.banprofil.data.model.RouteDefinition

/**
 * Repository contract for route packages available to the Android app.
 */
interface RouteRepository {
    /**
     * Return all locally available routes.
     *
     * Returns
     * -------
     * list of RouteDefinition
     *     Available route definitions.
     */
    fun listRoutes(): List<RouteDefinition>
}
