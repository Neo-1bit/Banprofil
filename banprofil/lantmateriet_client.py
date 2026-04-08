from __future__ import annotations

import base64
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import requests

from .config_loader import load_config
from .coordinate_transform import wgs84_to_sweref99tm

logger = logging.getLogger(__name__)


class LantmaterietError(Exception):
    """Basundantag för Lantmäteriet-klienten."""


class TokenScopeError(LantmaterietError):
    """Undantag för token utan förväntat scope."""


class ApiResponseError(LantmaterietError):
    """Undantag när API-svaret inte har förväntat format."""


@dataclass(slots=True)
class LantmaterietConfig:
    """
    Konfiguration för Lantmäteriets API.

    Parameters
    ----------
    consumer_key : str
        OAuth consumer key.
    consumer_secret : str
        OAuth consumer secret.
    token_url : str
        URL för token-endpoint.
    api_base_url : str
        Bas-URL för höjd-API:t.
    scope : str, optional
        Scope som ska begäras vid tokenhämtning.
    timeout_seconds : int, optional
        Timeout i sekunder för HTTP-anrop.
    """

    consumer_key: str
    consumer_secret: str
    token_url: str
    api_base_url: str
    scope: str = "markhojd_direkt_v1_read"
    timeout_seconds: int = 30


class LantmaterietClient:
    """
    Klient för Lantmäteriets Markhöjd Direkt API.

    Parameters
    ----------
    config : LantmaterietConfig
        Konfiguration för API-anrop.
    """

    def __init__(self, config: LantmaterietConfig) -> None:
        """
        Initierar klienten med given konfiguration.

        Parameters
        ----------
        config : LantmaterietConfig
            Konfiguration för API-anrop.
        """
        self.config = config
        self._access_token: str | None = None

    @classmethod
    def from_config_file(cls, path: str | Path = "config.json") -> "LantmaterietClient":
        """
        Skapar klienten från konfigurationsfil.

        Parameters
        ----------
        path : str | Path, optional
            Sökväg till konfigurationsfil.

        Returns
        -------
        LantmaterietClient
            Färdig klientinstans.
        """
        data = load_config(path)
        allowed_keys = {field for field in LantmaterietConfig.__dataclass_fields__}
        filtered = {key: value for key, value in data.items() if key in allowed_keys}
        config = LantmaterietConfig(**filtered)
        return cls(config)

    def _build_basic_auth_header(self) -> str:
        """
        Bygger Authorization-header för OAuth-tokenanrop.

        Returns
        -------
        str
            Basic Authorization-header.
        """
        credentials = f"{self.config.consumer_key}:{self.config.consumer_secret}".encode("ascii")
        token = base64.b64encode(credentials).decode("ascii")
        return f"Basic {token}"

    def fetch_access_token(self, force_refresh: bool = False) -> str:
        """
        Hämtar access token från Lantmäteriet.

        Parameters
        ----------
        force_refresh : bool, optional
            Om `True` hämtas ny token även om en token redan finns cachad.

        Returns
        -------
        str
            Access token.

        Raises
        ------
        LantmaterietError
            Om tokenanropet misslyckas eller om svar saknar token.
        TokenScopeError
            Om tokenen saknar förväntat scope.
        """
        if self._access_token and not force_refresh:
            return self._access_token

        logger.info("Requesting access token from Lantmäteriet")
        try:
            response = requests.post(
                self.config.token_url,
                headers={
                    "Authorization": self._build_basic_auth_header(),
                    "Content-Type": "application/x-www-form-urlencoded",
                },
                data={
                    "grant_type": "client_credentials",
                    "scope": self.config.scope,
                },
                timeout=self.config.timeout_seconds,
            )
            response.raise_for_status()
        except requests.RequestException as exc:
            raise LantmaterietError(f"Failed to fetch access token: {exc}") from exc

        payload = response.json()
        scope = payload.get("scope", "")
        if self.config.scope not in scope.split():
            raise TokenScopeError(
                f"Expected scope '{self.config.scope}', got '{scope or '<missing>'}'"
            )

        access_token = payload.get("access_token")
        if not access_token:
            raise LantmaterietError("Token response did not contain access_token")

        self._access_token = access_token
        return access_token

    def get_height(self, e: float, n: float, srid: int = 3006) -> dict[str, Any]:
        """
        Hämtar höjddata för en punkt.

        Parameters
        ----------
        e : float
            Easting i valt koordinatsystem.
        n : float
            Northing i valt koordinatsystem.
        srid : int, optional
            SRID för koordinaterna.

        Returns
        -------
        dict[str, Any]
            API-svar som dictionary.

        Raises
        ------
        LantmaterietError
            Om anropet misslyckas.
        ApiResponseError
            Om svaret saknar förväntad geometri.
        """
        token = self.fetch_access_token()
        logger.info("Fetching elevation for e=%s n=%s srid=%s", e, n, srid)
        try:
            response = requests.get(
                f"{self.config.api_base_url}/hojd",
                headers={
                    "Authorization": f"Bearer {token}",
                    "Accept": "application/json",
                },
                params={"srid": srid, "e": e, "n": n},
                timeout=self.config.timeout_seconds,
            )
            response.raise_for_status()
        except requests.RequestException as exc:
            raise LantmaterietError(f"Failed to fetch elevation data: {exc}") from exc

        payload = response.json()
        if "geometry" not in payload:
            raise ApiResponseError(f"Unexpected API response: {payload}")
        return payload

    def get_elevation_value(self, e: float, n: float, srid: int = 3006) -> float | None:
        """
        Hämtar endast höjdvärdet för en punkt.

        Parameters
        ----------
        e : float
            Easting i valt koordinatsystem.
        n : float
            Northing i valt koordinatsystem.
        srid : int, optional
            SRID för koordinaterna.

        Returns
        -------
        float | None
            Höjdvärde om det finns, annars `None`.
        """
        data = self.get_height(e=e, n=n, srid=srid)
        coordinates = data.get("geometry", {}).get("coordinates", [])
        if len(coordinates) >= 3:
            return coordinates[2]
        return None

    def get_height_from_wgs84(self, latitude: float, longitude: float) -> dict[str, Any]:
        """
        Hämtar höjddata från WGS84-koordinater.

        Parameters
        ----------
        latitude : float
            Latitud i WGS84.
        longitude : float
            Longitud i WGS84.

        Returns
        -------
        dict[str, Any]
            API-svar med höjddata.
        """
        sweref_point = wgs84_to_sweref99tm(latitude=latitude, longitude=longitude)
        return self.get_height(e=sweref_point.e, n=sweref_point.n, srid=3006)

    def get_many_heights(self, points: list[dict[str, float]]) -> list[dict[str, Any]]:
        """
        Hämtar höjddata för flera punkter.

        Parameters
        ----------
        points : list[dict[str, float]]
            Lista av punkter med antingen `e` och `n`, eller `latitude` och `longitude`.

        Returns
        -------
        list[dict[str, Any]]
            Lista med API-svar.

        Raises
        ------
        LantmaterietError
            Om en punkt saknar nödvändiga koordinatfält.
        """
        results: list[dict[str, Any]] = []
        for point in points:
            if {"e", "n"}.issubset(point):
                result = self.get_height(e=point["e"], n=point["n"], srid=int(point.get("srid", 3006)))
            elif {"latitude", "longitude"}.issubset(point):
                result = self.get_height_from_wgs84(
                    latitude=point["latitude"],
                    longitude=point["longitude"],
                )
            else:
                raise LantmaterietError(
                    "Each point must contain either 'e' and 'n' or 'latitude' and 'longitude'"
                )
            results.append(result)
        return results
