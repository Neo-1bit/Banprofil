from __future__ import annotations

import json
from dataclasses import asdict

from banprofil.net_jvg_resolver import NetJvgResolver


def main() -> None:
    """
    Kör traversal-demo som fristående entry point.

    Returns
    -------
    None
        Skriver traversalresultat till standard output.
    """
    resolver = NetJvgResolver.from_config_file()
    summary = resolver.summarize_network()
    print("Net_JVG network summary:")
    print(json.dumps(asdict(summary), indent=2, ensure_ascii=False))
    links = resolver.load_links(limit=1)
    traversal = resolver.traverse_from_node(start_node_oid=links[0].start_node_oid, target_length_m=50000.0)
    print("\nNet_JVG traversal:")
    print(json.dumps(asdict(traversal), indent=2, ensure_ascii=False))
    print("\nNext steps:")
    print(json.dumps(resolver.recommend_next_steps(), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
