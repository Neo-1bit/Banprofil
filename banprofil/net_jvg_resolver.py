from __future__ import annotations

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
    """

    oid: str


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
    """

    id: int
    linksequence_oid: str
    start_node_oid: str
    end_node_oid: str
    length: float
    extent_length: float


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
    notes : str
        Kommentar om traversalens karaktär.
    """

    start_node_oid: str
    target_length_m: float
    visited_node_count: int
    visited_link_count: int
    accumulated_length_m: float
    traversed_link_ids: list[int]
    notes: str


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

    def load_nodes(self, limit: int | None = None) -> list[NetJvgNode]:
        """
        Läser noder från `Net_JVG_Node`.

        Parameters
        ----------
        limit : int | None, optional
            Max antal noder att läsa. `None` läser alla.

        Returns
        -------
        list[NetJvgNode]
            Noder i nätverket.
        """
        row_limit = limit if limit is not None else self.gpkg.count_rows("Net_JVG_Node")
        rows = self.gpkg.fetch_rows("Net_JVG_Node", limit=row_limit, columns=["OID"])
        return [NetJvgNode(oid=str(row["OID"])) for row in rows]

    def load_links(self, limit: int | None = None) -> list[NetJvgLink]:
        """
        Läser länkar från `Net_JVG_Link`.

        Parameters
        ----------
        limit : int | None, optional
            Max antal länkar att läsa. `None` läser alla.

        Returns
        -------
        list[NetJvgLink]
            Länkar i nätverket.
        """
        row_limit = limit if limit is not None else self.gpkg.count_rows("Net_JVG_Link")
        rows = self.gpkg.fetch_rows(
            "Net_JVG_Link",
            limit=row_limit,
            columns=[
                "id",
                "LINKSEQUENCE_OID",
                "START_NODE_OID",
                "END_NODE_OID",
                "LENGTH",
                "EXTENT_LENGTH",
            ],
        )
        return [
            NetJvgLink(
                id=int(row["id"]),
                linksequence_oid=str(row["LINKSEQUENCE_OID"]),
                start_node_oid=str(row["START_NODE_OID"]),
                end_node_oid=str(row["END_NODE_OID"]),
                length=float(row["LENGTH"]),
                extent_length=float(row["EXTENT_LENGTH"]),
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

        Traverseringen använder en enkel grafgång över länkar och fungerar som
        första traversalprototyp, inte som slutlig ruttmotor.

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
        links = self.load_links(limit=limit_links)
        adjacency: dict[str, list[tuple[str, NetJvgLink]]] = defaultdict(list)
        for link in links:
            adjacency[link.start_node_oid].append((link.end_node_oid, link))
            adjacency[link.end_node_oid].append((link.start_node_oid, link))

        if start_node_oid not in adjacency:
            raise NetJvgResolverError(f"Start node not found in traversal graph: {start_node_oid}")

        visited_nodes: set[str] = set()
        visited_links: set[int] = set()
        traversed_link_ids: list[int] = []
        accumulated = 0.0
        stack = [start_node_oid]

        while stack and accumulated < target_length_m:
            current = stack.pop()
            if current in visited_nodes:
                continue
            visited_nodes.add(current)
            for neighbor, link in adjacency[current]:
                if link.id in visited_links:
                    continue
                visited_links.add(link.id)
                traversed_link_ids.append(link.id)
                accumulated += link.length
                if neighbor not in visited_nodes:
                    stack.append(neighbor)
                if accumulated >= target_length_m:
                    break

        return TraversalResult(
            start_node_oid=start_node_oid,
            target_length_m=target_length_m,
            visited_node_count=len(visited_nodes),
            visited_link_count=len(visited_links),
            accumulated_length_m=accumulated,
            traversed_link_ids=traversed_link_ids,
            notes="Traversal v1 använder enkel grafgång över länkar och är första steg mot sammanhängande nätverkskorridorer.",
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
