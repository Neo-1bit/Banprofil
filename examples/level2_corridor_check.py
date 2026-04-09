from __future__ import annotations

from pathlib import Path
from xml.sax.saxutils import escape

from banprofil.gpkg_inspector import GeoPackageInspector
from banprofil.net_jvg_kml import sweref99tm_to_wgs84
from banprofil.net_jvg_resolver import NetJvgResolver


def _to_kml_coords(vertices: list[tuple[float, float]]) -> str:
    coords = []
    for x, y in vertices:
        lon, lat, alt = sweref99tm_to_wgs84(x, y, 0.0)
        coords.append(f"{lon},{lat},{alt}")
    return " ".join(coords)


def main() -> None:
    """
    Skapar level2 corridor check-KML för ett svårare referenspar.

    Returns
    -------
    None
        Skriver ut sökväg till skapad KML.
    """
    resolver = NetJvgResolver.from_config_file()
    inspector = GeoPackageInspector.from_config_file()

    point1 = (619730.0, 6919318.0)
    point2 = (623103.0, 6920698.0)
    buffer_m = 1500.0
    minx = min(point1[0], point2[0]) - buffer_m
    maxx = max(point1[0], point2[0]) + buffer_m
    miny = min(point1[1], point2[1]) - buffer_m
    maxy = max(point1[1], point2[1]) + buffer_m

    candidate_ids = set(
        inspector.rtree_window_query(
            table_name="Net_JVG_Link",
            minx=minx,
            maxx=maxx,
            miny=miny,
            maxy=maxy,
            limit=10000,
        )
    )

    start_match = resolver.match_reference_point_to_node(*point1)
    end_match = resolver.match_reference_point_to_node(*point2)
    traversal = resolver.route_between_nodes_constrained(start_match.node_oid, end_match.node_oid)
    traversal_ids = set(traversal.traversed_link_ids)

    rows = resolver.gpkg.fetch_rows(
        "Net_JVG_Link",
        limit=resolver.gpkg.count_rows("Net_JVG_Link"),
        columns=["id", "geom"],
    )

    placemarks: list[str] = []
    for row in rows:
        link_id = int(row["id"])
        if link_id not in candidate_ids:
            continue
        vertices = resolver._decode_link_vertices(row["geom"])
        if len(vertices) < 2:
            continue
        if link_id in traversal_ids:
            color = "ff0000ff"
            width = 5
            name = f"Level2 traversal link {link_id}"
        else:
            color = "b3ffffff"
            width = 2
            name = f"Level2 local candidate link {link_id}"
        placemarks.append(
            f"""
    <Placemark>
      <name>{escape(name)}</name>
      <Style>
        <LineStyle><color>{color}</color><width>{width}</width></LineStyle>
      </Style>
      <LineString>
        <tessellate>1</tessellate>
        <coordinates>{_to_kml_coords(vertices)}</coordinates>
      </LineString>
    </Placemark>"""
        )

    for label, point in (("Punkt1b", point1), ("Punkt2b", point2)):
        lon, lat, alt = sweref99tm_to_wgs84(point[0], point[1], 0.0)
        placemarks.append(
            f"""
    <Placemark>
      <name>{label}</name>
      <Style>
        <IconStyle>
          <color>ff00ffff</color>
          <scale>1.2</scale>
        </IconStyle>
      </Style>
      <Point><coordinates>{lon},{lat},{alt}</coordinates></Point>
    </Placemark>"""
        )

    content = f"""<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2">
  <Document>
    <name>Level2 Corridor Check</name>{''.join(placemarks)}
  </Document>
</kml>
"""
    output = Path("examples") / "level2_corridor_check.kml"
    output.write_text(content, encoding="utf-8")
    print(output)
    print(f"Punkt1b -> nod {start_match.node_oid} distans {start_match.distance_m:.2f} m")
    print(f"Punkt2b -> nod {end_match.node_oid} distans {end_match.distance_m:.2f} m")
    print(f"Traversal {traversal.visited_link_count} länkar {traversal.accumulated_length_m:.2f} m kostnad {traversal.total_cost:.2f}")


if __name__ == "__main__":
    main()
