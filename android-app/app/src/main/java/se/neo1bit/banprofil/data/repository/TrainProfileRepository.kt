package se.neo1bit.banprofil.data.repository

import se.neo1bit.banprofil.data.model.TrainProfile

/**
 * Repository contract for train profile persistence.
 */
interface TrainProfileRepository {
    /**
     * Save the active train profile.
     *
     * Parameters
     * ----------
     * profile : TrainProfile
     *     Train profile to persist.
     */
    fun saveActive(profile: TrainProfile)
}
