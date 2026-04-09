# Banprofil

Banprofil är ett Python-projekt för analys av Trafikverkets järnvägsdata med fokus på `Net_JVG` som nätverksryggrad.

Projektet används för att:
- hitta och verifiera järnvägskorridorer mellan referenspunkter
- exportera KML för visuell kontroll
- analysera nätverkstopologi och connector-problem
- bygga en första höjdprofil längs en verklig järnvägsrutt

## Status

**Version:** `0.1 Alpha`

Det här är en tidig men fungerande alpha.

Det viktigaste som nu fungerar:
- korrekt tolkning av GeoPackageBinary för `Net_JVG_Node`, `Net_JVG_Link` och `Net_JVG_LinkSequence`
- KML-export för level1 och level2 corridor checks
- bakgrunds-KML för nätlagren i level2-området
- första höjdprofil för level1-rutten baserad på `BIS_DK_O_4015_Lutning`
- lokal analys av gap och connector-kandidater
- första `networkx`-baserade grafgrund

## Viktig teknisk lärdom

Den största felkällan tidigt i projektet var **felaktig tolkning av GeoPackage-geometrin**.

Verifierad GeoPackageBinary-header gav:
- `Net_JVG_Node` → `wkb_offset = 8`
- `Net_JVG_Link` → `wkb_offset = 56`
- `Net_JVG_LinkSequence` → `wkb_offset = 56`

När geometrin började läsas korrekt försvann de flesta tidigare "gap" i level1-analysen.

## Projektstruktur

### Kärnmoduler

- `banprofil/net_jvg_resolver.py`
  - matchning av referenspunkter till Net_JVG
  - traversal och constrained routing
- `banprofil/net_jvg_kml.py`
  - export av korridorer och traversaler till KML
- `banprofil/geopackage_geometry.py`
  - korrekt läsning av GeoPackageBinary via verifierad WKB-offset
- `banprofil/gpkg_inspector.py`
  - inspektion av GeoPackage-header och RTree-frågor
- `banprofil/height_profile.py`
  - första höjdprofil längs verifierad korridor
- `banprofil/rail_graph.py`
  - första `networkx`-baserade grafmodell
- `banprofil/local_gap_repair.py`
  - analys av lokala gap mellan ankarssegment
- `banprofil/local_connector_search.py`
  - sökning efter connector-kandidater i lokal korridor

### Exempel och verifiering

- `examples/reference_corridor_visual_check.py`
  - **level1 corridor check**
- `examples/level2_corridor_check.py`
  - första **level2 corridor check**
- `examples/level2_corridor_check_wide.py`
  - bredare level2-variant med större sökfönster
- `examples/export_level2_network_layers_kml.py`
  - KML per nätlager i level2-området
- `examples/level1_height_profile.py`
  - bygger första höjdprofilen för level1

## Nuvarande arbetssätt

1. Matcha referenspunkter mot `Net_JVG_Node`
2. Bygg och verifiera korridor med KML
3. Kontrollera korridoren visuellt
4. Förfina routing eller urval om korridoren inte är giltig
5. Bygg höjdprofil längs verifierad korridor

## Filer med verifierad nytta just nu

### Behåll

- `examples/reference_corridor_visual_check.kml`
- `examples/level2_corridor_check.kml`
- `examples/level2_corridor_check_wide.kml`
- `examples/level1_height_profile.json`
- `examples/level1_height_profile.csv`
- `examples/level2_network_layers/Net_JVG_Link.kml`
- `examples/level2_network_layers/Net_JVG_Node.kml`
- `examples/level2_network_layers/Net_JVG_LinkSequence.kml`

### Historiska eller sekundära debugfiler

Äldre proof-of-concept-KML:er kan tas bort eller arkiveras när de inte längre behövs.

## Nästa steg

- förbättra routing längs verklig bana i svårare level2-fall
- låta bbox/RTree-urval växa adaptivt när koppling saknas
- förbättra höjdprofilen med bättre projektion mot linjen, inte bara närmaste vertex
- integrera `Vertikalkurva` och fler vertikalgeometriska lager
- förfina hur profilkedjan byggs längs hela korridoren

## Utvecklingsprincip

Projektet bygger på en viktig princip:

> Det måste vara tillåtet att göra fel, för det är så vi lär oss att göra rätt.

Det har redan visat sig sant i Banprofil. Många tidiga antaganden var fel, men varje fel ledde till bättre förståelse av både järnvägsnätet och GeoPackage-datan.
