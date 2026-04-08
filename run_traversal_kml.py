from __future__ import annotations

from pathlib import Path

from banprofil.net_jvg_kml import export_traversal_kml
from banprofil.net_jvg_resolver import NetJvgResolver


def main() -> None:
    """
    Exporterar en ren debug-KML för traverserad Net_JVG-korridor.

    Returns
    -------
    None
        Skriver sökvägen till skapad KML-fil.
    """
    resolver = NetJvgResolver.from_config_file()
    links = resolver.load_links(limit=1)
    traversal = resolver.traverse_from_node(start_node_oid=links[0].start_node_oid, target_length_m=50000.0)
    output = export_traversal_kml(
        resolver,
        traversal,
        Path("examples") / "net_jvg_traversal_debug.kml",
        name="Net_JVG Traversal Debug",
    )
    print(output)


if __name__ == "__main__":
    main()
