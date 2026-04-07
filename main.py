from __future__ import annotations

import json
import logging
from pathlib import Path

from banprofil.lantmateriet_client import LantmaterietClient, LantmaterietError


logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger("banprofil")


def main() -> None:
    config_path = Path("config.json")
    if not config_path.exists():
        raise SystemExit("config.json saknas. Kopiera config.example.json och fyll i nycklarna.")

    client = LantmaterietClient.from_config_file(config_path)

    try:
        result = client.get_height(e=667552, n=6983948, srid=3006)
    except LantmaterietError as exc:
        logger.error("Kunde inte hämta höjddata: %s", exc)
        raise SystemExit(1) from exc

    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
