from __future__ import annotations

from banprofil.rail_graph import RailGraph


def main() -> None:
    """
    Demonstrerar grundläggande grafanalys för referenssträckan.

    Returns
    -------
    None
        Skriver nodmatchning, komponentstorlek och vägdata till stdout.
    """
    graph = RailGraph.from_config_file()

    point1_easting = 664502.0
    point1_northing = 7037403.0
    point2_easting = 643473.0
    point2_northing = 7031542.0

    start_node_oid, start_distance_m = graph.nearest_node(point1_easting, point1_northing)
    end_node_oid, end_distance_m = graph.nearest_node(point2_easting, point2_northing)
    print("Graf", graph.summary())
    print("Punkt1 -> nod", start_node_oid, f"distans {start_distance_m:.2f} m")
    print("Punkt2 -> nod", end_node_oid, f"distans {end_distance_m:.2f} m")
    print("Komponentstorlek punkt1", graph.connected_component_size(start_node_oid))
    print("Komponentstorlek punkt2", graph.connected_component_size(end_node_oid))

    try:
        path = graph.shortest_path(start_node_oid, end_node_oid)
    except Exception as exc:
        print("Ingen grafväg hittad", type(exc).__name__, str(exc))
        return

    print("Väg", f"{len(path.link_ids)} länkar", f"{path.total_length_m:.2f} m", f"kostnad {path.total_cost:.2f}")
    print("Länkar", path.link_ids)


if __name__ == "__main__":
    main()
