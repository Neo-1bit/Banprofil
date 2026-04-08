from __future__ import annotations

from banprofil.local_connector_search import LocalConnectorSearch
from banprofil.local_gap_repair import LocalGapRepair


def main() -> None:
    """
    Demonstrerar lokal connector-sökning för de korta gapen på referenssträckan.

    Returns
    -------
    None
        Skriver topprankade connector-kandidater till stdout.
    """
    repair = LocalGapRepair.from_config_file()
    search = LocalConnectorSearch.from_config_file()

    result = repair.analyze_reference_route(
        point1_easting=664502.0,
        point1_northing=7037403.0,
        point2_easting=643473.0,
        point2_northing=7031542.0,
        sequence_gap_m=500.0,
        max_bridgable_gap_m=1000.0,
    )

    for gap in result.bridgable_gaps:
        print(f"Gap {gap.from_sequence_index}->{gap.to_sequence_index} {gap.gap_m:.2f} m")
        candidates = search.find_candidates_for_gap(
            from_point=gap.from_point,
            to_point=gap.to_point,
            corridor_buffer_m=250.0,
            endpoint_radius_m=400.0,
            limit=10,
        )
        for candidate in candidates:
            print(
                "  kandidat",
                candidate.link_id,
                candidate.linksequence_oid,
                f"len {candidate.length_m:.2f} m",
                f"corr {candidate.distance_to_corridor_m:.2f} m",
                f"start {candidate.start_distance_m:.2f} m",
                f"end {candidate.end_distance_m:.2f} m",
            )


if __name__ == "__main__":
    main()
