from __future__ import annotations

import json
import logging
from dataclasses import asdict

from banprofil.feature_projection import FeatureProjector
from banprofil.master_network_analyzer import MasterNetworkAnalyzer
from banprofil.net_jvg_resolver import NetJvgResolver


logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger("banprofil")


def demo_master_network_analysis() -> None:
    """
    Kör en första analys av masterpaketets nätverksstruktur.

    Returns
    -------
    None
        Funktionen skriver analysresultat till standard output.
    """
    analyzer = MasterNetworkAnalyzer.from_config_file()
    print("\nMaster network tables:")
    print(json.dumps([asdict(item) for item in analyzer.summarize_network_tables()], indent=2, ensure_ascii=False, default=str))
    print("\nMaster chain parents:")
    print(json.dumps([asdict(item) for item in analyzer.summarize_chain_parents()], indent=2, ensure_ascii=False, default=str))
    print("\nRekommenderad chain key-strategi:")
    print(json.dumps(analyzer.recommend_chain_key_strategy(), indent=2, ensure_ascii=False))



def demo_net_jvg_resolver() -> None:
    """
    Kör första nätverksförst-resolvern för Net_JVG-lagren.

    Returns
    -------
    None
        Funktionen skriver nätverkssammanfattning och traversalexempel till standard output.
    """
    resolver = NetJvgResolver.from_config_file()
    summary = resolver.summarize_network()
    print("\nNet_JVG network summary:")
    print(json.dumps(asdict(summary), indent=2, ensure_ascii=False))
    links = resolver.load_links(limit=1)
    traversal = resolver.traverse_from_node(start_node_oid=links[0].start_node_oid, target_length_m=50000.0)
    print("\nNet_JVG traversal v1:")
    print(json.dumps(asdict(traversal), indent=2, ensure_ascii=False))
    print("\nNet_JVG next steps:")
    print(json.dumps(resolver.recommend_next_steps(), indent=2, ensure_ascii=False))



def demo_feature_projection() -> None:
    """
    Kör första feature projection ovanpå traverserad Net_JVG-korridor.

    Returns
    -------
    None
        Funktionen skriver kandidatstatistik till standard output.
    """
    resolver = NetJvgResolver.from_config_file()
    links = resolver.load_links(limit=1)
    traversal = resolver.traverse_from_node(start_node_oid=links[0].start_node_oid, target_length_m=50000.0)
    projector = FeatureProjector.from_config_file()
    projected = projector.project_features_from_traversal(traversal)
    print("\nFeature projection v2:")
    print(json.dumps([asdict(item) for item in projected], indent=2, ensure_ascii=False))



def main() -> None:
    """
    Kör fokuserade demoexempel för master- och Net_JVG-arkitekturen.

    Returns
    -------
    None
        Funktionen skriver resultat från analyser och traversal till standard output.
    """
    demo_master_network_analysis()
    demo_net_jvg_resolver()
    demo_feature_projection()


if __name__ == "__main__":
    main()
