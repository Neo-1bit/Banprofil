from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from .profile_chain import parse_km_string
from .trafikverket_gpkg import TrafikverketGeoPackage

POINT_Z_PATTERN = re.compile(
    r"POINT\((?P<e>-?\d+(?:\.\d+)?)\s+(?P<n>-?\d+(?:\.\d+)?)\s+(?P<z>-?\d+(?:\.\d+)?)\)"
)


class ChainAnalysisError(Exception):
    """Basundantag för kedjeanalys."""


@dataclass(frozen=True, slots=True)
class ChainCandidate:
    """
    Beskriver en kandidat för överordnad kedjenyckel.

    Parameters
    ----------
    layer : str
        Namn på lager eller källa.
    key : str
        Kandidatnyckel, till exempel indkod eller annan identifierare.
    description : str
        Mänskligt läsbar beskrivning.
    match_count : int
        Antal profilerade punkter eller objekt som matchar kandidaten.
    notes : str
        Kort analyskommentar.
    """

    layer: str
    key: str
    description: str
    match_count: int
    notes: str


@dataclass(frozen=True, slots=True)
class AmbiguousInterval:
    """
    Representerar ett km-intervall som inte är unikt.

    Parameters
    ----------
    start_km : str
        Start av intervallet.
    end_km : str
        Slut av intervallet.
    unique_geometry_count : int
        Antal unika geometrier för intervallet.
    unique_bis_count : int
        Antal unika BIS-objekt för intervallet.
    spread_m : float
        Geografisk spridning i meter mellan ytterpunkterna.
    sample_rows : list[dict[str, Any]]
        Exempelrader från intervallet.
    """

    start_km: str
    end_km: str
    unique_geometry_count: int
    unique_bis_count: int
    spread_m: float
    sample_rows: list[dict[str, Any]]


