from __future__ import annotations

import math
import re
from dataclasses import dataclass

from .gpkg_inspector import GeoPackageInspector
from .net_jvg_resolver import NetJvgResolver, TraversalResult

POINT_Z_PATTERN = re.compile(
    r"POINT\((?P<e>-?\d+(?:\.\d+)?)\s+(?P<n>-?\d+(?:\.\d+)?)\s+(?P<z>-?\d+(?:\.\d+)?)\)"
)


class HeightProfileError(Exception):
    """Basundantag för höjdprofil."""


@dataclass(frozen=True, slots=True)
class HeightProfilePoint:
    """
    Punkt i höjdprofilen.

    Parameters
    ----------
    distance_m : float
        Kumulativt avstånd längs korridoren.
    elevation_m : float
        Höjd i meter.
    source : str
        Datakälla för punkten.
    description : str
        Kort beskrivning av punktens ursprung.
    """

    distance_m: float
    elevation_m: float
    source: str
    description: str


@dataclass(frozen=True, slots=True)
class HeightProfileResult:
    """
    Resultat från första höjdprofil längs en korridor.

    Parameters
    ----------
    route_length_m : float
        Total ruttlängd.
    points : list[HeightProfilePoint]
        Profilpunkter längs rutten.
    notes : str
        Kommentar om profilens kvalitet.
    """

    route_length_m: float
    points: list[HeightProfilePoint]
    notes: str


