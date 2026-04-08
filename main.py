from __future__ import annotations

import json
import logging
from pathlib import Path

from banprofil.lantmateriet_client import LantmaterietClient, LantmaterietError
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
    gpkg_path = Path("../filelibrary/trafikverket/Trafikverket_Sweref_Geopackage_677446/Trafikverket_Sweref_677446.gpkg")
    if not gpkg_path.exists():
        logger.warning("Trafikverket GeoPackage saknas, hoppar över GeoPackage-test.")
        return

    gpkg = TrafikverketGeoPackage(gpkg_path)
    summary = gpkg.summarize_default_layers()
    print("\nTrafikverket standardlager:")
    print(json.dumps(summary[:3], indent=2, ensure_ascii=False))

    sample_rows = gpkg.fetch_named_layer("raklinje", limit=2)
    print("\nExempel från raklinje:")
    print(json.dumps(sample_rows, indent=2, ensure_ascii=False, default=str))


def main() -> None:
    try:
        demo_lantmateriet()
        demo_trafikverket()
    except (LantmaterietError, TrafikverketGeoPackageError) as exc:
        logger.error("Kunde inte köra demo: %s", exc)
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()
