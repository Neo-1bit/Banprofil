from __future__ import annotations

import re
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
    Första projektionen av featurelager ovanpå en traverserad Net_JVG-korridor.

    Den här första versionen använder korridorens geometriområde som grov
    kandidatfilter. Nästa version bör projicera features mer exakt mot länkar.

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
        return cls(gpkg=resolver.gpkg, resolver=resolver)

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

    def _corridor_bbox_from_traversal(self, traversal: TraversalResult) -> dict[str, float]:
        """
        Beräknar grov bbox för traverserade länkar.

        Parameters
        ----------
        traversal : TraversalResult
            Resultat från traversal.

        Returns
        -------
        dict[str, float]
            Bounding box för traverserade länkar.
        """
        link_id_set = set(traversal.traversed_link_ids)
        rows = self.gpkg.fetch_rows("Net_JVG_Link", limit=50000, columns=["id", "geom"])
        boxes = []
        for row in rows:
            if int(row["id"]) not in link_id_set:
                continue
            geom = row["geom"]
            if not isinstance(geom, bytes) or len(geom) < 40:
                continue
            import struct

            minx, maxx, miny, maxy = struct.unpack("<dddd", geom[8:40])
            boxes.append((minx, maxx, miny, maxy))
        if not boxes:
            raise FeatureProjectionError("No link geometries found for traversal")
        return {
            "minx": min(item[0] for item in boxes),
            "maxx": max(item[1] for item in boxes),
            "miny": min(item[2] for item in boxes),
            "maxy": max(item[3] for item in boxes),
        }

    def project_features_from_traversal(self, traversal: TraversalResult) -> list[ProjectedFeatureSummary]:
        """
        Hämtar grova featurekandidater för en traverserad korridor.

        Parameters
        ----------
        traversal : TraversalResult
            Traverserad nätverkskorridor.

        Returns
        -------
        list[ProjectedFeatureSummary]
            Sammanfattning av kandidater per featurelager.
        """
        bbox = self._corridor_bbox_from_traversal(traversal)
        summaries: list[ProjectedFeatureSummary] = []
        for layer_key, table_name in self.FEATURE_TABLES.items():
            rows = self.gpkg.fetch_rows(
                table_name,
                limit=50000,
                columns=["Koordinater_start", "Koordinater_slut"],
            )
            count = 0
            for row in rows:
                for key in ("Koordinater_start", "Koordinater_slut"):
                    point = self._parse_point_xy(row.get(key))
                    if not point:
                        continue
                    x, y = point
                    if bbox["minx"] <= x <= bbox["maxx"] and bbox["miny"] <= y <= bbox["maxy"]:
                        count += 1
                        break
            summaries.append(
                ProjectedFeatureSummary(
                    layer_key=layer_key,
                    candidate_count=count,
                    notes="Första projektionen använder korridorens bbox som grovt filter. Nästa steg är exakt länkprojektion.",
                )
            )
        return summaries
