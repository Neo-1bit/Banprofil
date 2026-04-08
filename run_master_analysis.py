from __future__ import annotations

import json
from dataclasses import asdict

from banprofil.master_network_analyzer import MasterNetworkAnalyzer


def main() -> None:
    """
    Kör masteranalys som fristående entry point.

    Returns
    -------
    None
        Skriver resultat till standard output.
    """
    analyzer = MasterNetworkAnalyzer.from_config_file()
    print("Master network tables:")
    print(json.dumps([asdict(item) for item in analyzer.summarize_network_tables()], indent=2, ensure_ascii=False, default=str))
    print("\nMaster chain parents:")
    print(json.dumps([asdict(item) for item in analyzer.summarize_chain_parents()], indent=2, ensure_ascii=False, default=str))
    print("\nRecommended chain key strategy:")
    print(json.dumps(analyzer.recommend_chain_key_strategy(), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
