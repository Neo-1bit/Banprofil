from __future__ import annotations

from pathlib import Path

from banprofil.net_jvg_kml import export_traversal_kml
from banprofil.net_jvg_resolver import NetJvgResolver


def main() -> None:
    """
    Matchar två referenspunkter mot Net_JVG och exporterar rutten till KML.

    Returns
    -------
    None
        Skriver matchning och utdatafil till stdout.
    """
    resolver = NetJvgResolver.from_config_file()

    point1_easting = 664502.0
    point1_northing = 7037403.0
    point2_easting = 643473.0
    point2_northing = 7031542.0

    start_match = resolver.match_reference_point_to_node(
        easting=point1_easting,
        northing=point1_northing,
    )
    end_match = resolver.match_reference_point_to_node(
        easting=point2_easting,
        northing=point2_northing,
    )

    traversal = resolver.route_between_nodes_constrained(
        start_node_oid=start_match.node_oid,
        end_node_oid=end_match.node_oid,
        sequence_change_penalty=2500.0,
        direction_break_penalty=1200.0,
        corridor_width_m=3000.0,
        off_corridor_penalty_factor=4.0,
    )
    output = export_traversal_kml(
        resolver=resolver,
        traversal=traversal,
        output_path=Path("examples") / "reference_points_route.kml",
        name="Net_JVG Route Between Reference Points",
    )

    print(
        "Punkt1 -> nod",
        start_match.node_oid,
        f"distans {start_match.distance_m:.2f} m",
        f"({start_match.easting:.2f}, {start_match.northing:.2f})",
    )
    print(
        "Punkt2 -> nod",
        end_match.node_oid,
        f"distans {end_match.distance_m:.2f} m",
        f"({end_match.easting:.2f}, {end_match.northing:.2f})",
    )
    print(
        "Rutt",
        f"{traversal.visited_link_count} länkar",
        f"{traversal.accumulated_length_m:.2f} m",
        f"kostnad {traversal.total_cost:.2f}" if traversal.total_cost is not None else "",
    )
    print(output)


if __name__ == "__main__":
    main()
