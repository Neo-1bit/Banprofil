from __future__ import annotations

import math
from dataclasses import dataclass

from .net_jvg_kml import _load_traversal_link_geometries, _sequence_traversal_vertices
from .net_jvg_resolver import NetJvgResolver, TraversalResult


class LocalGapRepairError(Exception):
    """Basundantag för lokal gap-reparation."""


@dataclass(frozen=True, slots=True)
class GapSegment:
    """
    Beskriver ett gap mellan två sekvenser.

    Parameters
    ----------
    from_sequence_index : int
        Index för sekvens före gapet.
    to_sequence_index : int
        Index för sekvens efter gapet.
    gap_m : float
        Euklidiskt avstånd mellan sekvensändpunkterna.
    from_point : tuple[float, float]
        Slutpunkt för föregående sekvens.
    to_point : tuple[float, float]
        Startpunkt för nästa sekvens.
    """

    from_sequence_index: int
    to_sequence_index: int
    gap_m: float
    from_point: tuple[float, float]
    to_point: tuple[float, float]


@dataclass(frozen=True, slots=True)
class LocalGapRepairResult:
    """
    Resultat från lokal gap-analys.

    Parameters
    ----------
    sequence_count : int
        Antal sekvenser före eventuell reparation.
    gaps : list[GapSegment]
        Identifierade gap mellan sekvenser.
    bridgable_gaps : list[GapSegment]
        Gap som bedömts som rimliga att försöka laga lokalt.
    """

    sequence_count: int
    gaps: list[GapSegment]
    bridgable_gaps: list[GapSegment]


class LocalGapRepair:
    """
    Analyserar lokala gap mellan redan giltiga ankarssegment.

    Fokus ligger på att identifiera kortare gap som bör gå att laga lokalt,
    i stället för att försöka lösa hela korridoren globalt i ett steg.

    Parameters
    ----------
    resolver : NetJvgResolver
        Resolver för Net_JVG-nätet.
    """

    def __init__(self, resolver: NetJvgResolver) -> None:
        """
        Initierar lokal gap-analys.

        Parameters
        ----------
        resolver : NetJvgResolver
            Resolver för Net_JVG-nätet.
        """
        self.resolver = resolver

    @classmethod
    def from_config_file(cls, config_path: str = "config.json") -> "LocalGapRepair":
        """
        Skapar instans från konfigurationsfil.

        Parameters
        ----------
        config_path : str, optional
            Sökväg till konfigurationsfil.

        Returns
        -------
        LocalGapRepair
            Färdig instans.
        """
        return cls(resolver=NetJvgResolver.from_config_file(config_path))

    def analyze_reference_route(
        self,
        point1_easting: float,
        point1_northing: float,
        point2_easting: float,
        point2_northing: float,
        sequence_gap_m: float = 500.0,
        max_bridgable_gap_m: float = 1000.0,
    ) -> LocalGapRepairResult:
        """
        Identifierar lokala gap på referensrutten mellan två SWEREF-punkter.

        Parameters
        ----------
        point1_easting : float
            Easting för första referenspunkten.
        point1_northing : float
            Northing för första referenspunkten.
        point2_easting : float
            Easting för andra referenspunkten.
        point2_northing : float
            Northing för andra referenspunkten.
        sequence_gap_m : float, optional
            Max gap som används när råa sekvenser bildas från traverserade länkar.
        max_bridgable_gap_m : float, optional
            Max gap som betraktas som lokal och rimlig att försöka laga.

        Returns
        -------
        LocalGapRepairResult
            Resultat med alla gap och de lokalt brobara gapen.
        """
        point1 = self.resolver.match_reference_point_to_node(point1_easting, point1_northing)
        point2 = self.resolver.match_reference_point_to_node(point2_easting, point2_northing)
        traversal = self.resolver.route_between_nodes_constrained(point1.node_oid, point2.node_oid)
        geometries = _load_traversal_link_geometries(self.resolver, traversal)
        sequences = _sequence_traversal_vertices(geometries, max_gap_m=sequence_gap_m)

        gaps: list[GapSegment] = []
        bridgable_gaps: list[GapSegment] = []
        for index in range(len(sequences) - 1):
            from_point = sequences[index][-1]
            to_point = sequences[index + 1][0]
            gap_m = math.hypot(from_point[0] - to_point[0], from_point[1] - to_point[1])
            gap = GapSegment(
                from_sequence_index=index + 1,
                to_sequence_index=index + 2,
                gap_m=gap_m,
                from_point=from_point,
                to_point=to_point,
            )
            gaps.append(gap)
            if gap_m <= max_bridgable_gap_m:
                bridgable_gaps.append(gap)

        return LocalGapRepairResult(
            sequence_count=len(sequences),
            gaps=gaps,
            bridgable_gaps=bridgable_gaps,
        )
