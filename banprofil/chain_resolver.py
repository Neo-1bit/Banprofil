from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .chain_analysis import ChainAnalyzer
from .height_profile import HeightProfileBuilder, HeightSample, HeightSegment
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
    """

    chain_key: str
    strategy: str
    notes: str
    sample_count: int


class ChainResolver:
    """
    Försöker välja en sammanhängande kedja för ett km-intervall.

    Första versionen använder heuristik och bygger på kedjeanalysens resultat.
    Målet är att undvika att olika geografiska delsträckor blandas ihop när
    samma km-tal återkommer på flera platser.

    Parameters
    ----------
    analyzer : ChainAnalyzer
        Analysobjekt för Trafikverkets GeoPackage.
    profile_builder : HeightProfileBuilder
        Byggare för höjdprofiler.
    """

    def __init__(self, analyzer: ChainAnalyzer, profile_builder: HeightProfileBuilder) -> None:
        """
        Initierar kedjeresolvern.

        Parameters
        ----------
        analyzer : ChainAnalyzer
            Analysobjekt för Trafikverkets GeoPackage.
        profile_builder : HeightProfileBuilder
            Byggare för höjdprofiler.
        """
        self.analyzer = analyzer
        self.profile_builder = profile_builder

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
        return cls(analyzer=analyzer, profile_builder=profile_builder)

    def resolve_chain(self, start_km: str, end_km: str) -> ResolvedChain:
        """
        Väljer en första kedjekandidat för km-intervallet.

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
        """
        profile = self.profile_builder.build_height_profile(start_km=start_km, end_km=end_km)
        if not profile:
            raise ChainResolverError("No height profile samples found for interval")

        # Första heuristik: välj kedja utifrån vilket km-intervall vi faktiskt arbetar med.
        # Tills vi hittat explicita relationer används ett stabilt kedjenamn per intervall.
        start_m = parse_km_string(start_km).total_meters
        end_m = parse_km_string(end_km).total_meters
        chain_key = f"interval:{int(start_m)}-{int(end_m)}"

        return ResolvedChain(
            chain_key=chain_key,
            strategy="interval-heuristic",
            notes="Första versionen håller ihop en fysisk profil inom valt intervall och förbereder nästa steg där längdmätningsdel/spår binds explicit.",
            sample_count=len(profile),
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
