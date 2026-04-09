from __future__ import annotations

import math
from dataclasses import dataclass

import networkx as nx
from shapely.geometry import Point
from shapely.strtree import STRtree

from .config_loader import load_config
from .geopackage_geometry import line_vertices_xy, point_xy
from .trafikverket_gpkg import TrafikverketGeoPackage


class RailGraphError(Exception):
    """Basundantag för grafmodell av järnvägsnätet."""


@dataclass(frozen=True, slots=True)
class RailGraphPath:
    """
    Sammanfattning av väg genom järnvägsgrafen.

    Parameters
    ----------
    start_node_oid : str
        Startnodens OID.
    end_node_oid : str
        Slutnodens OID.
    node_oids : list[str]
        Nodföljd längs vägen.
    link_ids : list[int]
        Länk-id:n längs vägen.
    total_length_m : float
        Total länklängd i meter.
    total_cost : float
        Total viktad kostnad i grafen.
    """

    start_node_oid: str
    end_node_oid: str
    node_oids: list[str]
    link_ids: list[int]
    total_length_m: float
    total_cost: float


@dataclass(frozen=True, slots=True)
class RepairGraphSummary:
    """
    Sammanfattning av reparerad graf.

    Parameters
    ----------
    snapped_start_endpoints : int
        Antal saknade startändpunkter som kunnat snappas mot existerande nod.
    snapped_end_endpoints : int
        Antal saknade slutändpunkter som kunnat snappas mot existerande nod.
    synthetic_nodes_created : int
        Antal syntetiska noder som skapats från geometriändpunkter.
    missing_links_after_repair : int
        Antal länkar som fortfarande inte kunde föras in i grafen.
    """

    snapped_start_endpoints: int
    snapped_end_endpoints: int
    synthetic_nodes_created: int
    missing_links_after_repair: int


