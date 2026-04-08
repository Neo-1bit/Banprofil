from __future__ import annotations

from banprofil.net_jvg_resolver import NetJvgResolver
from banprofil.net_jvg_kml import _load_traversal_link_geometries, _sequence_traversal_vertices


def main() -> None:
    """
    Probar lokala gap mellan sekvenser i referensrutten.

    Returns
    -------
    None
        Skriver gapmätningar till stdout.
    """
    resolver = NetJvgResolver.from_config_file()
    point1 = resolver.match_reference_point_to_node(664502.0, 7037403.0)
    point2 = resolver.match_reference_point_to_node(643473.0, 7031542.0)
    traversal = resolver.route_between_nodes_constrained(point1.node_oid, point2.node_oid)
    geoms = _load_traversal_link_geometries(resolver, traversal)
    sequences = _sequence_traversal_vertices(geoms, max_gap_m=500.0)

    print("Antal sekvenser", len(sequences))
    for index in range(len(sequences) - 1):
        current_end = sequences[index][-1]
        next_start = sequences[index + 1][0]
        gap = ((current_end[0] - next_start[0]) ** 2 + (current_end[1] - next_start[1]) ** 2) ** 0.5
        print(index + 1, "->", index + 2, f"gap {gap:.2f} m", current_end, next_start)


if __name__ == "__main__":
    main()
