from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .config_loader import load_config
from .trafikverket_gpkg import TrafikverketGeoPackage


class MasterNetworkAnalyzerError(Exception):
    """Basundantag för master network analyzer."""


@dataclass(frozen=True, slots=True)
class NetworkTableSummary:
    """
    Sammanfattning av ett nätverksrelaterat lager.

    Parameters
    ----------
    table_name : str
        Namn på tabellen.
    row_count : int
        Antal rader i tabellen.
    columns : list[str]
        Tillgängliga kolumner.
    sample_records : list[dict[str, Any]]
        Exempelposter utan geometri.
    """

    table_name: str
    row_count: int
    columns: list[str]
    sample_records: list[dict[str, Any]]


@dataclass(frozen=True, slots=True)
class ChainParentSummary:
    """
    Sammanfattning av en möjlig föräldrastruktur i mastern.

    Parameters
    ----------
    layer : str
        Lagerkategori, till exempel bandel eller stråk.
    distinct_codes : int
        Antal unika koder i `Indkod`.
    top_examples : list[dict[str, Any]]
        Exempel på frekventa koder.
    notes : str
        Kommentar om hur lagret kan användas i kedjemodellen.
    """

    layer: str
    distinct_codes: int
    top_examples: list[dict[str, Any]]
    notes: str


class MasterNetworkAnalyzer:
    """
    Analyserar masterpaketet från Trafikverket med fokus på nätverk och kedjeföräldrar.

    Parameters
    ----------
    gpkg : TrafikverketGeoPackage
        GeoPackage-läsare riktad mot masterfilen.
    """

    NETWORK_TABLES = ["Net_JVG_Link", "Net_JVG_LinkSequence", "Net_JVG_Node"]
    PARENT_TABLES = {
        "bandel": "BIS_DK_O_13_Bandel",
        "strak": "BIS_DK_O_19_Strak",
        "langdmatningsdel": "BIS_DK_O_20_Langdmatningsdel",
        "spar": "BIS_DK_O_70_Spar_Upp_Ned_Enkel",
        "sparnummer": "BIS_DK_O_71_Sparnummer",
    }

    def __init__(self, gpkg: TrafikverketGeoPackage) -> None:
        """
        Initierar analyzern.

        Parameters
        ----------
        gpkg : TrafikverketGeoPackage
            GeoPackage-läsare riktad mot masterfilen.
        """
        self.gpkg = gpkg

    @classmethod
    def from_config_file(cls, config_path: str = "config.json") -> "MasterNetworkAnalyzer":
        """
        Skapar analyzern från konfigurationsfil.

        Parameters
        ----------
        config_path : str, optional
            Sökväg till konfigurationsfil.

        Returns
        -------
        MasterNetworkAnalyzer
            Färdig analyzer-instans.
        """
        config = load_config(config_path)
        gpkg_path = config.get("trafikverket_gpkg_path")
        if not gpkg_path:
            raise MasterNetworkAnalyzerError("Config is missing trafikverket_gpkg_path for master data")
        gpkg = TrafikverketGeoPackage(gpkg_path)
        return cls(gpkg=gpkg)

    def summarize_network_tables(self) -> list[NetworkTableSummary]:
        """
        Sammanfattar de centrala nätverkstabellerna i mastern.

        Returns
        -------
        list[NetworkTableSummary]
            Sammanfattningar för link, link sequence och node.
        """
        summaries: list[NetworkTableSummary] = []
        for table_name in self.NETWORK_TABLES:
            columns = self.gpkg.get_columns(table_name)
            samples = self.gpkg.fetch_rows(table_name, limit=3)
            summaries.append(
                NetworkTableSummary(
                    table_name=table_name,
                    row_count=self.gpkg.count_rows(table_name),
                    columns=columns,
                    sample_records=samples,
                )
            )
        return summaries

    def summarize_chain_parents(self) -> list[ChainParentSummary]:
        """
        Sammanfattar lager som kan fungera som chain parents.

        Returns
        -------
        list[ChainParentSummary]
            Sammanfattningar för bandel, stråk, längdmätningsdel och spårrelaterade lager.
        """
        summaries: list[ChainParentSummary] = []
        notes_map = {
            "bandel": "Bandel ser ut som en stark fysisk/administrativ förälder för längre sammanhängande sträckor.",
            "strak": "Stråk verkar vara överordnad bana eller trafikrelation, sannolikt för grov som ensam nyckel.",
            "langdmatningsdel": "Längdmätningsdel är stark kandidat för själva referenskedjan längs banan.",
            "spar": "Spårkod behövs sannolikt för att skilja upp-, ned- och parallella spår inom samma kedja.",
            "sparnummer": "Spårnummer kan ge lokal identifiering där flera spår förekommer nära varandra.",
        }
        for layer_key, table_name in self.PARENT_TABLES.items():
            rows = self.gpkg.fetch_rows(
                table_name,
                limit=50000,
                columns=["Indkod", "Indkod_beskr"],
            )
            counts: dict[tuple[str, str], int] = {}
            for row in rows:
                code = str(row.get("Indkod") or "")
                desc = str(row.get("Indkod_beskr") or "")
                counts[(code, desc)] = counts.get((code, desc), 0) + 1
            top_examples = [
                {"Indkod": code, "Indkod_beskr": desc, "count": count}
                for (code, desc), count in sorted(counts.items(), key=lambda item: item[1], reverse=True)[:10]
            ]
            summaries.append(
                ChainParentSummary(
                    layer=layer_key,
                    distinct_codes=len({code for code, _ in counts}),
                    top_examples=top_examples,
                    notes=notes_map[layer_key],
                )
            )
        return summaries

    def recommend_chain_key_strategy(self) -> dict[str, Any]:
        """
        Returnerar en första rekommenderad strategi för chain key i masterdatan.

        Returns
        -------
        dict[str, Any]
            Rekommenderad strategi och motivering.
        """
        return {
            "network_backbone": ["Net_JVG_Node", "Net_JVG_Link", "Net_JVG_LinkSequence"],
            "chain_parent_order": ["bandel", "langdmatningsdel", "spar", "sparnummer"],
            "notes": [
                "Använd nätverkstabellerna som topologisk ryggrad för sammanhängande länkning.",
                "Använd bandel som överordnat filter för att undvika att olika geografiska områden blandas ihop.",
                "Använd längdmätningsdel som sannolik referenskedja för km-tal inom bandelen.",
                "Använd spårkod och vid behov spårnummer för att särskilja parallella spår inom samma kedja.",
            ],
        }