class ChainAnalyzer:
    """
    Analyserar hur profilkedjor bör grupperas i Trafikverkets data.

    Syftet är att undersöka vilka nycklar som krävs utöver km-tal för att få
    en geografiskt sammanhängande kedja.

    Parameters
    ----------
    gpkg : TrafikverketGeoPackage
        GeoPackage-läsare för Trafikverkets data.
    """

    PROFILE_TABLES = {
        "raklinje": "BIS_DK_O_4012_Raklinje",
        "overgangskurva": "BIS_DK_O_4011_Overgangskurva",
        "cirkularkurva": "BIS_DK_O_4010_Cirkularkurva",
        "lutning": "BIS_DK_O_4015_Lutning",
    }

    PARENT_TABLES = {
        "langdmatningsdel": "BIS_DK_O_20_Langdmatningsdel",
        "strak": "BIS_DK_O_19_Strak",
        "spar": "BIS_DK_O_70_Spar_Upp_Ned_Enkel",
    }

    def __init__(self, gpkg: TrafikverketGeoPackage) -> None:
        """
        Initierar kedjeanalys.

        Parameters
        ----------
        gpkg : TrafikverketGeoPackage
            GeoPackage-läsare för Trafikverkets data.
        """
        self.gpkg = gpkg

    @classmethod
    def from_config_file(cls, config_path: str = "config.json") -> "ChainAnalyzer":
        """
        Skapar kedjeanalys från konfigurationsfil.

        Parameters
        ----------
        config_path : str, optional
            Sökväg till konfigurationsfil.

        Returns
        -------
        ChainAnalyzer
            Färdig instans av analysklassen.
        """
        gpkg = TrafikverketGeoPackage.from_config_file(config_path)
        return cls(gpkg)

    def _parse_point_xy(self, value: str | None) -> tuple[float, float] | None:
        """
        Tolkar X/Y ur textrepräsentation av punkt.

        Parameters
        ----------
        value : str | None
            Punkttext från Trafikverket.

        Returns
        -------
        tuple[float, float] | None
            Easting och northing, eller `None` om punkten inte gick att tolka.
        """
        if not value:
            return None
        match = POINT_Z_PATTERN.search(value)
        if not match:
            return None
        return float(match.group("e")), float(match.group("n"))

    def find_ambiguous_intervals(
        self,
        layer_key: str = "raklinje",
        min_unique_geometries: int = 2,
        limit: int = 20,
    ) -> list[AmbiguousInterval]:
        """
        Hittar km-intervall som förekommer på flera geometrier.

        Parameters
        ----------
        layer_key : str, optional
            Profilager som ska analyseras.
        min_unique_geometries : int, optional
            Minsta antal unika geometrier för att intervallet ska räknas som tvetydigt.
        limit : int, optional
            Max antal intervall att returnera.

        Returns
        -------
        list[AmbiguousInterval]
            Tvetydiga km-intervall sorterade efter störst spridning och flest geometrier.

        Raises
        ------
        ChainAnalysisError
            Om lagernyckeln är okänd.
        """
        table_name = self.PROFILE_TABLES.get(layer_key)
        if not table_name:
            raise ChainAnalysisError(f"Unknown profile layer: {layer_key}")

        rows = self.gpkg.fetch_rows(
            table_name,
            limit=50000,
            columns=[
                "Kmtal",
                "Kmtalti",
                "Koordinater_start",
                "Koordinater_slut",
                "ELEMENT_ID",
                "Bisobjektnr",
            ],
        )

        grouped: dict[tuple[str, str], list[dict[str, Any]]] = {}
        for row in rows:
            start_km = row.get("Kmtal")
            end_km = row.get("Kmtalti")
            if not start_km or not end_km:
                continue
            grouped.setdefault((str(start_km), str(end_km)), []).append(row)

        results: list[AmbiguousInterval] = []
        for (start_km, end_km), items in grouped.items():
            geometries = {
                f"{item.get('Koordinater_start')}|{item.get('Koordinater_slut')}"
                for item in items
                if item.get("Koordinater_start") and item.get("Koordinater_slut")
            }
            bis_ids = {item.get("Bisobjektnr") for item in items if item.get("Bisobjektnr") is not None}
            if len(geometries) < min_unique_geometries:
                continue

            points = []
            for item in items:
                for key in ("Koordinater_start", "Koordinater_slut"):
                    point = self._parse_point_xy(item.get(key))
                    if point:
                        points.append(point)
            if not points:
                continue

            xs = [point[0] for point in points]
            ys = [point[1] for point in points]
            spread_m = ((max(xs) - min(xs)) ** 2 + (max(ys) - min(ys)) ** 2) ** 0.5

            results.append(
                AmbiguousInterval(
                    start_km=start_km,
                    end_km=end_km,
                    unique_geometry_count=len(geometries),
                    unique_bis_count=len(bis_ids),
                    spread_m=spread_m,
                    sample_rows=items[:5],
                )
            )

        results.sort(key=lambda item: (item.spread_m, item.unique_geometry_count), reverse=True)
        return results[:limit]

    def summarize_chain_key_hypothesis(self) -> list[ChainCandidate]:
        """
        Returnerar en kvalitativ sammanfattning av rimliga chain key-kandidater.

        Returns
        -------
        list[ChainCandidate]
            Kandidater med kort analys av deras lämplighet.
        """
        parent_rows = {}
        for key, table in self.PARENT_TABLES.items():
            rows = self.gpkg.fetch_rows(table, limit=50000, columns=["ELEMENT_ID", "Indkod", "Indkod_beskr"])
            parent_rows[key] = rows

        return [
            ChainCandidate(
                layer="langdmatningsdel",
                key="Indkod",
                description="Längdmätningsdelens indkod",
                match_count=len({row.get('Indkod') for row in parent_rows['langdmatningsdel'] if row.get('Indkod')}),
                notes="Stark kandidat eftersom lagret explicit representerar längdmätningskedjor och har linjeliknande koder.",
            ),
            ChainCandidate(
                layer="strak",
                key="Indkod",
                description="Stråkets indkod",
                match_count=len({row.get('Indkod') for row in parent_rows['strak'] if row.get('Indkod')}),
                notes="Bra överordnad gruppering, men sannolikt för grov som ensam kedjenyckel.",
            ),
            ChainCandidate(
                layer="spar",
                key="Indkod",
                description="Spårtyp eller spårnummer-indkod",
                match_count=len({row.get('Indkod') for row in parent_rows['spar'] if row.get('Indkod')}),
                notes="Viktig kompletterande dimension för att skilja uppspår, nedspår och parallella spår.",
            ),
        ]

    def analyze_interval(self, start_km: str, end_km: str) -> dict[str, Any]:
        """
        Gör en riktad analys av ett km-intervall.

        Parameters
        ----------
        start_km : str
            Start av intervallet.
        end_km : str
            Slut av intervallet.

        Returns
        -------
        dict[str, Any]
            Sammanställning med numeriska km-värden och tvetydiga matchningar i profillagren.
        """
        start_m = parse_km_string(start_km).total_meters
        end_m = parse_km_string(end_km).total_meters
        layer_hits: dict[str, int] = {}

        for layer_key, table_name in self.PROFILE_TABLES.items():
            rows = self.gpkg.fetch_rows(table_name, limit=50000, columns=["Kmtal", "Kmtalti"])
            count = 0
            for row in rows:
                row_start = row.get("Kmtal")
                row_end = row.get("Kmtalti")
                if not row_start or not row_end:
                    continue
                try:
                    row_start_m = parse_km_string(str(row_start)).total_meters
                    row_end_m = parse_km_string(str(row_end)).total_meters
                except Exception:
                    continue
                if row_end_m >= start_m and row_start_m <= end_m:
                    count += 1
            layer_hits[layer_key] = count

        return {
            "start_km": start_km,
            "end_km": end_km,
            "start_m": start_m,
            "end_m": end_m,
            "profile_layer_hits": layer_hits,
        }
