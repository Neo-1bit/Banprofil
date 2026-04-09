from __future__ import annotations

from pathlib import Path
from xml.sax.saxutils import escape

from banprofil.gpkg_inspector import GeoPackageInspector
from banprofil.geopackage_geometry import line_vertices_xy, point_xy
from banprofil.net_jvg_kml import sweref99tm_to_wgs84
from banprofil.net_jvg_resolver import NetJvgResolver


def _to_kml_coords(vertices: list[tuple[float, float]]) -> str:
    coords: list[str] = []
    for x, y in vertices:
        lon, lat, alt = sweref99tm_to_wgs84(x, y, 0.0)
        coords.append(f"{lon},{lat},{alt}")
    return " ".join(coords)


def _point_to_kml_coord(point: tuple[float, float]) -> str:
    lon, lat, alt = sweref99tm_to_wgs84(point[0], point[1], 0.0)
    return f"{lon},{lat},{alt}"


def _write_kml(path: Path, name: str, placemarks: list[str]) -> None:
    content = f"""<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2">
  <Document>
    <name>{escape(name)}</name>{''.join(placemarks)}
  </Document>
</kml>
"""
    path.write_text(content, encoding="utf-8")


def main() -> None:
    """
    Exporterar level2-bakgrundslager till separata KML-filer.

    Returns
    -------
    None
        Skriver ut skapade filer.
    """
    resolver = NetJvgResolver.from_config_file()
    inspector = GeoPackageInspector.from_config_file()

    point1 = (619730.0, 6919318.0)
    point2 = (623103.0, 6920698.0)
    buffer_m = 2500.0
    minx = min(point1[0], point2[0]) - buffer_m
    maxx = max(point1[0], point2[0]) + buffer_m
    miny = min(point1[1], point2[1]) - buffer_m
    maxy = max(point1[1], point2[1]) + buffer_m

    output_dir = Path("examples") / "level2_network_layers"
    output_dir.mkdir(parents=True, exist_ok=True)

    layer_specs = [
        ("Net_JVG_Link", "ffbfbfbf", 2),
        ("Net_JVG_LinkSequence", "ff00ffff", 3),
        ("Net_JVG_Node", "ff00ff00", 1),
    ]

    for table_name, color, width in layer_specs:
        candidate_ids = set(
            inspector.rtree_window_query(
                table_name=table_name,
                minx=minx,
                maxx=maxx,
                miny=miny,
                maxy=maxy,
                limit=20000,
            )
        )
        rows = resolver.gpkg.fetch_rows(
            table_name,
            limit=resolver.gpkg.count_rows(table_name),
            columns=["id", "geom"],
        )
        placemarks: list[str] = []
        for row in rows:
            row_id = int(row["id"])
            if row_id not in candidate_ids:
                continue
            geom = row["geom"]
            if table_name == "Net_JVG_Node":
                point = point_xy(geom)
                if point is None:
                    continue
                placemarks.append(
                    f"""
    <Placemark>
      <name>{escape(f'{table_name} {row_id}')}</name>
      <Style>
        <IconStyle><color>{color}</color><scale>{width}</scale></IconStyle>
      </Style>
      <Point><coordinates>{_point_to_kml_coord(point)}</coordinates></Point>
    </Placemark>"""
                )
            else:
                vertices = line_vertices_xy(geom)
                if len(vertices) < 2:
                    continue
                placemarks.append(
                    f"""
    <Placemark>
      <name>{escape(f'{table_name} {row_id}')}</name>
      <Style>
        <LineStyle><color>{color}</color><width>{width}</width></LineStyle>
      </Style>
      <LineString>
        <tessellate>1</tessellate>
        <coordinates>{_to_kml_coords(vertices)}</coordinates>
      </LineString>
    </Placemark>"""
                )

        output_path = output_dir / f"{table_name}.kml"
        _write_kml(output_path, f"Level2 {table_name}", placemarks)
        print(output_path)


if __name__ == "__main__":
    main()
