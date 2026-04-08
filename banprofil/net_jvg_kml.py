from __future__ import annotations

import math
import struct
from dataclasses import dataclass
from pathlib import Path
from xml.sax.saxutils import escape

from .net_jvg_resolver import NetJvgResolver, TraversalResult


class NetJvgKmlError(Exception):
    """Basundantag för Net_JVG KML-export."""


@dataclass(frozen=True, slots=True)
class TraversalLinkGeometry:
    """
    Geometri och traversalmetadata för en traverserad Net_JVG-länk.

    Parameters
    ----------
    link_id : int
        Länkens rad-id.
    vertices : list[tuple[float, float]]
        Vertexlista i SWEREF 99 TM.
    sequence_index : int
        Länkens position i traverseringsordningen.
    start_node_oid : str | None
        Startnod för länken i traversalriktning.
    end_node_oid : str | None
        Slutnod för länken i traversalriktning.
    """

    link_id: int
    vertices: list[tuple[float, float]]
    sequence_index: int
    start_node_oid: str | None = None
    end_node_oid: str | None = None


def sweref99tm_to_wgs84(easting: float, northing: float, altitude: float = 0.0) -> tuple[float, float, float]:
    """
    Omvandlar SWEREF 99 TM till WGS84.

    Parameters
    ----------
    easting : float
        Easting i SWEREF 99 TM.
    northing : float
        Northing i SWEREF 99 TM.
    altitude : float, optional
        Höjd i meter.

    Returns
    -------
    tuple[float, float, float]
        Longitud, latitud och höjd.
    """
    import math

    axis = 6378137.0
    flattening = 1.0 / 298.257222101
    central_meridian = math.radians(15.0)
    scale = 0.9996
    false_northing = 0.0
    false_easting = 500000.0

    e2 = flattening * (2.0 - flattening)
    n = flattening / (2.0 - flattening)
    a_roof = axis / (1.0 + n) * (1.0 + n**2 / 4.0 + n**4 / 64.0)
    delta1 = n / 2.0 - 2.0 * n**2 / 3.0 + 37.0 * n**3 / 96.0 - n**4 / 360.0
    delta2 = n**2 / 48.0 + n**3 / 15.0 - 437.0 * n**4 / 1440.0
    delta3 = 17.0 * n**3 / 480.0 - 37.0 * n**4 / 840.0
    delta4 = 4397.0 * n**4 / 161280.0

    a_star = e2 + e2**2 + e2**3 + e2**4
    b_star = -(7.0 * e2**2 + 17.0 * e2**3 + 30.0 * e2**4) / 6.0
    c_star = (224.0 * e2**3 + 889.0 * e2**4) / 120.0
    d_star = -(4279.0 * e2**4) / 1260.0

    xi = (northing - false_northing) / (scale * a_roof)
    eta = (easting - false_easting) / (scale * a_roof)

    xi_prim = (
        xi
        - delta1 * math.sin(2.0 * xi) * math.cosh(2.0 * eta)
        - delta2 * math.sin(4.0 * xi) * math.cosh(4.0 * eta)
        - delta3 * math.sin(6.0 * xi) * math.cosh(6.0 * eta)
        - delta4 * math.sin(8.0 * xi) * math.cosh(8.0 * eta)
    )
    eta_prim = (
        eta
        - delta1 * math.cos(2.0 * xi) * math.sinh(2.0 * eta)
        - delta2 * math.cos(4.0 * xi) * math.sinh(4.0 * eta)
        - delta3 * math.cos(6.0 * xi) * math.sinh(6.0 * eta)
        - delta4 * math.cos(8.0 * xi) * math.sinh(8.0 * eta)
    )

    phi_star = math.asin(math.sin(xi_prim) / math.cosh(eta_prim))
    delta_lambda = math.atan(math.sinh(eta_prim) / math.cos(xi_prim))

    lon_radian = central_meridian + delta_lambda
    lat_radian = phi_star + math.sin(phi_star) * math.cos(phi_star) * (
        a_star
        + b_star * math.sin(phi_star) ** 2
        + c_star * math.sin(phi_star) ** 4
        + d_star * math.sin(phi_star) ** 6
    )

    return math.degrees(lon_radian), math.degrees(lat_radian), altitude


