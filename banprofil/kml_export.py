from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable
from xml.sax.saxutils import escape

from .height_profile import HeightSample, HeightSegment


@dataclass(frozen=True, slots=True)
class KmlPlacemark:
    """
    Beskriver ett KML-objekt som kan exporteras.

    Parameters
    ----------
    name : str
        Namn som visas i Google Earth.
    description : str
        Beskrivning som visas i popup.
    geometry_xml : str
        Färdig KML-geometri.
    style_id : str | None, optional
        Namn på stil som ska användas.
    """

    name: str
    description: str
    geometry_xml: str
    style_id: str | None = None


@dataclass(frozen=True, slots=True)
class Wgs84Point:
    """
    Representerar en punkt i WGS84.

    Parameters
    ----------
    longitude : float
        Longitud i decimalgrader.
    latitude : float
        Latitud i decimalgrader.
    altitude : float
        Höjd i meter.
    """

    longitude: float
    latitude: float
    altitude: float


def sweref99tm_to_wgs84(easting: float, northing: float, altitude: float = 0.0) -> Wgs84Point:
    """
    Omvandlar SWEREF 99 TM till WGS84 för KML-export.

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
    Wgs84Point
        Punkt i WGS84.
    """
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

    return Wgs84Point(
        longitude=math.degrees(lon_radian),
        latitude=math.degrees(lat_radian),
        altitude=altitude,
    )


def _line_string_geometry(coordinates: str) -> str:
    """
    Bygger LineString-geometri för KML.

    Parameters
    ----------
    coordinates : str
        Koordinatsträng i KML-format.

    Returns
    -------
    str
        XML-fragment för LineString.
    """
    return f"""
      <LineString>
        <tessellate>1</tessellate>
        <altitudeMode>absolute</altitudeMode>
        <coordinates>{coordinates}</coordinates>
      </LineString>"""


def _point_geometry(longitude: float, latitude: float, altitude: float) -> str:
    """
    Bygger Point-geometri för KML.

    Parameters
    ----------
    longitude : float
        Longitud i decimalgrader.
    latitude : float
        Latitud i decimalgrader.
    altitude : float
        Höjd i meter.

    Returns
    -------
    str
        XML-fragment för Point.
    """
    return f"""
      <Point>
        <altitudeMode>absolute</altitudeMode>
        <coordinates>{longitude},{latitude},{altitude}</coordinates>
      </Point>"""


def _styles_xml() -> str:
    """
    Returnerar standardstilar för KML-export.

    Returns
    -------
    str
        XML-fragment med stildefinitioner.
    """
    return """
    <Style id="profileLine">
      <LineStyle><color>ff00a5ff</color><width>3</width></LineStyle>
    </Style>
    <Style id="segmentLineFlat">
      <LineStyle><color>ff00ff00</color><width>3</width></LineStyle>
    </Style>
    <Style id="segmentLineUp">
      <LineStyle><color>ff0000ff</color><width>3</width></LineStyle>
    </Style>
    <Style id="segmentLineDown">
      <LineStyle><color>ff00ffff</color><width>3</width></LineStyle>
    </Style>
    <Style id="samplePoint">
      <IconStyle>
        <color>ff00a5ff</color>
        <scale>0.7</scale>
      </IconStyle>
    </Style>
    """


def build_kml_document(name: str, placemarks: Iterable[KmlPlacemark]) -> str:
    """
    Bygger ett komplett KML-dokument.

    Parameters
    ----------
    name : str
        Namn på dokumentet.
    placemarks : Iterable[KmlPlacemark]
        Placemark-objekt som ska skrivas ut.

    Returns
    -------
    str
        Färdigt KML-dokument som text.
    """
    body = []
    for placemark in placemarks:
        style_ref = f"<styleUrl>#{placemark.style_id}</styleUrl>" if placemark.style_id else ""
        body.append(
            f"""
    <Placemark>
      <name>{escape(placemark.name)}</name>
      <description>{escape(placemark.description)}</description>
      {style_ref}{placemark.geometry_xml}
    </Placemark>"""
        )

    return f"""<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2">
  <Document>
    <name>{escape(name)}</name>{_styles_xml()}{''.join(body)}
  </Document>
</kml>
"""


