from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

from banprofil.height_profile import HeightProfileBuilder
from banprofil.net_jvg_resolver import NetJvgResolver


def main() -> None:
    """
    Bygger första höjdprofil för level1-rutten.

    Returns
    -------
    None
        Skriver profilfilernas sökvägar och enkel statistik.
    """
    resolver = NetJvgResolver.from_config_file()
    builder = HeightProfileBuilder.from_config_file()

    point1 = resolver.match_reference_point_to_node(664502.0, 7037403.0)
    point2 = resolver.match_reference_point_to_node(643473.0, 7031542.0)
    traversal = resolver.route_between_nodes_constrained(point1.node_oid, point2.node_oid)
    profile = builder.build_from_traversal(traversal, max_offset_m=150.0)

    output_json = Path("examples") / "level1_height_profile.json"
    output_json.write_text(json.dumps(asdict(profile), indent=2, ensure_ascii=False), encoding="utf-8")

    output_csv = Path("examples") / "level1_height_profile.csv"
    lines = ["distance_m,elevation_m,source,description"]
    for point in profile.points:
        description = point.description.replace('"', '""')
        lines.append(f'{point.distance_m:.3f},{point.elevation_m:.3f},{point.source},"{description}"')
    output_csv.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(output_json)
    print(output_csv)
    print(f"Ruttlängd {profile.route_length_m:.2f} m")
    print(f"Profilpunkter {len(profile.points)}")
    print(profile.notes)


if __name__ == "__main__":
    main()
