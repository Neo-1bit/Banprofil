from __future__ import annotations

import sqlite3
import struct
from dataclasses import dataclass
from pathlib import Path

from .config_loader import load_config


class GeoPackageInspectorError(Exception):
    """Basundantag för GeoPackage-inspektion."""


@dataclass(frozen=True, slots=True)
class GeometryHeaderInfo:
    """
    Sammanfattning av GeoPackageBinary-header.

    Parameters
    ----------
    magic : str
        Magic bytes, normalt `GP`.
    version : int
        GeoPackageBinary-version.
    flags : int
        Flaggbiten från headern.
    envelope_code : int
        Envelope-indikator från flaggorna.
    srs_id : int
        SRS-id i headern.
    envelope_size_bytes : int
        Antal bytes som envelope upptar.
    wkb_offset : int
        Startoffset för WKB-delen.
    """

    magic: str
    version: int
    flags: int
    envelope_code: int
    srs_id: int
    envelope_size_bytes: int
    wkb_offset: int


class GeoPackageInspector:
    """
    Hjälpklass för att inspektera GeoPackageBinary-header och RTree-användning.

    Parameters
    ----------
    gpkg_path : str | Path
        Sökväg till GeoPackage-fil.
    """

    def __init__(self, gpkg_path: str | Path) -> None:
        """
        Initierar inspektören.

        Parameters
        ----------
        gpkg_path : str | Path
            Sökväg till GeoPackage-fil.
        """
        self.gpkg_path = Path(gpkg_path)
        if not self.gpkg_path.exists():
            raise GeoPackageInspectorError(f"GeoPackage not found: {self.gpkg_path}")

    @classmethod
    def from_config_file(cls, config_path: str = "config.json") -> "GeoPackageInspector":
        """
        Skapar inspektör från konfigurationsfil.

        Parameters
        ----------
        config_path : str, optional
            Sökväg till konfigurationsfil.

        Returns
        -------
        GeoPackageInspector
            Färdig instans.
        """
        config = load_config(config_path)
        gpkg_path = config.get("trafikverket_gpkg_path")
        if not gpkg_path:
            raise GeoPackageInspectorError("Config is missing trafikverket_gpkg_path")
        return cls(gpkg_path)

    def _connect(self) -> sqlite3.Connection:
        """
        Öppnar SQLite-anslutning.

        Returns
        -------
        sqlite3.Connection
            Aktiv databasanslutning.
        """
        return sqlite3.connect(self.gpkg_path)

    @staticmethod
    def inspect_geometry_header_static(geom: bytes) -> GeometryHeaderInfo:
        """
        Tolkar GeoPackageBinary-header från en geometri.

        Parameters
        ----------
        geom : bytes
            GeoPackage-geometri.

        Returns
        -------
        GeometryHeaderInfo
            Headerinformation.
        """
        if not isinstance(geom, bytes) or len(geom) < 8:
            raise GeoPackageInspectorError("Geometry payload is too short")
        magic = geom[0:2].decode("ascii", errors="replace")
        version = geom[2]
        flags = geom[3]
        envelope_code = (flags >> 1) & 0b111
        envelope_size_map = {
            0: 0,
            1: 32,
            2: 48,
            3: 48,
            4: 64,
        }
        envelope_size_bytes = envelope_size_map.get(envelope_code, 0)
        srs_id = struct.unpack("<i", geom[4:8])[0]
        wkb_offset = 8 + envelope_size_bytes
        return GeometryHeaderInfo(
            magic=magic,
            version=version,
            flags=flags,
            envelope_code=envelope_code,
            srs_id=srs_id,
            envelope_size_bytes=envelope_size_bytes,
            wkb_offset=wkb_offset,
        )

    def inspect_geometry_header(self, geom: bytes) -> GeometryHeaderInfo:
        """
        Tolkar GeoPackageBinary-header från en geometri.

        Parameters
        ----------
        geom : bytes
            GeoPackage-geometri.

        Returns
        -------
        GeometryHeaderInfo
            Headerinformation.
        """
        return self.inspect_geometry_header_static(geom)

    def fetch_sample_headers(self, table_name: str, limit: int = 5) -> list[GeometryHeaderInfo]:
        """
        Hämtar headerinfo för ett urval geometrier i en tabell.

        Parameters
        ----------
        table_name : str
            Tabell att läsa från.
        limit : int, optional
            Antal rader att inspektera.

        Returns
        -------
        list[GeometryHeaderInfo]
            Headerinformation för urvalet.
        """
        with self._connect() as con:
            cur = con.cursor()
            cur.execute(f'SELECT geom FROM "{table_name}" LIMIT {int(limit)}')
            return [self.inspect_geometry_header(row[0]) for row in cur.fetchall()]

    def rtree_window_query(
        self,
        table_name: str,
        minx: float,
        maxx: float,
        miny: float,
        maxy: float,
        limit: int = 500,
    ) -> list[int]:
        """
        Hämtar feature-id:n från RTree inom bbox.

        Parameters
        ----------
        table_name : str
            Featuretabellens namn.
        minx : float
            Bbox min x.
        maxx : float
            Bbox max x.
        miny : float
            Bbox min y.
        maxy : float
            Bbox max y.
        limit : int, optional
            Max antal id:n att returnera.

        Returns
        -------
        list[int]
            Matchande feature-id:n.
        """
        rtree_name = f"rtree_{table_name}_geom"
        with self._connect() as con:
            cur = con.cursor()
            cur.execute(
                f'''
                SELECT id
                FROM "{rtree_name}"
                WHERE maxx >= ? AND minx <= ? AND maxy >= ? AND miny <= ?
                LIMIT ?
                ''',
                (minx, maxx, miny, maxy, int(limit)),
            )
            return [int(row[0]) for row in cur.fetchall()]
