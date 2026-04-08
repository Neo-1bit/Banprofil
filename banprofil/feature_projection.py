from __future__ import annotations

import math
import re
import struct
from dataclasses import dataclass
from typing import Any

from .net_jvg_resolver import NetJvgResolver, TraversalResult
from .trafikverket_gpkg import TrafikverketGeoPackage

POINT_Z_PATTERN = re.compile(
    r"POINT\((?P<e>-?\d+(?:\.\d+)?)\s+(?P<n>-?\d+(?:\.\d+)?)\s+(?P<z>-?\d+(?:\.\d+)?)\)"
)


class FeatureProjectionError(Exception):
    """Basundantag för feature projection."""


@dataclass(frozen=True, slots=True)
class ProjectedFeatureSummary:
    """
    Sammanfattning av projekterade features mot en traverserad korridor.

    Parameters
    ----------
    layer_key : str
        Namn på featurelager.
    candidate_count : int
        Antal kandidater som överlappar korridorens geometriområde.
    notes : str
        Kommentar om kvalitet eller begränsning i projektionen.
    """

    layer_key: str
    candidate_count: int
    notes: str


class FeatureProjector:
    """
    Projekterar featurelager ovanpå en traverserad Net_JVG-korridor.

    V3 använder både korridorens bbox och ett finare avståndsfilter för att
    minska mängden arbete per lager.

    Parameters
    ----------
    gpkg : TrafikverketGeoPackage
        GeoPackage-läsare mot masterfilen.
    resolver : NetJvgResolver
        Resolver för Net_JVG-korridorer.
    """

    FEATURE_TABLES = {
        "raklinje": "BIS_DK_O_4012_Raklinje",
        "lutning": "BIS_DK_O_4015_Lutning",
        "cirkularkurva": "BIS_DK_O_4010_Cirkularkurva",
        "overgangskurva": "BIS_DK_O_4011_Overgangskurva",
    }

    def __init__(self, gpkg: TrafikverketGeoPackage, resolver: NetJvgResolver) -> None:
        """
        Initierar feature projector.

        Parameters
        ----------
        gpkg : TrafikverketGeoPackage
            GeoPackage-läsare mot masterfilen.
        resolver : NetJvgResolver
            Resolver för Net_JVG-korridorer.
        """
        self.gpkg = gpkg
        self.resolver = resolver

    @classmethod
    def from_config_file(cls, config_path: str = "config.json") -> "FeatureProjector":
        """
        Skapar feature projector från konfigurationsfil.

        Parameters
        ----------
        config_path : str, optional
            Sökväg till konfigurationsfil.

        Returns
        -------
        FeatureProjector
            Färdig instans.
        """
        resolver = NetJvgResolver.from_config_file(config_path)
        return cls(gpkg=resolver.gpgk if False else resolver.gpkg, resolver=resolver)

    def _parse_point_xy(self, value: str | None) -> tuple[float, float] | None:
        """
        Tolkar X/Y ur punkttext.

        Parameters
        ----------
        value : str | None
            Punkt i textformat.

        Returns
        -------
        tuple[float, float] | None
            Easting och northing, eller `None` om punkt inte gick att tolka.
        """
        if not value:
            return None
        match = POINT_Z_PATTERN.search(value)
        if not match:
            return None
        return float(match.group("e")), float(match.group("n"))

    def _decode_link_vertices(self, geom: bytes) -> list[tuple[float, float]]:
        """
        Dekodar punktsekvens ur GeoPackage-linjegeometri.

        Parameters
        ----------
        geom : bytes
            GeoPackage-binär geometri för en länk.

        Returns
        -------
        list[tuple[float, float]]
            Lista av hörnpunkter i SWEREF 99 TM.
        """
        if not isinstance(geom, bytes) or len(geom) < 64:
            return []
        num_points = struct.unpack('<I', geom[57:61])[0]
        offset = 61
        points = []
        for _ in range(num_points):
            if offset + 16 > len(geom):
                break
            x, y = struct.unpack('<dd', geom[offset:offset + 16])
            points.append((x, y))
            offset += 16
        return points

    def _corridor_vertices_from_traversal(self, traversal: TraversalResult) -> list[tuple[float, float]]:
        """
        Hämtar alla länkpunkter för en traverserad korridor.

        Parameters
        ----------
        traversal : TraversalResult
            Traverserad nätverkskorridor.

        Returns
        -------
        list[tuple[float, float]]
            Länkpunkter för korridoren.
        """
        link_id_set = set(traversal.traversed_link_ids)
        rows = self.gpkg.fetch_rows("Net_JVG_Link", limit=50000, columns=["id", "geom"])
        vertices: list[tuple[float, float]] = []
        for row in rows:
            if int(row["id"]) not in link_id_set:
                continue
            vertices.extend(self._decode_link_vertices(row["geom"]))
        if not vertices:
            raise FeatureProjectionError("No link vertices found for traversal")
        return vertices

    def _corridor_bbox(self, vertices: list[tuple[float, float]], padding_m: float = 250.0) -> dict[str, float]:
        """
        Bygger bbox kring korridorens hörnpunkter.

        Parameters
        ----------
        vertices : list[tuple[float, float]]
            Korridorens hörnpunkter.
        padding_m : float, optional
            Extra marginal runt bbox i meter.

        Returns
        -------
        dict[str, float]
            Bounding box med padding.
        """
        xs = [vertex[0] for vertex in vertices]
        ys = [vertex[1] for vertex in vertices]
        return {
            "minx": min(xs) - padding_m,
            "maxx": max(xs) + padding_m,
            "miny": min(ys) - padding_m,
            "maxy": max(ys) + padding_m,
        }

    def _min_distance_to_corridor(self, point: tuple[float, float], corridor_vertices: list[tuple[float, float]]) -> float:
        """
        Beräknar minsta punktavstånd till korridorens hörnpunkter.

        Parameters
        ----------
        point : tuple[float, float]
            Punkt som ska testas.
        corridor_vertices : list[tuple[float, float]]
            Korridorens hörnpunkter.

        Returns
        -------
        float
            Minsta avstånd i meter.
        """
        px, py = point
        return min(math.hypot(px - vx, py - vy) for vx, vy in corridor_vertices)

    def project_features_from_traversal(
        self,
        traversal: TraversalResult,
        max_distance_m: float = 250.0,
        per_layer_limit: int = 12000,
    ) -> list[ProjectedFeatureSummary]:
        """
        Hämtar featurekandidater för en traverserad korridor.

        Parameters
        ----------
        traversal : TraversalResult
            Traverserad nätverkskorridor.
        max_distance_m : float, optional
            Maxavstånd från korridoren för att ett feature ska räknas som kandidat.
        per_layer_limit : int, optional
            Max antal rader att läsa per lager i denna fokuserade verifieringsversion.

        Returns
        -------
        list[ProjectedFeatureSummary]
            Sammanfattning av kandidater per featurelager.
        """
        corridor_vertices = self._corridor_vertices_from_traversal(traversal)
        bbox = self._corridor_bbox(corridor_vertices, padding_m=max_distance_m)
        summaries: list[ProjectedFeatureSummary] = []
        for layer_key, table_name in self.FEATURE_TABLES.items():
            rows = self.gpkg.fetch_rows(
                table_name,
                limit=per_layer_limit,
                columns=["Koordinater_start", "Koordinater_slut"],
            )
            count = 0
            for row in rows:
                points = [self._parse_point_xy(row.get("Koordinater_start")), self._parse_point_xy(row.get("Koordinater_slut"))]
                points = [point for point in points if point is not None]
                if not points:
                    continue
                # snabb bbox-gallring först
                in_bbox = [
                    point for point in points
                    if bbox["minx"] <= point[0] <= bbox["maxx"] and bbox["miny"] <= point[1] <= bbox["maxy"]
                ]
                if not in_bbox:
                    continue
                if min(self._min_distance_to_corridor(point, corridor_vertices) for point in in_bbox) <= max_distance_m:
                    count += 1
            summaries.append(
                ProjectedFeatureSummary(
                    layer_key=layer_key,
                    candidate_count=count,
                    notes=(
                        f"V3 använder bbox-gallring + minsta punktavstånd till traverserad länkkorridor "
                        f"med tröskel {max_distance_m} m och max {per_layer_limit} rader per lager i denna verifieringskörning."
                    ),
                )
            )
        return summaries
