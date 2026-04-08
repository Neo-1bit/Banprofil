from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable
from xml.sax.saxutils import escape

from .height_profile import HeightSample


@dataclass(frozen=True, slots=True)
class KmlPlacemark:
    name: str
    description: str
    coordinates: str


@dataclass(frozen=True, slots=True)
class Wgs84Point:
    longitude: float
    latitude: float
    altitude: float


def sweref99tm_to_wgs84(easting: float, northing: float, altitude: float = 0.0) -> Wgs84Point:
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


def build_kml_document(name: str, placemarks: Iterable[KmlPlacemark]) -> str:
    body = []
    for placemark in placemarks:
        body.append(
            f"""
    <Placemark>
      <name>{escape(placemark.name)}</name>
      <description>{escape(placemark.description)}</description>
      <Style>
        <LineStyle>
          <color>ff00a5ff</color>
          <width>3</width>
        </LineStyle>
      </Style>
      <LineString>
        <tessellate>1</tessellate>
        <altitudeMode>absolute</altitudeMode>
        <coordinates>{placemark.coordinates}</coordinates>
      </LineString>
    </Placemark>"""
        )

    return f"""<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2">
  <Document>
    <name>{escape(name)}</name>{''.join(body)}
  </Document>
</kml>
"""


def height_samples_to_linestring(samples: list[HeightSample]) -> str:
    coords = []
    for sample in samples:
        point = sweref99tm_to_wgs84(sample.e, sample.n, sample.z if sample.z is not None else 0.0)
        coords.append(f"{point.longitude},{point.latitude},{point.altitude}")
    return " ".join(coords)


def export_height_profile_kml(samples: list[HeightSample], output_path: str | Path, name: str = "Banprofil Proof of Concept") -> Path:
    placemark = KmlPlacemark(
        name=name,
        description="Höjdprofil exporterad från Banprofil i WGS84 för Google Earth",
        coordinates=height_samples_to_linestring(samples),
    )
    content = build_kml_document(name=name, placemarks=[placemark])
    path = Path(output_path)
    path.write_text(content, encoding="utf-8")
    return path
