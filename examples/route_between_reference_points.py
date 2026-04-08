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

    traversal = resolver.route_between_nodes(
        start_node_oid=start_match.node_oid,
        end_node_oid=end_match.node_oid,
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
    )
    print(output)


if __name__ == "__main__":
    main()
