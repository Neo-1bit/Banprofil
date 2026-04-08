from __future__ import annotations

import heapq
import math
import struct
from collections import defaultdict
from dataclasses import dataclass
from typing import Any

from .config_loader import load_config
from .trafikverket_gpkg import TrafikverketGeoPackage


class NetJvgResolverError(Exception):
    """Basundantag för Net_JVG-resolver."""


@dataclass(frozen=True, slots=True)
class NetJvgNode:
    """
    Representerar en nod i Trafikverkets järnvägsnät.

    Parameters
    ----------
    oid : str
        Nodens OID.
    easting : float | None
        Nodens easting i SWEREF 99 TM när geometri lästs in.
    northing : float | None
        Nodens northing i SWEREF 99 TM när geometri lästs in.
    """

    oid: str
    easting: float | None = None
    northing: float | None = None


@dataclass(frozen=True, slots=True)
class NetJvgLink:
    """
    Representerar en länk i Trafikverkets järnvägsnät.

    Parameters
    ----------
    id : int
        Internt rad-id.
    linksequence_oid : str
        Referens till länksekvens.
    start_node_oid : str
        Startnodens OID.
    end_node_oid : str
        Slutnodens OID.
    length : float
        Längd i meter.
    extent_length : float
        Utbredningslängd i meter.
    geom : bytes | None
        GeoPackage-geometri för länken.
    """

    id: int
    linksequence_oid: str
    start_node_oid: str
    end_node_oid: str
    length: float
    extent_length: float
    geom: bytes | None = None


@dataclass(frozen=True, slots=True)
class NetJvgLinkSequence:
    """
    Representerar en länksekvens i Trafikverkets järnvägsnät.

    Parameters
    ----------
    oid : str
        Sekvensens OID.
    length : float
        Längd i meter.
    extent_length : float
        Utbredningslängd i meter.
    """

    oid: str
    length: float
    extent_length: float


@dataclass(frozen=True, slots=True)
class NetJvgNetworkSummary:
    """
    Sammanfattar ett topologiskt nätverk.

    Parameters
    ----------
    node_count : int
        Antal noder.
    link_count : int
        Antal länkar.
    linksequence_count : int
        Antal länksekvenser.
    connected_component_sizes : list[int]
        Storlek på de största komponenterna.
    notes : str
        Kort kommentar om nätverkets struktur.
    """

    node_count: int
    link_count: int
    linksequence_count: int
    connected_component_sizes: list[int]
    notes: str


@dataclass(frozen=True, slots=True)
class TraversalResult:
    """
    Resultat från en enkel nätverkstraversering.

    Parameters
    ----------
    start_node_oid : str
        Startnod för traverseringen.
    target_length_m : float
        Önskad traverseringslängd.
    visited_node_count : int
        Antal besökta noder.
    visited_link_count : int
        Antal traverserade länkar.
    accumulated_length_m : float
        Ackumulerad längd i meter.
    traversed_link_ids : list[int]
        Länk-id:n i traverserad ordning.
    traversed_node_oids : list[str]
        Nod-OID:n i den ordning traverseringen följde dem.
    notes : str
        Kommentar om traversalens karaktär.
    """

    start_node_oid: str
    target_length_m: float
    visited_node_count: int
    visited_link_count: int
    accumulated_length_m: float
    traversed_link_ids: list[int]
    traversed_node_oids: list[str]
    notes: str


@dataclass(frozen=True, slots=True)
class PointToNodeMatch:
    """
    Matchning mellan referenspunkt och närmaste Net_JVG-nod.

    Parameters
    ----------
    node_oid : str
        Matchad nod.
    easting : float
        Nodens easting i SWEREF 99 TM.
    northing : float
        Nodens northing i SWEREF 99 TM.
    distance_m : float
        Avstånd från referenspunkten till noden i meter.
    """

    node_oid: str
    easting: float
    northing: float
    distance_m: float


