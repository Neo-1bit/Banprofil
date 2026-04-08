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

    V3 utgår från masterpaketets hierarki och väljer explicit parent filters
    som ett första steg mot hård kedjefiltrering.

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

    def _infer_parent_filters(self, start_km: str, end_km: str) -> dict[str, Any]:
        """
        Härleder preliminära parent filters för kedjan.

        Parameters
        ----------
        start_km : str
            Start på intervallet.
        end_km : str
            Slut på intervallet.

        Returns
        -------
        dict[str, Any]
            Preliminära filter för bandel, längdmätningsdel och spår.
        """
        start_m = parse_km_string(start_km).total_meters
        # första explicita v3-hypotes: låga km-tal hör ofta till bandelar med faktisk bandelindelning,
        # medan äldre heuristik blandade flera geografier. Här använder vi mastermodellens hierarki
        # och sätter tydliga placeholders som nästa iteration ska slå upp direkt ur parenttabellerna.
        if start_m < 200000:
            bandel = "master-bandel-candidate"
            langdmatningsdel = "master-langdmatningsdel-candidate"
            spar = "master-spar-candidate"
        else:
            bandel = "master-bandel-candidate"
            langdmatningsdel = "master-langdmatningsdel-candidate"
            spar = "master-spar-candidate"

        strategy = self.master_analyzer.recommend_chain_key_strategy() if self.master_analyzer else {}
        return {
            "bandel": bandel,
            "langdmatningsdel": langdmatningsdel,
            "spar": spar,
            "network_backbone": strategy.get("network_backbone", []),
            "km_interval": {"start": start_km, "end": end_km},
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
        filters = self._infer_parent_filters(start_km, end_km)
        chain_key = f"master-v3:{int(start_m)}-{int(end_m)}:{filters['bandel']}:{filters['langdmatningsdel']}:{filters['spar']}"

        return ResolvedChain(
            chain_key=chain_key,
            strategy="master-parent-heuristic-v3",
            notes=(
                "V3 använder masterhierarkin som explicit modell och bär med sig parent filters för bandel, "
                "längdmätningsdel och spårdimension. Nästa iteration ska slå upp dessa direkt i mastertabellerna "
                "för att filtrera profilobjekten hårt och minska geografiska hopp i KML."
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
