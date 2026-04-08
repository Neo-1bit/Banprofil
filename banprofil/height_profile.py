from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from .lantmateriet_client import LantmaterietClient, LantmaterietError
from .profile_chain import ProfileChainIndex, parse_km_string
from .trafikverket_gpkg import TrafikverketGeoPackage

POINT_Z_PATTERN = re.compile(
    r"POINT\((?P<e>-?\d+(?:\.\d+)?)\s+(?P<n>-?\d+(?:\.\d+)?)\s+(?P<z>-?\d+(?:\.\d+)?)\)"
)


class HeightProfileError(Exception):
    """Base exception for height profile building."""


@dataclass(slots=True)
class HeightSample:
    source: str
    km: str
    e: float
    n: float
    z: float | None
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def km_meters(self) -> float:
        return parse_km_string(self.km).total_meters


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

    def _merge_metadata(self, existing: dict[str, Any], incoming: dict[str, Any]) -> dict[str, Any]:
        merged = dict(existing)

        layers = set()
        for value in (existing.get("layers"), incoming.get("layers")):
            if isinstance(value, list):
                layers.update(str(item) for item in value if item)
        for value in (existing.get("layer"), incoming.get("layer")):
            if value:
                layers.add(str(value))
        if layers:
            merged["layers"] = sorted(layers)
            merged.pop("layer", None)

        element_ids = set()
        for value in (existing.get("element_ids"), incoming.get("element_ids")):
            if isinstance(value, list):
                element_ids.update(str(item) for item in value if item)
        for value in (existing.get("element_id"), incoming.get("element_id")):
            if value:
                element_ids.add(str(value))
        if element_ids:
            merged["element_ids"] = sorted(element_ids)
            merged.pop("element_id", None)

        bisobjektnr = set()
        for value in (existing.get("bisobjektnr_list"), incoming.get("bisobjektnr_list")):
            if isinstance(value, list):
                bisobjektnr.update(value)
        for value in (existing.get("bisobjektnr"), incoming.get("bisobjektnr")):
            if value is not None:
                bisobjektnr.add(value)
        if bisobjektnr:
            merged["bisobjektnr_list"] = sorted(bisobjektnr)
            merged.pop("bisobjektnr", None)

        for numeric_key in ("lutning_promille", "radie_m"):
            values = []
            for source in (existing, incoming):
                value = source.get(numeric_key)
                if value is not None and value not in values:
                    values.append(value)
            if values:
                merged[numeric_key] = values[0] if len(values) == 1 else values

        return merged

    def build_height_profile(self, start_km: str, end_km: str) -> list[HeightSample]:
        forward_view = self.profile_index.build_forward_view(start_km=start_km, end_km=end_km)
        samples_by_key: dict[tuple[int, int, int], HeightSample] = {}

        for layer_name, rows in forward_view.items():
            for row in rows:
                for point_key, km_key in (("Koordinater_start", "Kmtal"), ("Koordinater_slut", "Kmtalti")):
                    parsed = self._parse_point(row.get(point_key))
                    km_value = row.get(km_key)
                    if not parsed or not km_value:
                        continue

                    e, n, trafikverket_z = parsed
                    km_text = str(km_value)
                    km_meters = parse_km_string(km_text).total_meters
                    dedupe_key = (
                        round(km_meters * 1000),
                        round(e * 1000),
                        round(n * 1000),
                    )

                    z = trafikverket_z if trafikverket_z is not None else self._lm_height(e, n)
                    source = "trafikverket" if trafikverket_z is not None else "lantmateriet"
                    metadata = {
                        "layer": layer_name,
                        "element_id": row.get("ELEMENT_ID"),
                        "bisobjektnr": row.get("Bisobjektnr"),
                        "lutning_promille": row.get("Lutning_promille"),
                        "radie_m": row.get("Radie_m"),
                    }

                    existing = samples_by_key.get(dedupe_key)
                    if existing is None:
                        samples_by_key[dedupe_key] = HeightSample(
                            source=source,
                            km=km_text,
                            e=e,
                            n=n,
                            z=z,
                            metadata=metadata,
                        )
                        continue

                    existing.metadata = self._merge_metadata(existing.metadata, metadata)
                    if existing.source != "trafikverket" and source == "trafikverket":
                        existing.source = source
                        existing.z = z
                    elif existing.z is None and z is not None:
                        existing.z = z

        samples = list(samples_by_key.values())
        samples.sort(key=lambda sample: (sample.km_meters, sample.e, sample.n))
        return samples
