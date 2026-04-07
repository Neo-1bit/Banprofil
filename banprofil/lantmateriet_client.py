from __future__ import annotations

import base64
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import requests


class LantmaterietError(Exception):
    """Base exception for Lantmäteriet client errors."""


class TokenScopeError(LantmaterietError):
    """Raised when the token response does not include the expected scope."""


@dataclass(slots=True)
class LantmaterietConfig:
    consumer_key: str
    consumer_secret: str
    token_url: str
    api_base_url: str
    scope: str = "markhojd_direkt_v1_read"
    timeout_seconds: int = 30


class LantmaterietClient:
    def __init__(self, config: LantmaterietConfig) -> None:
        self.config = config
        self._access_token: str | None = None

    @classmethod
    def from_config_file(cls, path: str | Path) -> "LantmaterietClient":
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        config = LantmaterietConfig(**data)
        return cls(config)

    def _build_basic_auth_header(self) -> str:
        credentials = f"{self.config.consumer_key}:{self.config.consumer_secret}".encode("ascii")
        token = base64.b64encode(credentials).decode("ascii")
        return f"Basic {token}"

    def fetch_access_token(self, force_refresh: bool = False) -> str:
        if self._access_token and not force_refresh:
            return self._access_token

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
        token = self.fetch_access_token()
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
        return response.json()

    def get_elevation_value(self, e: float, n: float, srid: int = 3006) -> float | None:
        data = self.get_height(e=e, n=n, srid=srid)
        coordinates = data.get("geometry", {}).get("coordinates", [])
        if len(coordinates) >= 3:
            return coordinates[2]
        return None
