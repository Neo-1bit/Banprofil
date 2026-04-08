from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from .trafikverket_gpkg import TrafikverketGeoPackage, TrafikverketGeoPackageError

KM_PATTERN = re.compile(r"^\s*(\d+)\s*\+\s*(\d+(?:[\.,]\d+)?)\s*$")


class ProfileChainError(Exception):
    """Base exception for km-tal/profile-chain helpers."""


@dataclass(frozen=True, slots=True)
class KmValue:
    kilometers: int
    meters: float

    @property
    def total_meters(self) -> float:
        return self.kilometers * 1000.0 + self.meters


def parse_km_string(value: str) -> KmValue:
    match = KM_PATTERN.match(value)
    if not match:
        raise ProfileChainError(f"Invalid km-tal format: {value!r}")

    kilometers = int(match.group(1))
    meters = float(match.group(2).replace(',', '.'))
    return KmValue(kilometers=kilometers, meters=meters)


def format_km_value(total_meters: float) -> str:
    kilometers = int(total_meters // 1000)
    meters = total_meters - kilometers * 1000
    if meters.is_integer():
        meter_str = f"{int(meters):03d}"
    else:
        meter_str = f"{meters:06.3f}".rstrip("0").rstrip(".")
    return f"{kilometers}+{meter_str}"


def km_range_to_meters(start_km: str, end_km: str) -> tuple[float, float]:
    start = parse_km_string(start_km).total_meters
    end = parse_km_string(end_km).total_meters
    if end < start:
        raise ProfileChainError("End km-tal must be greater than or equal to start km-tal")
    return start, end


class ProfileChainIndex:
    DEFAULT_PROFILE_LAYERS = {
        "raklinje": "BIS_DK_O_4012_Raklinje",
        "cirkularkurva": "BIS_DK_O_4010_Cirkularkurva",
        "overgangskurva": "BIS_DK_O_4011_Overgangskurva",
        "vertikalkurva": "BIS_DK_O_4014_Vertikalkurva",
        "lutning": "BIS_DK_O_4015_Lutning",
    }

    def __init__(self, gpkg: TrafikverketGeoPackage) -> None:
        self.gpkg = gpkg

    def fetch_profile_range(
        self,
        layer_key: str,
        start_km: str,
        end_km: str,
        limit: int = 500,
    ) -> list[dict[str, Any]]:
        table_name = self.DEFAULT_PROFILE_LAYERS.get(layer_key)
        if not table_name:
            raise ProfileChainError(
                f"Unknown profile layer '{layer_key}'. Available: {', '.join(sorted(self.DEFAULT_PROFILE_LAYERS))}"
            )

        start_meters, end_meters = km_range_to_meters(start_km, end_km)
        rows = self.gpkg.fetch_rows(table_name=table_name, limit=limit)
        matches: list[dict[str, Any]] = []

        for row in rows:
            row_start = row.get("Kmtal")
            row_end = row.get("Kmtalti")
            if not row_start or not row_end:
                continue

            try:
                row_start_m = parse_km_string(str(row_start)).total_meters
                row_end_m = parse_km_string(str(row_end)).total_meters
            except ProfileChainError:
                continue

            overlaps = row_end_m >= start_meters and row_start_m <= end_meters
            if overlaps:
                enriched = dict(row)
                enriched["profile_start_m"] = row_start_m
                enriched["profile_end_m"] = row_end_m
                matches.append(enriched)

        matches.sort(key=lambda item: item.get("profile_start_m", 0.0))
        return matches

    def build_forward_view(
        self,
        start_km: str,
        end_km: str,
    ) -> dict[str, list[dict[str, Any]]]:
        view: dict[str, list[dict[str, Any]]] = {}
        for layer_key in self.DEFAULT_PROFILE_LAYERS:
            view[layer_key] = self.fetch_profile_range(layer_key, start_km=start_km, end_km=end_km)
        return view