def _decode_link_vertices(geom: bytes) -> list[tuple[float, float]]:
    """
    Dekodar vertices ur GeoPackage-linjegeometri för `Net_JVG_Link`.

    Trafikverkets masterdata använder här en generell GEOMETRY med Z och M,
    där WKB-delen innehåller 4D-koordinater per vertex.

    Parameters
    ----------
    geom : bytes
        GeoPackage-geometri.

    Returns
    -------
    list[tuple[float, float]]
        Vertexlista i SWEREF 99 TM.
    """
    if not isinstance(geom, bytes) or len(geom) < 65:
        return []
    point_count = struct.unpack('<I', geom[57:61])[0] - 3000
    if point_count <= 0:
        return []
    offset = 65
    points: list[tuple[float, float]] = []
    for _ in range(point_count):
        if offset + 32 > len(geom):
            break
        x = struct.unpack('<d', geom[offset:offset + 8])[0]
        y = struct.unpack('<d', geom[offset + 8:offset + 16])[0]
        points.append((x, y))
        offset += 32
    return points


def _distance(point_a: tuple[float, float], point_b: tuple[float, float]) -> float:
    """
    Beräknar euklidiskt avstånd mellan två punkter.

    Parameters
    ----------
    point_a : tuple[float, float]
        Första punkt.
    point_b : tuple[float, float]
        Andra punkt.

    Returns
    -------
    float
        Avstånd i meter.
    """
    return math.hypot(point_a[0] - point_b[0], point_a[1] - point_b[1])


def _load_traversal_link_geometries(
    resolver: NetJvgResolver,
    traversal: TraversalResult,
) -> list[TraversalLinkGeometry]:
    """
    Läser geometrier för traverserade länkar i traversalordning.

    Parameters
    ----------
    resolver : NetJvgResolver
        Resolver med åtkomst till master-GPKG.
    traversal : TraversalResult
        Traverserad korridor.

    Returns
    -------
    list[TraversalLinkGeometry]
        Traverserade länkar med geometri i traversalordning.
    """
    if not traversal.traversed_link_ids:
        return []

    link_id_to_index = {link_id: index for index, link_id in enumerate(traversal.traversed_link_ids)}
    rows = resolver.gpkg.fetch_rows(
        "Net_JVG_Link",
        limit=50000,
        columns=["id", "geom", "START_NODE_OID", "END_NODE_OID"],
    )
    traversed_nodes = traversal.traversed_node_oids
    geometries: list[TraversalLinkGeometry] = []
    for row in rows:
        link_id = int(row["id"])
        if link_id not in link_id_to_index:
            continue
        vertices = _decode_link_vertices(row["geom"])
        if not vertices:
            continue
        sequence_index = link_id_to_index[link_id]
        start_node_oid = None
        end_node_oid = None
        if sequence_index + 1 < len(traversed_nodes):
            start_node_oid = traversed_nodes[sequence_index]
            end_node_oid = traversed_nodes[sequence_index + 1]
        row_start_node_oid = str(row["START_NODE_OID"])
        row_end_node_oid = str(row["END_NODE_OID"])
        if start_node_oid == row_end_node_oid and end_node_oid == row_start_node_oid:
            vertices.reverse()
        geometries.append(
            TraversalLinkGeometry(
                link_id=link_id,
                vertices=vertices,
                sequence_index=sequence_index,
                start_node_oid=start_node_oid,
                end_node_oid=end_node_oid,
            )
        )
    geometries.sort(key=lambda item: item.sequence_index)
    return geometries


