from __future__ import annotations

import json
import logging
from dataclasses import asdict
from pathlib import Path

from banprofil.height_profile import HeightProfileBuilder
from banprofil.kml_export import export_height_profile_kml
from banprofil.lantmateriet_client import LantmaterietClient, LantmaterietError
from banprofil.profile_chain import ProfileChainError, ProfileChainIndex
from banprofil.trafikverket_gpkg import TrafikverketGeoPackage, TrafikverketGeoPackageError


logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger("banprofil")


def demo_lantmateriet() -> None:
    """
    Kör ett enkelt exempelanrop mot Lantmäteriet.

    Returns
    -------
    None
        Funktionen skriver resultatet till standard output.
    """
    client = LantmaterietClient.from_config_file()
    result = client.get_height(e=667552, n=6983948, srid=3006)
    print("Lantmäteriet svar:")
    print(json.dumps(result, indent=2, ensure_ascii=False))


def demo_trafikverket() -> None:
    """
    Visar grundläggande exempel med Trafikverkets GeoPackage.

    Returns
    -------
    None
        Funktionen skriver lageröversikt och exempeldata till standard output.
    """
    gpkg = TrafikverketGeoPackage.from_config_file()
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


def demo_height_profile() -> None:
    """
    Visar exempel på höjdprofil och höjdsegment.

    Returns
    -------
    None
        Funktionen skriver profiler och segment till standard output.
    """
    builder = HeightProfileBuilder.from_config_file()
    profile = builder.build_height_profile(start_km="1180+200", end_km="1180+320")
    serializable = [asdict(sample) for sample in profile[:8]]
    print("\nHöjdprofil:")
    print(json.dumps(serializable, indent=2, ensure_ascii=False, default=str))

    segments = builder.build_height_segments(start_km="1180+200", end_km="1180+320")
    print("\nHöjdsegment:")
    print(json.dumps([asdict(segment) for segment in segments[:5]], indent=2, ensure_ascii=False, default=str))


def demo_kml_export() -> None:
    """
    Exporterar proof-of-concept-KML för cirka 50 km järnväg.

    Returns
    -------
    None
        Funktionen skriver sökvägen till skapad KML-fil.
    """
    builder = HeightProfileBuilder.from_config_file()
    profile = builder.build_height_profile(start_km="75+935", end_km="125+935")
    segments = builder.build_height_segments(start_km="75+935", end_km="125+935")
    output = export_height_profile_kml(
        profile,
        Path("examples") / "proof_of_concept_50km.kml",
        segments=segments,
    )
    print(f"\nKML exporterad till: {output}")


def main() -> None:
    """
    Kör alla demoexempel för projektet.

    Returns
    -------
    None
        Funktionen avslutar processen med felkod vid undantag.

    Raises
    ------
    SystemExit
        Om någon av demo-funktionerna misslyckas.
    """
    try:
        demo_lantmateriet()
        demo_trafikverket()
        demo_height_profile()
        demo_kml_export()
    except (LantmaterietError, TrafikverketGeoPackageError, ProfileChainError) as exc:
        logger.error("Kunde inte köra demo: %s", exc)
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()
