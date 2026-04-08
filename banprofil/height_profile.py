from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from .lantmateriet_client import LantmaterietClient, LantmaterietError
from .profile_chain import ProfileChainIndex
from .trafikverket_gpkg import TrafikverketGeoPackage

POINT_Z_PATTERN = re.compile(
    r"POINT\((?P<e>-?\d+(?:\.\d+)?)\s+(?P<n>-?\d+(?:\.\d+)?)\s+(?P<z>-?\d+(?:\.\d+)?)\)"
)


class HeightProfileError(Exception):
    """Base exception for height profile building."""


@dataclass(frozen=True, slots=True)
class HeightSample:
    source: str
    km: str
    e: float
    n: float
    z: float | None
    metadata: dict[str, Any]


class HeightProfileBuilder:
    def __init__(
        self,
        gpkg: TrafikverketGeoPackage,
        lantmateriet_client: LantmaterietClient | None = None,
    ) -> None:
        self.gpkg = gpkg
        self.profile_index = ProfileChainIndex(gpkg)
        self.lantmateriet_client = lantmateriet_client

    @classmethod
    def from_config_file(cls, config_path: str = "config.json") -> "HeightProfileBuilder":
        gpkg = TrafikverketGeoPackage.from_config_file(config_path)
        try:
            lantmateriet_client = LantmaterietClient.from_config_file(config_path)
        except Exception:
            lantmateriet_client = None
        return cls(gpkg=gpkg, lantmateriet_client=lantmateriet_client)

    def _parse_point(self, value: str | None) -> tuple[float, float, float] | None:
        if not value:
            return None
        match = POINT_Z_PATTERN.search(value)
        if not match:
            return None
        return (
            float(match.group("e")),
            float(match.group("n")),
            float(match.group("z")),
        )

    def _lm_height(self, e: float, n: float) -> float | None:
        if not self.lantmateriet_client:
            return None
        try:
            return self.lantmateriet_client.get_elevation_value(e=e, n=n, srid=3006)
        except LantmaterietError:
            return None

    def build_height_profile(self, start_km: str, end_km: str) -> list[HeightSample]:
        forward_view = self.profile_index.build_forward_view(start_km=start_km, end_km=end_km)
        samples: list[HeightSample] = []
        seen: set[tuple[str, str, str]] = set()

        for layer_name, rows in forward_view.items():
            for row in rows:
                for point_key, km_key in (("Koordinater_start", "Kmtal"), ("Koordinater_slut", "Kmtalti")):
                    parsed = self._parse_point(row.get(point_key))
                    km_value = row.get(km_key)
                    if not parsed or not km_value:
                        continue

                    e, n, trafikverket_z = parsed
                    dedupe_key = (str(km_value), f"{e:.3f}", f"{n:.3f}")
                    if dedupe_key in seen:
                        continue
                    seen.add(dedupe_key)

                    z = trafikverket_z if trafikverket_z is not None else self._lm_height(e, n)
                    source = "trafikverket" if trafikverket_z is not None else "lantmateriet"

                    samples.append(
                        HeightSample(
                            source=source,
                            km=str(km_value),
                            e=e,
                            n=n,
                            z=z,
                            metadata={
                                "layer": layer_name,
                                "element_id": row.get("ELEMENT_ID"),
                                "bisobjektnr": row.get("Bisobjektnr"),
                                "lutning_promille": row.get("Lutning_promille"),
                                "radie_m": row.get("Radie_m"),
                            },
                        )
                    )

        samples.sort(key=lambda sample: sample.km)
        return samples