class NetJvgResolver:
    """
    Första nätverksförst-resolvern för Trafikverkets `Net_JVG_*`-lager.

    Den här resolvern etablerar nätverkets topologi som projektets ryggrad.

    Parameters
    ----------
    gpkg : TrafikverketGeoPackage
        GeoPackage-läsare riktad mot masterfilen.
    """

    def __init__(self, gpkg: TrafikverketGeoPackage) -> None:
        """
        Initierar resolvern.

        Parameters
        ----------
        gpkg : TrafikverketGeoPackage
            GeoPackage-läsare riktad mot masterfilen.
        """
        self.gpkg = gpkg

    @classmethod
    def from_config_file(cls, config_path: str = "config.json") -> "NetJvgResolver":
        """
        Skapar resolvern från konfigurationsfil.

        Parameters
        ----------
        config_path : str, optional
            Sökväg till konfigurationsfil.

        Returns
        -------
        NetJvgResolver
            Färdig resolver-instans.
        """
        config = load_config(config_path)
        gpkg_path = config.get("trafikverket_gpkg_path")
        if not gpkg_path:
            raise NetJvgResolverError("Config is missing trafikverket_gpkg_path")
        return cls(TrafikverketGeoPackage(gpkg_path))

    def _decode_node_xy(self, geom: bytes | None) -> tuple[float, float] | None:
        """
        Dekodar nodpunkt ur GeoPackage-geometri.

        Parameters
        ----------
        geom : bytes | None
            Binär GeoPackage-geometri.

        Returns
        -------
        tuple[float, float] | None
            Easting och northing i SWEREF 99 TM, eller `None` om tolkning misslyckas.
        """
        if not isinstance(geom, bytes) or len(geom) < 29:
            return None
        return (
            struct.unpack('<d', geom[13:21])[0],
            struct.unpack('<d', geom[21:29])[0],
        )

    def load_nodes(self, limit: int | None = None, include_geom: bool = False) -> list[NetJvgNode]:
        """
        Läser noder från `Net_JVG_Node`.

        Parameters
        ----------
        limit : int | None, optional
            Max antal noder att läsa. `None` läser alla.
        include_geom : bool, optional
            Om `True` dekodas nodernas SWEREF-position.

        Returns
        -------
        list[NetJvgNode]
            Noder i nätverket.
        """
        row_limit = limit if limit is not None else self.gpkg.count_rows("Net_JVG_Node")
        columns = ["OID"]
        if include_geom:
            columns.append("geom")
        rows = self.gpkg.fetch_rows("Net_JVG_Node", limit=row_limit, columns=columns)
        nodes: list[NetJvgNode] = []
        for row in rows:
            easting = None
            northing = None
            if include_geom:
                point = self._decode_node_xy(row.get("geom"))
                if point is not None:
                    easting, northing = point
            nodes.append(NetJvgNode(oid=str(row["OID"]), easting=easting, northing=northing))
        return nodes

    def load_links(self, limit: int | None = None, include_geom: bool = False) -> list[NetJvgLink]:
        """
        Läser länkar från `Net_JVG_Link`.

        Parameters
        ----------
        limit : int | None, optional
            Max antal länkar att läsa. `None` läser alla.
        include_geom : bool, optional
            Om `True` inkluderas geometri i resultatet.

        Returns
        -------
        list[NetJvgLink]
            Länkar i nätverket.
        """
        row_limit = limit if limit is not None else self.gpkg.count_rows("Net_JVG_Link")
        columns = [
            "id",
            "LINKSEQUENCE_OID",
            "START_NODE_OID",
            "END_NODE_OID",
            "LENGTH",
            "EXTENT_LENGTH",
        ]
        if include_geom:
            columns.append("geom")
        rows = self.gpkg.fetch_rows("Net_JVG_Link", limit=row_limit, columns=columns)
        return [
            NetJvgLink(
                id=int(row["id"]),
                linksequence_oid=str(row["LINKSEQUENCE_OID"]),
                start_node_oid=str(row["START_NODE_OID"]),
                end_node_oid=str(row["END_NODE_OID"]),
                length=float(row["LENGTH"]),
                extent_length=float(row["EXTENT_LENGTH"]),
                geom=row.get("geom"),
            )
            for row in rows
        ]

    def load_link_sequences(self, limit: int | None = None) -> list[NetJvgLinkSequence]:
        """
        Läser länksekvenser från `Net_JVG_LinkSequence`.

        Parameters
        ----------
        limit : int | None, optional
            Max antal sekvenser att läsa. `None` läser alla.

        Returns
        -------
        list[NetJvgLinkSequence]
            Länksekvenser i nätverket.
        """
        row_limit = limit if limit is not None else self.gpkg.count_rows("Net_JVG_LinkSequence")
        rows = self.gpkg.fetch_rows(
            "Net_JVG_LinkSequence",
            limit=row_limit,
            columns=["OID", "LENGTH", "EXTENT_LENGTH"],
        )
        return [
            NetJvgLinkSequence(
                oid=str(row["OID"]),
                length=float(row["LENGTH"]),
                extent_length=float(row["EXTENT_LENGTH"]),
            )
            for row in rows
        ]

    def _link_direction(self, link: NetJvgLink, from_node_oid: str) -> tuple[float, float]:
        """
        Beräknar ungefärlig riktning för en länk från en viss nod.

        Parameters
        ----------
        link : NetJvgLink
            Länk som ska bedömas.
        from_node_oid : str
            Nod som traversaln kommer från.

        Returns
        -------
        tuple[float, float]
            Normaliserad riktningsvektor.
        """
        if not link.geom or len(link.geom) < 40:
            return (0.0, 0.0)
        minx, maxx, miny, maxy = struct.unpack('<dddd', link.geom[8:40])
        if from_node_oid == link.start_node_oid:
            dx = maxx - minx
            dy = maxy - miny
        else:
            dx = minx - maxx
            dy = miny - maxy
        length = math.hypot(dx, dy)
        if length == 0:
            return (0.0, 0.0)
        return (dx / length, dy / length)

    def summarize_network(self, limit_links: int | None = 5000) -> NetJvgNetworkSummary:
        """
        Sammanfattar topologin i `Net_JVG`.

        Parameters
        ----------
        limit_links : int | None, optional
            Antal länkar att använda i första sammanfattningen.

        Returns
        -------
        NetJvgNetworkSummary
            Summering av noder, länkar, sekvenser och komponentstorlekar.
        """
        links = self.load_links(limit=limit_links)
        nodes = self.load_nodes(limit=None)
        sequences = self.load_link_sequences(limit=None)

        adjacency: dict[str, set[str]] = defaultdict(set)
        for link in links:
            adjacency[link.start_node_oid].add(link.end_node_oid)
            adjacency[link.end_node_oid].add(link.start_node_oid)

        visited: set[str] = set()
        component_sizes: list[int] = []
        for node in adjacency:
            if node in visited:
                continue
            stack = [node]
            size = 0
            while stack:
                current = stack.pop()
                if current in visited:
                    continue
                visited.add(current)
                size += 1
                stack.extend(neighbor for neighbor in adjacency[current] if neighbor not in visited)
            component_sizes.append(size)

        component_sizes.sort(reverse=True)
        return NetJvgNetworkSummary(
            node_count=len(nodes),
            link_count=len(links),
            linksequence_count=len(sequences),
            connected_component_sizes=component_sizes[:10],
            notes="Första sammanfattning av Net_JVG-nätet. Nästa steg är att följa länksekvenser och koppla features ovanpå nätverket.",
        )

    def traverse_from_node(self, start_node_oid: str, target_length_m: float = 50000.0, limit_links: int | None = 20000) -> TraversalResult:
        """
        Traverserar nätverket framåt från en startnod tills önskad längd uppnåtts.

        Traversal v2 försöker hålla riktning genom att välja nästa länk som bäst
        fortsätter föregående riktning och undviker att svälla ut i sidogrenar.

        Parameters
        ----------
        start_node_oid : str
            Startnodens OID.
        target_length_m : float, optional
            Mållängd i meter.
        limit_links : int | None, optional
            Max antal länkar att läsa för traversal.

        Returns
        -------
        TraversalResult
            Resultat från traverseringen.

        Raises
        ------
        NetJvgResolverError
            Om startnoden inte finns i den lästa grafen.
        """
        links = self.load_links(limit=limit_links, include_geom=True)
        adjacency: dict[str, list[tuple[str, NetJvgLink]]] = defaultdict(list)
        for link in links:
            adjacency[link.start_node_oid].append((link.end_node_oid, link))
            adjacency[link.end_node_oid].append((link.start_node_oid, link))

        if start_node_oid not in adjacency:
            raise NetJvgResolverError(f"Start node not found in traversal graph: {start_node_oid}")

        visited_nodes: set[str] = {start_node_oid}
        visited_links: set[int] = set()
        traversed_link_ids: list[int] = []
        traversed_node_oids: list[str] = [start_node_oid]
        accumulated = 0.0
        current_node = start_node_oid
        previous_direction: tuple[float, float] | None = None

        while accumulated < target_length_m:
            candidates = []
            for neighbor, link in adjacency[current_node]:
                if link.id in visited_links:
                    continue
                direction = self._link_direction(link, current_node)
                score = link.length
                if previous_direction is not None:
                    score += 1000.0 * (previous_direction[0] * direction[0] + previous_direction[1] * direction[1])
                candidates.append((score, neighbor, link, direction))

            if not candidates:
                break

            candidates.sort(key=lambda item: item[0], reverse=True)
            _, next_node, best_link, best_direction = candidates[0]
            visited_links.add(best_link.id)
            traversed_link_ids.append(best_link.id)
            accumulated += best_link.length
            current_node = next_node
            traversed_node_oids.append(current_node)
            visited_nodes.add(current_node)
            previous_direction = best_direction

        return TraversalResult(
            start_node_oid=start_node_oid,
            target_length_m=target_length_m,
            visited_node_count=len(visited_nodes),
            visited_link_count=len(visited_links),
            accumulated_length_m=accumulated,
            traversed_link_ids=traversed_link_ids,
            traversed_node_oids=traversed_node_oids,
            notes="Traversal v2 använder enkel riktningskontinuitet för att följa huvudkorridoren och undvika grenar.",
        )

    def match_reference_point_to_node(self, easting: float, northing: float) -> PointToNodeMatch:
        """
        Matchar en SWEREF-referenspunkt till närmaste Net_JVG-nod.

        Parameters
        ----------
        easting : float
            Easting i SWEREF 99 TM.
        northing : float
            Northing i SWEREF 99 TM.

        Returns
        -------
        PointToNodeMatch
            Närmaste nod och avstånd till referenspunkten.
        """
        nodes = self.load_nodes(limit=None, include_geom=True)
        best_match: PointToNodeMatch | None = None
        for node in nodes:
            if node.easting is None or node.northing is None:
                continue
            distance_m = math.hypot(node.easting - easting, node.northing - northing)
            if best_match is None or distance_m < best_match.distance_m:
                best_match = PointToNodeMatch(
                    node_oid=node.oid,
                    easting=node.easting,
                    northing=node.northing,
                    distance_m=distance_m,
                )
        if best_match is None:
            raise NetJvgResolverError("Could not decode any Net_JVG node geometries")
        return best_match

    def route_between_nodes(
        self,
        start_node_oid: str,
        end_node_oid: str,
        limit_links: int | None = None,
    ) -> TraversalResult:
        """
        Beräknar kortaste väg i Net_JVG mellan två noder.

        Parameters
        ----------
        start_node_oid : str
            Startnodens OID.
        end_node_oid : str
            Slutnodens OID.
        limit_links : int | None, optional
            Max antal länkar att läsa. `None` läser alla.

        Returns
        -------
        TraversalResult
            Traversalresultat för rutten mellan noderna.

        Raises
        ------
        NetJvgResolverError
            Om någon nod saknas eller om ingen rutt hittas.
        """
        links = self.load_links(limit=limit_links, include_geom=True)
        adjacency: dict[str, list[tuple[str, NetJvgLink]]] = defaultdict(list)
        for link in links:
            adjacency[link.start_node_oid].append((link.end_node_oid, link))
            adjacency[link.end_node_oid].append((link.start_node_oid, link))

        if start_node_oid not in adjacency:
            raise NetJvgResolverError(f"Start node not found in graph: {start_node_oid}")
        if end_node_oid not in adjacency:
            raise NetJvgResolverError(f"End node not found in graph: {end_node_oid}")

        distances: dict[str, float] = {start_node_oid: 0.0}
        previous_nodes: dict[str, str] = {}
        previous_links: dict[str, int] = {}
        queue: list[tuple[float, str]] = [(0.0, start_node_oid)]
        visited: set[str] = set()

        while queue:
            distance_so_far, current_node_oid = heapq.heappop(queue)
            if current_node_oid in visited:
                continue
            visited.add(current_node_oid)
            if current_node_oid == end_node_oid:
                break
            for neighbor_oid, link in adjacency[current_node_oid]:
                new_distance = distance_so_far + link.length
                if new_distance >= distances.get(neighbor_oid, float('inf')):
                    continue
                distances[neighbor_oid] = new_distance
                previous_nodes[neighbor_oid] = current_node_oid
                previous_links[neighbor_oid] = link.id
                heapq.heappush(queue, (new_distance, neighbor_oid))

        if end_node_oid not in distances:
            raise NetJvgResolverError(
                f"No route found between Net_JVG nodes {start_node_oid} and {end_node_oid}"
            )

        traversed_node_oids: list[str] = [end_node_oid]
        traversed_link_ids: list[int] = []
        current_node_oid = end_node_oid
        while current_node_oid != start_node_oid:
            traversed_link_ids.append(previous_links[current_node_oid])
            current_node_oid = previous_nodes[current_node_oid]
            traversed_node_oids.append(current_node_oid)
        traversed_link_ids.reverse()
        traversed_node_oids.reverse()

        return TraversalResult(
            start_node_oid=start_node_oid,
            target_length_m=distances[end_node_oid],
            visited_node_count=len(traversed_node_oids),
            visited_link_count=len(traversed_link_ids),
            accumulated_length_m=distances[end_node_oid],
            traversed_link_ids=traversed_link_ids,
            traversed_node_oids=traversed_node_oids,
            notes=(
                "Point-to-point route i Net_JVG beräknad med kortaste väg mellan matchade referensnoder."
            ),
        )

    def recommend_next_steps(self) -> dict[str, Any]:
        """
        Returnerar rekommenderade fortsatta steg för nätverksförst-arkitekturen.

        Returns
        -------
        dict[str, Any]
            Rekommenderade nästa steg.
        """
        return {
            "network_backbone": ["Net_JVG_Node", "Net_JVG_Link", "Net_JVG_LinkSequence"],
            "next_steps": [
                "Bygg traversal längs sammanhängande länksekvenser.",
                "Identifiera hur features som Raklinje och Lutning projiceras onto Net_JVG.",
                "Använd bandel och längdmätningsdel som filter ovanpå nätverket, inte som ersättning för nätverket.",
            ],
        }