def _sequence_traversal_vertices(
    link_geometries: list[TraversalLinkGeometry],
    max_gap_m: float = 25.0,
) -> list[list[tuple[float, float]]]:
    """
    Syr ihop traverserade länkar till längre sammanhängande linjesträngar.

    Parameters
    ----------
    link_geometries : list[TraversalLinkGeometry]
        Traverserade länkar med geometri i traversalordning.
    max_gap_m : float, optional
        Max tillåtet gap mellan länkändar innan en ny delsträcka startas.

    Returns
    -------
    list[list[tuple[float, float]]]
        En eller flera sammanhängande vertexsekvenser.
    """
    sequences: list[list[tuple[float, float]]] = []
    current_sequence: list[tuple[float, float]] = []

    for link_geometry in link_geometries:
        vertices = list(link_geometry.vertices)
        if len(vertices) < 2:
            continue

        if not current_sequence:
            current_sequence = vertices
            continue

        start_gap = _distance(current_sequence[-1], vertices[0])

        if start_gap <= max_gap_m:
            if _distance(current_sequence[-1], vertices[0]) <= 1e-6:
                current_sequence.extend(vertices[1:])
            else:
                current_sequence.extend(vertices)
            continue

        sequences.append(current_sequence)
        current_sequence = vertices

    if current_sequence:
        sequences.append(current_sequence)
    return sequences


def _vertices_to_kml_coordinates(vertices: list[tuple[float, float]]) -> str:
    """
    Omvandlar SWEREF-vertices till KML-koordinatsträng.

    Parameters
    ----------
    vertices : list[tuple[float, float]]
        Vertexlista i SWEREF 99 TM.

    Returns
    -------
    str
        KML-koordinater i WGS84.
    """
    coords: list[str] = []
    for x, y in vertices:
        lon, lat, alt = sweref99tm_to_wgs84(x, y, 0.0)
        coords.append(f"{lon},{lat},{alt}")
    return " ".join(coords)


def export_traversal_kml(
    resolver: NetJvgResolver,
    traversal: TraversalResult,
    output_path: str | Path,
    name: str = "Net_JVG Traversal Debug",
) -> Path:
    """
    Exporterar traverserad Net_JVG-korridor till KML.

    Sequencing v3 ordnar traverserade länkar i traversalordning, vänder vid
    behov länkgeometrierna och syr ihop intilliggande länkar till längre
    linjesträngar när ändpunkterna ligger nära varandra.

    Parameters
    ----------
    resolver : NetJvgResolver
        Resolver med åtkomst till master-GPKG.
    traversal : TraversalResult
        Traverserad korridor.
    output_path : str | Path
        Sökväg till utdatafil.
    name : str, optional
        Namn i KML-dokumentet.

    Returns
    -------
    Path
        Sökväg till skapad fil.

    Raises
    ------
    NetJvgKmlError
        Om inga geometrier kunde hittas för traverseringen.
    """
    link_geometries = _load_traversal_link_geometries(resolver=resolver, traversal=traversal)
    if not link_geometries:
        raise NetJvgKmlError("No Net_JVG link geometries found for traversal")

    sequences = _sequence_traversal_vertices(link_geometries=link_geometries)
    placemarks = []
    for index, sequence in enumerate(sequences, start=1):
        placemarks.append(
            f"""
    <Placemark>
      <name>{escape(name)} sekvens {index}</name>
      <description>{escape(f'Länkar: {len(link_geometries)}. Vertex i sekvens: {len(sequence)}.')}</description>
      <Style>
        <LineStyle><color>ff0000ff</color><width>5</width></LineStyle>
      </Style>
      <LineString>
        <tessellate>1</tessellate>
        <coordinates>{_vertices_to_kml_coordinates(sequence)}</coordinates>
      </LineString>
    </Placemark>"""
        )

    for link_geometry in link_geometries:
        placemarks.append(
            f"""
    <Placemark>
      <name>{escape(name)} link {link_geometry.link_id}</name>
      <Style>
        <LineStyle><color>b3000000</color><width>2</width></LineStyle>
      </Style>
      <LineString>
        <tessellate>1</tessellate>
        <coordinates>{_vertices_to_kml_coordinates(link_geometry.vertices)}</coordinates>
      </LineString>
    </Placemark>"""
        )

    content = f"""<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2">
  <Document>
    <name>{escape(name)}</name>{''.join(placemarks)}
  </Document>
</kml>
"""
    path = Path(output_path)
    path.write_text(content, encoding="utf-8")
    return path
