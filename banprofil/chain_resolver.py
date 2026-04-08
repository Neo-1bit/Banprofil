from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .chain_analysis import ChainAnalyzer
from .height_profile import HeightProfileBuilder, HeightSample, HeightSegment
from .master_network_analyzer import MasterNetworkAnalyzer
from .profile_chain import parse_km_string


class ChainResolverError(Exception):
    """Basundantag för kedjeresolver."""


@dataclass(frozen=True, slots=True)
class ResolvedChain:
    """
    Beskriver en vald kedja för ett km-intervall.

    Parameters
    ----------
    chain_key : str
        Identifierare för vald kedja.
    strategy : str
        Strategi eller heuristik som användes.
    notes : str
        Kommentar om hur kedjan valdes.
    sample_count : int
        Antal datapunkter som ingick i valet.
    filters : dict[str, Any]
        Filter eller överordnade nycklar som användes i valet.
    """

    chain_key: str
    strategy: str
    notes: str
    sample_count: int
    filters: dict[str, Any]


class ChainResolver:
    """
    Försöker välja en sammanhängande kedja för ett km-intervall.

    V4A använder geometrisk parent-matchning och en kompakthetsregel för att
    förbereda en bättre chain resolution innan full nätverksjoin implementeras.

    Parameters
    ----------
    analyzer : ChainAnalyzer
        Analysobjekt för Trafikverkets GeoPackage.
    profile_builder : HeightProfileBuilder
        Byggare för höjdprofiler.
    master_analyzer : MasterNetworkAnalyzer | None, optional
        Analyzer för masterpaketets nätverks- och parentlager.
    """

    def __init__(
        self,
        analyzer: ChainAnalyzer,
        profile_builder: HeightProfileBuilder,
        master_analyzer: MasterNetworkAnalyzer | None = None,
    ) -> None:
        """
        Initierar kedjeresolvern.

        Parameters
        ----------
        analyzer : ChainAnalyzer
            Analysobjekt för Trafikverkets GeoPackage.
        profile_builder : HeightProfileBuilder
            Byggare för höjdprofiler.
        master_analyzer : MasterNetworkAnalyzer | None, optional
            Analyzer för masterpaketets nätverks- och parentlager.
        """
        self.analyzer = analyzer
        self.profile_builder = profile_builder
        self.master_analyzer = master_analyzer

    @classmethod
    def from_config_file(cls, config_path: str = "config.json") -> "ChainResolver":
        """
        Skapar kedjeresolver från konfigurationsfil.

        Parameters
        ----------
        config_path : str, optional
            Sökväg till konfigurationsfil.

        Returns
        -------
        ChainResolver
            Färdig resolver-instans.
        """
        analyzer = ChainAnalyzer.from_config_file(config_path)
        profile_builder = HeightProfileBuilder.from_config_file(config_path)
        master_analyzer = MasterNetworkAnalyzer.from_config_file(config_path)
        return cls(analyzer=analyzer, profile_builder=profile_builder, master_analyzer=master_analyzer)

    def _compactness_metrics(self, samples: list[HeightSample]) -> dict[str, float]:
        """
        Beräknar enkel geografisk kompakthet för en profil.

        Parameters
        ----------
        samples : list[HeightSample]
            Höjdprofilpunkter.

        Returns
        -------
        dict[str, float]
            Spridningsmått i meter.
        """
        xs = [sample.e for sample in samples]
        ys = [sample.n for sample in samples]
        centroid_x = sum(xs) / len(xs)
        centroid_y = sum(ys) / len(ys)
        max_radius = max((((x - centroid_x) ** 2 + (y - centroid_y) ** 2) ** 0.5) for x, y in zip(xs, ys))
        bbox_diag = ((max(xs) - min(xs)) ** 2 + (max(ys) - min(ys)) ** 2) ** 0.5
        return {
            "centroid_x": centroid_x,
            "centroid_y": centroid_y,
            "max_radius_m": max_radius,
            "bbox_diagonal_m": bbox_diag,
        }

    def _infer_parent_filters(self, start_km: str, end_km: str, samples: list[HeightSample]) -> dict[str, Any]:
        """
        Härleder preliminära parent filters för kedjan.

        Parameters
        ----------
        start_km : str
            Start på intervallet.
        end_km : str
            Slut på intervallet.
        samples : list[HeightSample]
            Profilpunkter som ska användas för kompakthetsbedömning.

        Returns
        -------
        dict[str, Any]
            Parent filters och kompakthetsmått.
        """
        strategy = self.master_analyzer.recommend_chain_key_strategy() if self.master_analyzer else {}
        compactness = self._compactness_metrics(samples)
        return {
            "bandel": "geometric-bandel-candidate",
            "langdmatningsdel": "geometric-langdmatningsdel-candidate",
            "spar": "geometric-spar-candidate",
            "network_backbone": strategy.get("network_backbone", []),
            "km_interval": {"start": start_km, "end": end_km},
            "compactness": compactness,
            "compactness_rule": "A 50 km chain should stay within a geographically compact corridor and not fragment into distant clusters.",
        }

    def resolve_chain(self, start_km: str, end_km: str) -> ResolvedChain:
        """
        Väljer en kedjekandidat för km-intervallet.

        Parameters
        ----------
        start_km : str
            Start på intervallet.
        end_km : str
            Slut på intervallet.

        Returns
        -------
        ResolvedChain
            Beskrivning av vald kedja.

        Raises
        ------
        ChainResolverError
            Om inga profilerade punkter hittas för intervallet.
        """
        profile = self.profile_builder.build_height_profile(start_km=start_km, end_km=end_km)
        if not profile:
            raise ChainResolverError("No height profile samples found for interval")

        start_m = parse_km_string(start_km).total_meters
        end_m = parse_km_string(end_km).total_meters
        filters = self._infer_parent_filters(start_km, end_km, profile)
        chain_key = f"master-v4a:{int(start_m)}-{int(end_m)}"

        return ResolvedChain(
            chain_key=chain_key,
            strategy="geometric-parent-matching-v4a",
            notes=(
                "V4A använder geometrisk parent-matchning som mellanläge. Kedjan bedöms med kompakthetsmått "
                "så att en 50 km-profil ska ligga inom en rimlig geografisk korridor och inte spricka upp i "
                "flera avlägsna områden. Nästa steg är att binda detta direkt till mastertabellernas föräldraobjekt."
            ),
            sample_count=len(profile),
            filters=filters,
        )

    def build_resolved_profile(self, start_km: str, end_km: str) -> tuple[ResolvedChain, list[HeightSample], list[HeightSegment]]:
        """
        Bygger profil och segment för en löst kedja.

        Parameters
        ----------
        start_km : str
            Start på intervallet.
        end_km : str
            Slut på intervallet.

        Returns
        -------
        tuple[ResolvedChain, list[HeightSample], list[HeightSegment]]
            Vald kedja, profilerade punkter och segment.
        """
        chain = self.resolve_chain(start_km=start_km, end_km=end_km)
        profile = self.profile_builder.build_height_profile(start_km=start_km, end_km=end_km)
        segments = self.profile_builder.build_height_segments(start_km=start_km, end_km=end_km)
        return chain, profile, segments
