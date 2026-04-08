from __future__ import annotations

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


def build_kml_document(name: str, placemarks: Iterable[KmlPlacemark]) -> str:
    body = []
    for placemark in placemarks:
        body.append(
            f"""
    <Placemark>
      <name>{escape(placemark.name)}</name>
      <description>{escape(placemark.description)}</description>
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
    return " ".join(f"{sample.e},{sample.n},{sample.z if sample.z is not None else 0.0}" for sample in samples)


def export_height_profile_kml(samples: list[HeightSample], output_path: str | Path, name: str = "Banprofil Proof of Concept") -> Path:
    placemark = KmlPlacemark(
        name=name,
        description="Höjdprofil exporterad från Banprofil",
        coordinates=height_samples_to_linestring(samples),
    )
    content = build_kml_document(name=name, placemarks=[placemark])
    path = Path(output_path)
    path.write_text(content, encoding="utf-8")
    return path
