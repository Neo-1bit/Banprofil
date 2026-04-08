from __future__ import annotations

import glob
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .config_loader import load_config


class TrafikverketGeoPackageError(Exception):
    """Basundantag för åtkomst till Trafikverkets GeoPackage."""


@dataclass(frozen=True, slots=True)
class LayerInfo:
    """
    Beskriver ett lager i GeoPackage.

    Parameters
    ----------
    table_name : str
        Tabellnamn i GeoPackage.
    data_type : str
        Datatyp enligt `gpkg_contents`.
    """

    table_name: str
    data_type: str


class TrafikverketGeoPackage:
    """
    Läser lager och rader från Trafikverkets GeoPackage.

    Parameters
    ----------
    gpkg_path : str | Path
        Sökväg till en lokal `.gpkg`-fil.

    Raises
    ------
    TrafikverketGeoPackageError
        Om filen inte finns.
    """

    DEFAULT_LAYERS = {
        "strak": "BIS_DK_O_19_Strak",
        "langdmatningsdel": "BIS_DK_O_20_Langdmatningsdel",
        "spar": "BIS_DK_O_70_Spar_Upp_Ned_Enkel",
        "raklinje": "BIS_DK_O_4012_Raklinje",
        "cirkularkurva": "BIS_DK_O_4010_Cirkularkurva",
        "overgangskurva": "BIS_DK_O_4011_Overgangskurva",
        "vertikalkurva": "BIS_DK_O_4014_Vertikalkurva",
        "lutning": "BIS_DK_O_4015_Lutning",
        "ralsforhojning": "BIS_DK_O_4013_Ralsforhojning",
        "driftplats": "BIS_DK_O_597_Driftplats_med_driftplat",
    }

    def __init__(self, gpkg_path: str | Path) -> None:
        self.gpkg_path = Path(gpkg_path)
        if not self.gpkg_path.exists():
            raise TrafikverketGeoPackageError(f"GeoPackage not found: {self.gpkg_path}")

    @classmethod
    def from_config_file(cls, config_path: str | Path = "config.json") -> "TrafikverketGeoPackage":
        """
        Skapar en GeoPackage-läsare från konfigurationsfil.

        Parameters
        ----------
        config_path : str | Path, optional
            Sökväg till konfigurationsfil.

        Returns
        -------
        TrafikverketGeoPackage
            Instans med upplöst GeoPackage-sökväg.

        Raises
        ------
        TrafikverketGeoPackageError
            Om ingen GeoPackage-sökväg eller glob finns i konfigurationen.
        """
        config = load_config(config_path)
        gpkg_path = config.get("trafikverket_gpkg_path")
        if gpkg_path:
            return cls(gpkg_path)

        gpkg_glob = config.get("trafikverket_gpkg_glob")
        if gpkg_glob:
            matches = sorted(glob.glob(gpkg_glob, recursive=True))
            if matches:
                latest = max(matches, key=lambda p: Path(p).stat().st_mtime)
                return cls(latest)

        raise TrafikverketGeoPackageError(
            "No Trafikverket GeoPackage path found in config. Set trafikverket_gpkg_path or trafikverket_gpkg_glob."
        )

    def _connect(self) -> sqlite3.Connection:
        """
        Öppnar SQLite-anslutning till GeoPackage.

        Returns
        -------
        sqlite3.Connection
            Aktiv databasanslutning.
        """
        return sqlite3.connect(self.gpkg_path)

    def list_layers(self) -> list[LayerInfo]:
        """
        Listar lager i GeoPackage.

        Returns
        -------
        list[LayerInfo]
            Lagerdefinitioner från `gpkg_contents`.
        """
        with self._connect() as con:
            cur = con.cursor()
            cur.execute("SELECT table_name, data_type FROM gpkg_contents ORDER BY table_name")
            return [LayerInfo(table_name=row[0], data_type=row[1]) for row in cur.fetchall()]

    def get_columns(self, table_name: str) -> list[str]:
        """
        Hämtar kolumner för en tabell.

        Parameters
        ----------
        table_name : str
            Namn på tabellen.

        Returns
        -------
        list[str]
            Kolumnnamn i tabellen.

        Raises
        ------
        TrafikverketGeoPackageError
            Om tabellen inte finns.
        """
        with self._connect() as con:
            cur = con.cursor()
            cur.execute(f'PRAGMA table_info("{table_name}")')
            rows = cur.fetchall()
            if not rows:
                raise TrafikverketGeoPackageError(f"Table not found: {table_name}")
            return [row[1] for row in rows]

    def fetch_rows(
        self,
        table_name: str,
        limit: int = 100,
        offset: int = 0,
        columns: list[str] | None = None,
        where: str | None = None,
        order_by: str | None = None,
    ) -> list[dict[str, Any]]:
        """
        Hämtar rader från en tabell.

        Parameters
        ----------
        table_name : str
            Namn på tabellen.
        limit : int, optional
            Max antal rader att hämta.
        offset : int, optional
            Antal rader att hoppa över.
        columns : list[str] | None, optional
            Kolumner att läsa. Om `None` hämtas alla utom `geom`.
        where : str | None, optional
            SQL-villkor utan ordet `WHERE`.
        order_by : str | None, optional
            SQL-sortering utan ordet `ORDER BY`.

        Returns
        -------
        list[dict[str, Any]]
            Hämtade rader som dictionaries.

        Raises
        ------
        TrafikverketGeoPackageError
            Om någon kolumn saknas.
        """
        available_columns = self.get_columns(table_name)
        selected_columns = columns or [column for column in available_columns if column != "geom"]
        invalid = [column for column in selected_columns if column not in available_columns]
        if invalid:
            raise TrafikverketGeoPackageError(
                f"Columns not found in {table_name}: {', '.join(invalid)}"
            )

        query = f'SELECT {", ".join(f"\"{column}\"" for column in selected_columns)} FROM "{table_name}"'
        if where:
            query += f" WHERE {where}"
        if order_by:
            query += f" ORDER BY {order_by}"
        query += f" LIMIT {int(limit)} OFFSET {int(offset)}"

        with self._connect() as con:
            con.row_factory = sqlite3.Row
            cur = con.cursor()
            cur.execute(query)
            return [dict(row) for row in cur.fetchall()]

    def count_rows(self, table_name: str) -> int:
        """
        Räknar antal rader i en tabell.

        Parameters
        ----------
        table_name : str
            Namn på tabellen.

        Returns
        -------
        int
            Antal rader.
        """
        with self._connect() as con:
            cur = con.cursor()
            cur.execute(f'SELECT COUNT(*) FROM "{table_name}"')
            return int(cur.fetchone()[0])

    def fetch_named_layer(
        self,
        layer_key: str,
        limit: int = 100,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        """
        Hämtar rader från ett fördefinierat lager.

        Parameters
        ----------
        layer_key : str
            Kortnamn för lager enligt `DEFAULT_LAYERS`.
        limit : int, optional
            Max antal rader att hämta.
        offset : int, optional
            Antal rader att hoppa över.

        Returns
        -------
        list[dict[str, Any]]
            Hämtade rader.

        Raises
        ------
        TrafikverketGeoPackageError
            Om lagernyckeln är okänd.
        """
        table_name = self.DEFAULT_LAYERS.get(layer_key)
        if not table_name:
            raise TrafikverketGeoPackageError(
                f"Unknown layer key '{layer_key}'. Available: {', '.join(sorted(self.DEFAULT_LAYERS))}"
            )
        return self.fetch_rows(table_name=table_name, limit=limit, offset=offset)

    def summarize_default_layers(self) -> list[dict[str, Any]]:
        """
        Sammanfattar projektets viktigaste standardlager.

        Returns
        -------
        list[dict[str, Any]]
            Lager, radantal och kolumner för varje standardlager.
        """
        summary: list[dict[str, Any]] = []
        for layer_key, table_name in self.DEFAULT_LAYERS.items():
            summary.append(
                {
                    "layer_key": layer_key,
                    "table_name": table_name,
                    "row_count": self.count_rows(table_name),
                    "columns": self.get_columns(table_name),
                }
            )
        return summary
