from __future__ import annotations

import math
from dataclasses import dataclass

from shapely.geometry import LineString, Point

from .net_jvg_resolver import NetJvgResolver
from .trafikverket_gpkg import TrafikverketGeoPackage


class LocalConnectorSearchError(Exception):
    """Basundantag för lokal connector-sökning."""


@dataclass(frozen=True, slots=True)
class ConnectorCandidate:
    """
    Kandidatlänk för att binda ett lokalt gap.

    Parameters
    ----------
    link_id : int
        Länkens rad-id.
    linksequence_oid : str
        Länksekvensens OID.
    length_m : float
        Länkens längd.
    distance_to_corridor_m : float
        Minsta avstånd från länkgeometri till gapkorridoren.
    start_distance_m : float
        Avstånd från länk till gapets startpunkt.
    end_distance_m : float
        Avstånd från länk till gapets slutpunkt.
    """

    link_id: int
    linksequence_oid: str
    length_m: float
    distance_to_corridor_m: float
    start_distance_m: float
    end_distance_m: float


class LocalConnectorSearch:
    """
    Söker lokala connector-kandidater kring korta gap mellan ankarssegment.

    Parameters
    ----------
    resolver : NetJvgResolver
        Resolver för Net_JVG-data.
    """

    def __init__(self, resolver: NetJvgResolver) -> None:
        """
        Initierar lokal connector-sökning.

        Parameters
        ----------
        resolver : NetJvgResolver
            Resolver för Net_JVG-data.
        """
        self.resolver = resolver
        self.gpkg: TrafikverketGeoPackage = resolver.gpkg

    @classmethod
    def from_config_file(cls, config_path: str = "config.json") -> "LocalConnectorSearch":
        """
        Skapar instans från konfigurationsfil.

        Parameters
        ----------
        config_path : str, optional
            Sökväg till konfigurationsfil.

        Returns
        -------
        LocalConnectorSearch
            Färdig instans.
        """
        return cls(NetJvgResolver.from_config_file(config_path))

    def _decode_link_vertices(self, geom: bytes | None) -> list[tuple[float, float]]:
        """
        Dekodar länkens vertexlista.

        Parameters
        ----------
        geom : bytes | None
            GeoPackage-geometri.

        Returns
        -------
        list[tuple[float, float]]
            Vertexlista i SWEREF 99 TM.
        """
        return self.resolver._decode_link_vertices(geom)

    def find_candidates_for_gap(
        self,
        from_point: tuple[float, float],
        to_point: tuple[float, float],
        corridor_buffer_m: float = 250.0,
        endpoint_radius_m: float = 400.0,
        limit: int = 50,
    ) -> list[ConnectorCandidate]:
        """
        Söker lokala kandidatlänkar i en korridor kring ett gap.

        Parameters
        ----------
        from_point : tuple[float, float]
            Startpunkt för gapet.
        to_point : tuple[float, float]
            Slutpunkt för gapet.
        corridor_buffer_m : float, optional
            Buffert runt gapets raka korridor.
        endpoint_radius_m : float, optional
            Max tillåtet avstånd till någon av gapets ändpunkter.
        limit : int, optional
            Max antal kandidater att returnera.

        Returns
        -------
        list[ConnectorCandidate]
            Kandidatlänkar sorterade efter relevans.
        """
        corridor = LineString([from_point, to_point])
        corridor_polygon = corridor.buffer(corridor_buffer_m)
        start_geometry = Point(from_point)
        end_geometry = Point(to_point)

        rows = self.gpkg.fetch_rows(
            "Net_JVG_Link",
            limit=self.gpkg.count_rows("Net_JVG_Link"),
            columns=["id", "geom", "LINKSEQUENCE_OID", "LENGTH"],
        )
        candidates: list[ConnectorCandidate] = []
        for row in rows:
            vertices = self._decode_link_vertices(row.get("geom"))
            if len(vertices) < 2:
                continue
            line = LineString(vertices)
            if not line.intersects(corridor_polygon):
                continue
            start_distance_m = line.distance(start_geometry)
            end_distance_m = line.distance(end_geometry)
            if min(start_distance_m, end_distance_m) > endpoint_radius_m:
                continue
            candidates.append(
                ConnectorCandidate(
                    link_id=int(row["id"]),
                    linksequence_oid=str(row["LINKSEQUENCE_OID"]),
                    length_m=float(row["LENGTH"]),
                    distance_to_corridor_m=line.distance(corridor),
                    start_distance_m=start_distance_m,
                    end_distance_m=end_distance_m,
                )
            )

        candidates.sort(
            key=lambda item: (
                item.start_distance_m + item.end_distance_m,
                item.distance_to_corridor_m,
                item.length_m,
            )
        )
        return candidates[:limit]
