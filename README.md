# Banprofil

Python-modul för analys av Trafikverkets järnvägsnät med fokus på `Net_JVG` som topologisk ryggrad.

## Innehåll

- `banprofil/config_loader.py` - laddar `config.json` och faller tillbaka till `config.example.json`
- `banprofil/coordinate_transform.py` - omvandling från WGS84 (EPSG:4326) till SWEREF 99 TM (EPSG:3006)
- `banprofil/trafikverket_gpkg.py` - generell läsare för Trafikverkets GeoPackage-lager
- `banprofil/master_network_analyzer.py` - analys av masterpaketets nätverk och föräldralager
- `banprofil/net_jvg_resolver.py` - nätverksförst-resolver och traversal över `Net_JVG`
- `banprofil/feature_projection.py` - första projektion av featurelager ovanpå traverserad `Net_JVG`-korridor
- `main.py` - fokuserad demo för masteranalys, traversal och feature projection

## Konfiguration

- `config.json` används om den finns
- annars används `config.example.json` som fallback
- `config.json` är ignorerad i git och är avsedd för riktiga lokala filvägar

Exempel:

```json
{
  "trafikverket_gpkg_path": "C:/data/trafikverket/master/Master_All_194445.gpkg",
  "trafikverket_gpkg_glob": "C:/data/trafikverket/master/**/*.gpkg"
}
```

## Arkitektur just nu

Projektet utgår nu från expertbekräftad modell:
- `Net_JVG_*` är själva järnvägsnätet
- övriga BIS-lager är features på nätverket

Det betyder att Banprofil nu bygger vidare på:
1. `Net_JVG_Node`
2. `Net_JVG_Link`
3. `Net_JVG_LinkSequence`

Och först därefter projiceras featurelager som:
- `raklinje`
- `lutning`
- `cirkularkurva`
- `overgangskurva`

## Demo

```bash
python main.py
```

Det kör:
- master network analysis
- `Net_JVG` traversal v1
- feature projection v2

## Nästa steg

- traversal längs bättre vald korridor än första startnod
- exakt projektion av featuresegment mot traverserade länkar
- senare återkoppling till höjdprofil och exportformat ovanpå korrekt nätverkskedja