def height_samples_to_linestring(samples: list[HeightSample]) -> str:
    """
    Omvandlar höjdpunkter till KML-koordinatsträng.

    Parameters
    ----------
    samples : list[HeightSample]
        Höjdpunkter i SWEREF 99 TM.

    Returns
    -------
    str
        KML-koordinatsträng i WGS84.
    """
    coords = []
    for sample in samples:
        point = sweref99tm_to_wgs84(sample.e, sample.n, sample.z if sample.z is not None else 0.0)
        coords.append(f"{point.longitude},{point.latitude},{point.altitude}")
    return " ".join(coords)


def _segment_style(segment: HeightSegment) -> str:
    """
    Väljer stil för segment baserat på lutning.

    Parameters
    ----------
    segment : HeightSegment
        Segment som ska färgsättas.

    Returns
    -------
    str
        Stil-ID för segmentet.
    """
    if segment.average_grade_promille is None:
        return "segmentLineFlat"
    if segment.average_grade_promille > 1.0:
        return "segmentLineUp"
    if segment.average_grade_promille < -1.0:
        return "segmentLineDown"
    return "segmentLineFlat"


def export_height_profile_kml(
    samples: list[HeightSample],
    output_path: str | Path,
    name: str = "Banprofil Proof of Concept",
    segments: list[HeightSegment] | None = None,
) -> Path:
    """
    Exporterar höjdprofil och segment till KML.

    Parameters
    ----------
    samples : list[HeightSample]
        Höjdpunkter som ska exporteras.
    output_path : str | Path
        Sökväg till KML-fil som ska skapas.
    name : str, optional
        Namn på KML-dokumentet.
    segments : list[HeightSegment] | None, optional
        Segment som också ska exporteras.

    Returns
    -------
    Path
        Sökväg till skapad KML-fil.
    """
    placemarks: list[KmlPlacemark] = []

    placemarks.append(
        KmlPlacemark(
            name=name,
            description="Höjdprofil exporterad från Banprofil i WGS84 för Google Earth",
            geometry_xml=_line_string_geometry(height_samples_to_linestring(samples)),
            style_id="profileLine",
        )
    )

    for sample in samples:
        point = sweref99tm_to_wgs84(sample.e, sample.n, sample.z if sample.z is not None else 0.0)
        description = f"km: {sample.km}\nkälla: {sample.source}\nhöjd: {sample.z}"
        placemarks.append(
            KmlPlacemark(
                name=f"Punkt {sample.km}",
                description=description,
                geometry_xml=_point_geometry(point.longitude, point.latitude, point.altitude),
                style_id="samplePoint",
            )
        )

    for segment in segments or []:
        start = sweref99tm_to_wgs84(segment.start_e, segment.start_n, segment.start_z or 0.0)
        end = sweref99tm_to_wgs84(segment.end_e, segment.end_n, segment.end_z or 0.0)
        coordinates = f"{start.longitude},{start.latitude},{start.altitude} {end.longitude},{end.latitude},{end.altitude}"
        description = (
            f"från: {segment.start_km}\n"
            f"till: {segment.end_km}\n"
            f"längd: {segment.distance_m:.1f} m\n"
            f"delta z: {segment.delta_z}\n"
            f"medellutning: {segment.average_grade_promille} ‰"
        )
        placemarks.append(
            KmlPlacemark(
                name=f"Segment {segment.start_km} - {segment.end_km}",
                description=description,
                geometry_xml=_line_string_geometry(coordinates),
                style_id=_segment_style(segment),
            )
        )

    content = build_kml_document(name=name, placemarks=placemarks)
    path = Path(output_path)
    path.write_text(content, encoding="utf-8")
    return path