class RailGraph:
    """
    NetworkX-baserad grafmodell för Trafikverkets Net_JVG-nät.

    Grafen håller isär topologi och geometri. Noder representerar
    `Net_JVG_Node` och kanter representerar `Net_JVG_Link`.

    Parameters
    ----------
    gpkg : TrafikverketGeoPackage
        GeoPackage-läsare riktad mot masterfilen.
    """

    def __init__(self, gpkg: TrafikverketGeoPackage) -> None:
        """
        Initierar grafmodellen.

        Parameters
        ----------
        gpkg : TrafikverketGeoPackage
            GeoPackage-läsare riktad mot masterfilen.
        """
        self.gpkg = gpkg
        self.graph = nx.Graph()
        self.repair_summary: RepairGraphSummary | None = None

    @classmethod
    def from_config_file(cls, config_path: str = "config.json") -> "RailGraph":
        """
        Skapar grafmodell från konfigurationsfil.

        Parameters
        ----------
        config_path : str, optional
            Sökväg till konfigurationsfil.

        Returns
        -------
        RailGraph
            Färdig grafmodell.
        """
        config = load_config(config_path)
        gpkg_path = config.get("trafikverket_gpkg_path")
        if not gpkg_path:
            raise RailGraphError("Config is missing trafikverket_gpkg_path")
        graph = cls(gpkg=TrafikverketGeoPackage(gpkg_path))
        graph.build()
        return graph

    def _decode_node_xy(self, geom: bytes | None) -> tuple[float, float] | None:
        """
        Dekodar nodpunkt från GeoPackage-geometri.

        Parameters
        ----------
        geom : bytes | None
            Binär punktgeometri.

        Returns
        -------
        tuple[float, float] | None
            Easting och northing i SWEREF 99 TM.
        """
        return point_xy(geom)

    def _decode_link_vertices(self, geom: bytes | None) -> list[tuple[float, float]]:
        """
        Dekodar vertexlista från länkgeometri.

        Parameters
        ----------
        geom : bytes | None
            Binär linjegeometri.

        Returns
        -------
        list[tuple[float, float]]
            Vertexlista i SWEREF 99 TM.
        """
        return line_vertices_xy(geom)

    def build(self, repair_missing_nodes: bool = False, snap_tolerance_m: float = 25.0) -> None:
        """
        Bygger graf från `Net_JVG_Node` och `Net_JVG_Link`.

        Parameters
        ----------
        repair_missing_nodes : bool, optional
            Om `True` försöker grafen reparera länkar med saknade noder genom
            snapping eller syntetiska noder från geometriändpunkter.
        snap_tolerance_m : float, optional
            Maxavstånd i meter för snapping av geometriändpunkt mot existerande nod.

        Returns
        -------
        None
            Uppdaterar `self.graph` in-place.
        """
        self.graph.clear()
        self.repair_summary = None

        node_rows = self.gpkg.fetch_rows(
            "Net_JVG_Node",
            limit=self.gpkg.count_rows("Net_JVG_Node"),
            columns=["OID", "geom"],
        )
        for row in node_rows:
            point = self._decode_node_xy(row["geom"])
            if point is None:
                continue
            easting, northing = point
            self.graph.add_node(
                str(row["OID"]),
                easting=easting,
                northing=northing,
                synthetic=False,
            )

        link_rows = self.gpkg.fetch_rows(
            "Net_JVG_Link",
            limit=self.gpkg.count_rows("Net_JVG_Link"),
            columns=[
                "id",
                "geom",
                "LINKSEQUENCE_OID",
                "START_NODE_OID",
                "END_NODE_OID",
                "START_MEASURE",
                "END_MEASURE",
                "LENGTH",
                "EXTENT_LENGTH",
            ],
        )

        synthetic_node_counter = 0
        snapped_start_endpoints = 0
        snapped_end_endpoints = 0
        missing_node_link_count = 0

        def nearest_existing_node(point_xy: tuple[float, float]) -> tuple[str, float] | None:
            point = Point(point_xy[0], point_xy[1])
            current_node_ids = list(self.graph.nodes)
            current_points = [
                Point(self.graph.nodes[node_oid]["easting"], self.graph.nodes[node_oid]["northing"])
                for node_oid in current_node_ids
            ]
            point_index = STRtree(current_points)
            nearest_index = point_index.nearest(point)
            if nearest_index is None:
                return None
            nearest_point = current_points[int(nearest_index)]
            nearest_node_oid = current_node_ids[int(nearest_index)]
            return nearest_node_oid, point.distance(nearest_point)

        def resolve_endpoint(node_oid: str, fallback_point: tuple[float, float], endpoint_role: str) -> str:
            nonlocal synthetic_node_counter, snapped_start_endpoints, snapped_end_endpoints
            if node_oid in self.graph:
                return node_oid
            if repair_missing_nodes:
                nearest = nearest_existing_node(fallback_point)
                if nearest is not None:
                    nearest_node_oid, nearest_distance = nearest
                    if nearest_distance <= snap_tolerance_m:
                        if endpoint_role == "start":
                            snapped_start_endpoints += 1
                        else:
                            snapped_end_endpoints += 1
                        return nearest_node_oid

                synthetic_node_counter += 1
                synthetic_node_oid = f"synthetic:{synthetic_node_counter}"
                self.graph.add_node(
                    synthetic_node_oid,
                    easting=fallback_point[0],
                    northing=fallback_point[1],
                    synthetic=True,
                )
                return synthetic_node_oid
            raise RailGraphError(f"Link endpoint node is missing from graph: {node_oid}")

        for row in link_rows:
            vertices = self._decode_link_vertices(row.get("geom"))
            if len(vertices) < 2:
                continue
            start_node_oid = str(row["START_NODE_OID"])
            end_node_oid = str(row["END_NODE_OID"])
            if start_node_oid not in self.graph or end_node_oid not in self.graph:
                if not repair_missing_nodes:
                    missing_node_link_count += 1
                    continue
                start_node_oid = resolve_endpoint(start_node_oid, vertices[0], "start")
                end_node_oid = resolve_endpoint(end_node_oid, vertices[-1], "end")
            self.graph.add_edge(
                start_node_oid,
                end_node_oid,
                link_id=int(row["id"]),
                linksequence_oid=str(row["LINKSEQUENCE_OID"]),
                start_measure=float(row["START_MEASURE"]),
                end_measure=float(row["END_MEASURE"]),
                length=float(row["LENGTH"]),
                extent_length=float(row["EXTENT_LENGTH"]),
                vertices=vertices,
            )

        self.graph.graph["missing_node_link_count"] = missing_node_link_count
        if repair_missing_nodes:
            self.repair_summary = RepairGraphSummary(
                snapped_start_endpoints=snapped_start_endpoints,
                snapped_end_endpoints=snapped_end_endpoints,
                synthetic_nodes_created=synthetic_node_counter,
                missing_links_after_repair=missing_node_link_count,
            )

    def nearest_node(self, easting: float, northing: float) -> tuple[str, float]:
        """
        Returnerar närmaste nod till en SWEREF-punkt.

        Parameters
        ----------
        easting : float
            Easting i SWEREF 99 TM.
        northing : float
            Northing i SWEREF 99 TM.

        Returns
        -------
        tuple[str, float]
            Nod-OID och avstånd i meter.
        """
        best_node_oid: str | None = None
        best_distance = float("inf")
        for node_oid, data in self.graph.nodes(data=True):
            distance_m = math.hypot(data["easting"] - easting, data["northing"] - northing)
            if distance_m < best_distance:
                best_distance = distance_m
                best_node_oid = node_oid
        if best_node_oid is None:
            raise RailGraphError("Graph has no nodes")
        return best_node_oid, best_distance

    def shortest_path(self, start_node_oid: str, end_node_oid: str, weight: str = "length") -> RailGraphPath:
        """
        Beräknar kortaste väg mellan två noder i grafen.

        Parameters
        ----------
        start_node_oid : str
            Startnodens OID.
        end_node_oid : str
            Slutnodens OID.
        weight : str, optional
            Kantattribut som ska användas som vikt.

        Returns
        -------
        RailGraphPath
            Summering av vägen genom grafen.
        """
        if start_node_oid not in self.graph:
            raise RailGraphError(f"Unknown start node: {start_node_oid}")
        if end_node_oid not in self.graph:
            raise RailGraphError(f"Unknown end node: {end_node_oid}")

        node_path = nx.shortest_path(self.graph, start_node_oid, end_node_oid, weight=weight)
        total_cost = nx.shortest_path_length(self.graph, start_node_oid, end_node_oid, weight=weight)

        link_ids: list[int] = []
        total_length_m = 0.0
        for from_node_oid, to_node_oid in zip(node_path[:-1], node_path[1:]):
            edge = self.graph[from_node_oid][to_node_oid]
            link_ids.append(int(edge["link_id"]))
            total_length_m += float(edge["length"])

        return RailGraphPath(
            start_node_oid=start_node_oid,
            end_node_oid=end_node_oid,
            node_oids=node_path,
            link_ids=link_ids,
            total_length_m=total_length_m,
            total_cost=float(total_cost),
        )

    def summary(self) -> dict[str, int]:
        """
        Returnerar enkel sammanfattning av grafen.

        Returns
        -------
        dict[str, int]
            Antal noder, kanter, komponenter och länkar med saknade noder.
        """
        summary = {
            "node_count": self.graph.number_of_nodes(),
            "edge_count": self.graph.number_of_edges(),
            "connected_components": nx.number_connected_components(self.graph),
            "missing_node_link_count": int(self.graph.graph.get("missing_node_link_count", 0)),
        }
        if self.repair_summary is not None:
            summary.update(
                {
                    "snapped_start_endpoints": self.repair_summary.snapped_start_endpoints,
                    "snapped_end_endpoints": self.repair_summary.snapped_end_endpoints,
                    "synthetic_nodes_created": self.repair_summary.synthetic_nodes_created,
                    "missing_links_after_repair": self.repair_summary.missing_links_after_repair,
                }
            )
        return summary

    def connected_component_size(self, node_oid: str) -> int:
        """
        Returnerar storlek på komponenten som innehåller en nod.

        Parameters
        ----------
        node_oid : str
            Nodens OID.

        Returns
        -------
        int
            Antal noder i komponenten.
        """
        if node_oid not in self.graph:
            raise RailGraphError(f"Unknown node: {node_oid}")
        return len(nx.node_connected_component(self.graph, node_oid))