class HeightProfileBuilder:
    """
    Bygger en första höjdprofil längs en traverserad korridor.

    Första versionen använder `BIS_DK_O_4015_Lutning` och väljer objekt vars
    start/slutpunkter ligger nära den traverserade korridoren.

    Parameters
    ----------
    resolver : NetJvgResolver
        Resolver med åtkomst till masterdata.
    """

    LUTNING_TABLE = "BIS_DK_O_4015_Lutning"

    def __init__(self, resolver: NetJvgResolver) -> None:
        """
        Initierar höjdprofilbyggaren.

        Parameters
        ----------
        resolver : NetJvgResolver
            Resolver med åtkomst till masterdata.
        """
        self.resolver = resolver
        self.inspector = GeoPackageInspector(resolver.gpkg.gpkg_path)

    @classmethod
    def from_config_file(cls, config_path: str = "config.json") -> "HeightProfileBuilder":
        """
        Skapar instans från konfigurationsfil.

        Parameters
        ----------
        config_path : str, optional
            Sökväg till konfigurationsfil.

        Returns
        -------
        HeightProfileBuilder
            Färdig instans.
        """
        return cls(NetJvgResolver.from_config_file(config_path))

    def _parse_point_xyz(self, value: str | None) -> tuple[float, float, float] | None:
        """
        Tolkar XYZ ur SRID/POINT-text.

        Parameters
        ----------
        value : str | None
            Text med SRID=3006;POINT(...).

        Returns
        -------
        tuple[float, float, float] | None
            Easting, northing och höjd.
        """
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

    def _route_vertices(self, traversal: TraversalResult) -> list[tuple[float, float, float]]:
        """
        Hämtar sammanhängande vertexlista för traverserad korridor.

        Parameters
        ----------
        traversal : TraversalResult
            Traverserad rutt.

        Returns
        -------
        list[tuple[float, float, float]]
            Korridorens vertexer med kumulativt avstånd.
        """
        link_id_to_index = {link_id: index for index, link_id in enumerate(traversal.traversed_link_ids)}
        rows = self.resolver.gpkg.fetch_rows(
            "Net_JVG_Link",
            limit=self.resolver.gpkg.count_rows("Net_JVG_Link"),
            columns=["id", "geom", "START_NODE_OID", "END_NODE_OID"],
        )
        ordered = []
        for row in rows:
            link_id = int(row["id"])
            if link_id not in link_id_to_index:
                continue
            vertices = self.resolver._decode_link_vertices(row["geom"])
            if len(vertices) < 2:
                continue
            sequence_index = link_id_to_index[link_id]
            start_node_oid = traversal.traversed_node_oids[sequence_index]
            end_node_oid = traversal.traversed_node_oids[sequence_index + 1]
            if start_node_oid == str(row["END_NODE_OID"]) and end_node_oid == str(row["START_NODE_OID"]):
                vertices.reverse()
            ordered.append((sequence_index, vertices))
        ordered.sort(key=lambda item: item[0])

        route_vertices: list[tuple[float, float, float]] = []
        distance_m = 0.0
        previous_xy: tuple[float, float] | None = None
        for _, vertices in ordered:
            for vertex_index, (x, y) in enumerate(vertices):
                current_xy = (x, y)
                if previous_xy is not None:
                    distance_m += math.hypot(current_xy[0] - previous_xy[0], current_xy[1] - previous_xy[1])
                if route_vertices and vertex_index == 0 and current_xy == previous_xy:
                    previous_xy = current_xy
                    continue
                route_vertices.append((x, y, distance_m))
                previous_xy = current_xy
        return route_vertices

    def _nearest_route_distance(self, point_xy: tuple[float, float], route_vertices: list[tuple[float, float, float]]) -> tuple[float, float]:
        """
        Hittar närmaste profildistans till en punkt.

        Parameters
        ----------
        point_xy : tuple[float, float]
            Punkt i SWEREF 99 TM.
        route_vertices : list[tuple[float, float, float]]
            Korridorens vertexer med kumulativt avstånd.

        Returns
        -------
        tuple[float, float]
            Minsta avstånd till korridoren och korridordistans vid närmaste vertex.
        """
        best_distance = float("inf")
        best_route_distance = 0.0
        for x, y, route_distance in route_vertices:
            distance = math.hypot(point_xy[0] - x, point_xy[1] - y)
            if distance < best_distance:
                best_distance = distance
                best_route_distance = route_distance
        return best_distance, best_route_distance

    def build_from_traversal(self, traversal: TraversalResult, max_offset_m: float = 150.0) -> HeightProfileResult:
        """
        Bygger första höjdprofil från traverserad rutt.

        Parameters
        ----------
        traversal : TraversalResult
            Traverserad rutt.
        max_offset_m : float, optional
            Max tillåtet sidavstånd från korridoren för att ta med lutningsobjekt.

        Returns
        -------
        HeightProfileResult
            Första höjdprofilresultatet.
        """
        route_vertices = self._route_vertices(traversal)
        if not route_vertices:
            raise HeightProfileError("No route vertices found for traversal")

        xs = [vertex[0] for vertex in route_vertices]
        ys = [vertex[1] for vertex in route_vertices]
        candidate_ids = set(
            self.inspector.rtree_window_query(
                table_name=self.LUTNING_TABLE,
                minx=min(xs) - max_offset_m,
                maxx=max(xs) + max_offset_m,
                miny=min(ys) - max_offset_m,
                maxy=max(ys) + max_offset_m,
                limit=50000,
            )
        )

        rows = self.resolver.gpkg.fetch_rows(
            self.LUTNING_TABLE,
            limit=self.resolver.gpkg.count_rows(self.LUTNING_TABLE),
            columns=["id", "Koordinater_start", "Koordinater_slut", "Lutning_promille", "Langd_m", "Kmtal", "Kmtalti"],
        )

        points: list[HeightProfilePoint] = []
        for row in rows:
            if int(row["id"]) not in candidate_ids:
                continue
            start_xyz = self._parse_point_xyz(row.get("Koordinater_start"))
            end_xyz = self._parse_point_xyz(row.get("Koordinater_slut"))
            if start_xyz is None or end_xyz is None:
                continue

            start_offset_m, start_distance_m = self._nearest_route_distance((start_xyz[0], start_xyz[1]), route_vertices)
            end_offset_m, end_distance_m = self._nearest_route_distance((end_xyz[0], end_xyz[1]), route_vertices)
            if max(start_offset_m, end_offset_m) > max_offset_m:
                continue

            description = (
                f"Lutning {row.get('Lutning_promille')}‰ "
                f"{row.get('Kmtal')}->{row.get('Kmtalti')} "
                f"längd {row.get('Langd_m')} m"
            )
            points.append(
                HeightProfilePoint(
                    distance_m=start_distance_m,
                    elevation_m=start_xyz[2],
                    source="lutning_start",
                    description=description,
                )
            )
            points.append(
                HeightProfilePoint(
                    distance_m=end_distance_m,
                    elevation_m=end_xyz[2],
                    source="lutning_end",
                    description=description,
                )
            )

        points.sort(key=lambda item: item.distance_m)
        deduplicated: list[HeightProfilePoint] = []
        for point in points:
            if deduplicated and abs(deduplicated[-1].distance_m - point.distance_m) < 1.0 and abs(deduplicated[-1].elevation_m - point.elevation_m) < 0.01:
                continue
            deduplicated.append(point)

        return HeightProfileResult(
            route_length_m=route_vertices[-1][2],
            points=deduplicated,
            notes=(
                "Första profilversion från BIS_DK_O_4015_Lutning, projekterad mot level1-korridoren via närmaste ruttvertex."
            ),
        )
