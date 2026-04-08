from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def load_config(path: str | Path = "config.json", fallback_path: str | Path = "config.example.json") -> dict[str, Any]:
    config_path = Path(path)
    if config_path.exists():
        return json.loads(config_path.read_text(encoding="utf-8"))

    example_path = Path(fallback_path)
    if example_path.exists():
        return json.loads(example_path.read_text(encoding="utf-8"))

    raise FileNotFoundError(
        f"Neither {config_path} nor fallback {example_path} could be found."
    )
