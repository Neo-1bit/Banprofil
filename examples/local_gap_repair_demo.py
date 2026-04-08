from __future__ import annotations

from banprofil.local_gap_repair import LocalGapRepair


def main() -> None:
    """
    Demonstrerar lokal gap-analys för referenssträckan.

    Returns
    -------
    None
        Skriver identifierade gap till stdout.
    """
    repair = LocalGapRepair.from_config_file()
    result = repair.analyze_reference_route(
        point1_easting=664502.0,
        point1_northing=7037403.0,
        point2_easting=643473.0,
        point2_northing=7031542.0,
        sequence_gap_m=500.0,
        max_bridgable_gap_m=1000.0,
    )

    print("Sekvenser", result.sequence_count)
    print("Alla gap")
    for gap in result.gaps:
        print(
            f"{gap.from_sequence_index}->{gap.to_sequence_index}",
            f"gap {gap.gap_m:.2f} m",
            gap.from_point,
            gap.to_point,
        )

    print("Lokalt brobara gap")
    for gap in result.bridgable_gaps:
        print(
            f"{gap.from_sequence_index}->{gap.to_sequence_index}",
            f"gap {gap.gap_m:.2f} m",
        )


if __name__ == "__main__":
    main()
