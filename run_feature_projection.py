from __future__ import annotations

import json
from dataclasses import asdict

from banprofil.feature_projection import FeatureProjector
from banprofil.net_jvg_resolver import NetJvgResolver


def main() -> None:
    """
    Kör feature projection som fristående entry point.

    Returns
    -------
    None
        Skriver projectionsresultat till standard output.
    """
    resolver = NetJvgResolver.from_config_file()
    links = resolver.load_links(limit=1)
    traversal = resolver.traverse_from_node(start_node_oid=links[0].start_node_oid, target_length_m=50000.0)
    projector = FeatureProjector.from_config_file()
    projected = projector.project_features_from_traversal(traversal)
    print("Feature projection:")
    print(json.dumps([asdict(item) for item in projected], indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
