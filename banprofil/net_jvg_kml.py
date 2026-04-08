from __future__ import annotations

import struct
from pathlib import Path
from xml.sax.saxutils import escape

from .net_jvg_resolver import NetJvgResolver, TraversalResult


class NetJvgKmlError(Exception):
    """Basundantag för Net_JVG KML-export."""


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
    Dekodar vertices ur GeoPackage-linjegeometri.

    Parameters
    ----------
    geom : bytes
        GeoPackage-geometri.

    Returns
    -------
    list[tuple[float, float]]
        Vertexlista i SWEREF 99 TM.
    """
    if not isinstance(geom, bytes) or len(geom) < 40:
        return []
    # Temporär men bättre debug-geometri: använd länkens bbox som diagonal linje.
    minx, maxx, miny, maxy = struct.unpack('<dddd', geom[8:40])
    return [(minx, miny), (maxx, maxy)]


def export_traversal_kml(
    resolver: NetJvgResolver,
    traversal: TraversalResult,
    output_path: str | Path,
    name: str = "Net_JVG Traversal Debug",
) -> Path:
    """
    Exporterar traverserad Net_JVG-korridor till KML.

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
    link_ids = set(traversal.traversed_link_ids)
    rows = resolver.gpkg.fetch_rows("Net_JVG_Link", limit=50000, columns=["id", "geom"])
    placemarks = []
    for row in rows:
        if int(row["id"]) not in link_ids:
            continue
        vertices = _decode_link_vertices(row["geom"])
        if not vertices:
            continue
        coords = []
        for x, y in vertices:
            lon, lat, alt = sweref99tm_to_wgs84(x, y, 0.0)
            coords.append(f"{lon},{lat},{alt}")
        placemarks.append(
            f"""
    <Placemark>
      <name>{escape(name)} link {row['id']}</name>
      <Style>
        <LineStyle><color>ff00a5ff</color><width>3</width></LineStyle>
      </Style>
      <LineString>
        <tessellate>1</tessellate>
        <coordinates>{' '.join(coords)}</coordinates>
      </LineString>
    </Placemark>"""
        )

    if not placemarks:
        raise NetJvgKmlError("No Net_JVG link geometries found for traversal")

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
