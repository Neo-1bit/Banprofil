from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def load_config(path: str | Path = "config.json", fallback_path: str | Path = "config.example.json") -> dict[str, Any]:
    """
    Laddar projektkonfiguration från JSON-fil.

    Funktionen försöker först läsa `config.json`. Om den inte finns används
    `config.example.json` som fallback.

    Parameters
    ----------
    path : str | Path, optional
        Sökväg till primär konfigurationsfil.
    fallback_path : str | Path, optional
        Sökväg till fallback-fil som används om primärfilen saknas.

    Returns
    -------
    dict[str, Any]
        Inläst konfiguration som dictionary.

    Raises
    ------
    FileNotFoundError
        Om varken primär konfigurationsfil eller fallback-fil finns.
    json.JSONDecodeError
        Om någon av konfigurationsfilerna innehåller ogiltig JSON.
    """
    config_path = Path(path)
    if config_path.exists():
        return json.loads(config_path.read_text(encoding="utf-8"))

    example_path = Path(fallback_path)
    if example_path.exists():
        return json.loads(example_path.read_text(encoding="utf-8"))

    raise FileNotFoundError(
        f"Neither {config_path} nor fallback {example_path} could be found."
    )
