from __future__ import annotations

import json
import logging
from pathlib import Path

from banprofil.lantmateriet_client import LantmaterietClient, LantmaterietError
from banprofil.profile_chain import ProfileChainError, ProfileChainIndex
from banprofil.trafikverket_gpkg import TrafikverketGeoPackage, TrafikverketGeoPackageError


logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger("banprofil")


def demo_lantmateriet() -> None:
    config_path = Path("config.json")
    if not config_path.exists():
        logger.warning("config.json saknas, hoppar över Lantmäteriet-test.")
        return

    client = LantmaterietClient.from_config_file(config_path)
    result = client.get_height(e=667552, n=6983948, srid=3006)
    print("Lantmäteriet svar:")
    print(json.dumps(result, indent=2, ensure_ascii=False))


def demo_trafikverket() -> None:
    config_path = Path("config.json")
    if not config_path.exists():
        logger.warning("config.json saknas, hoppar över Trafikverket-test.")
        return

    gpkg = TrafikverketGeoPackage.from_config_file(config_path)
    summary = gpkg.summarize_default_layers()
    print("\nTrafikverket standardlager:")
    print(json.dumps(summary[:4], indent=2, ensure_ascii=False))

    sample_rows = gpkg.fetch_named_layer("raklinje", limit=2)
    print("\nExempel från raklinje:")
    print(json.dumps(sample_rows, indent=2, ensure_ascii=False, default=str))

    profile_index = ProfileChainIndex(gpkg)
    forward_view = profile_index.build_forward_view(start_km="1180+200", end_km="1180+320")
    compact_view = {key: value[:2] for key, value in forward_view.items() if value}
    print("\nProfilkedja framåt:")
    print(json.dumps(compact_view, indent=2, ensure_ascii=False, default=str))


def main() -> None:
    try:
        demo_lantmateriet()
        demo_trafikverket()
    except (LantmaterietError, TrafikverketGeoPackageError, ProfileChainError) as exc:
        logger.error("Kunde inte köra demo: %s", exc)
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()
