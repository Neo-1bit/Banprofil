# Banprofil

Python-modul för kommunikation med Lantmäteriets Markhöjd Direkt API och läsning av Trafikverkets GeoPackage-data.

## Innehåll

- `banprofil/lantmateriet_client.py` - klient för tokenhämtning, höjdanrop, batchstöd och felhantering
- `banprofil/coordinate_transform.py` - omvandling från WGS84 (EPSG:4326) till SWEREF 99 TM (EPSG:3006)
- `banprofil/trafikverket_gpkg.py` - läsare för Trafikverkets GeoPackage-lager
- `banprofil/profile_chain.py` - km-tal och profilkedja längs spåret
- `banprofil/height_profile.py` - bygger höjdprofil med Trafikverket som primär källa och Lantmäteriet som fallback
- `banprofil/config_loader.py` - laddar `config.json` och faller tillbaka till `config.example.json`
- `main.py` - enkel körbar testfil
- `config.example.json` - mall för credentials och lokala datakällor
- `.gitignore` - skyddar lokala hemligheter

## Konfiguration

- `config.json` används om den finns
- annars används `config.example.json` som fallback
- `config.json` är ignorerad i git och är avsedd för riktiga lokala nycklar och filvägar

Exempel:

```json
{
  "consumer_key": "...",
  "consumer_secret": "...",
  "trafikverket_gpkg_path": "C:/data/trafikverket/Trafikverket_Sweref_677446.gpkg",
  "trafikverket_gpkg_glob": "C:/data/trafikverket/**/*.gpkg"
}
```

Tips:
- använd `trafikverket_gpkg_path` om du vet exakt filnamn
- använd `trafikverket_gpkg_glob` om filnamnet ändras vid varje ny leverans, då väljs senaste matchande `.gpkg`

## Exempel, höjdprofil

```python
from banprofil.height_profile import HeightProfileBuilder

builder = HeightProfileBuilder.from_config_file("config.json")
profile = builder.build_height_profile(start_km="1180+200", end_km="1180+320")
```

Varje sample i profilen innehåller bland annat:
- km-tal
- e, n
- z
- källa (`trafikverket` eller `lantmateriet`)
- metadata som lutning eller radie där det finns

## Data-prioritet

Höjdprofilen prioriterar:
1. **Trafikverket**, via Z-värden i `Koordinater_start` och `Koordinater_slut`
2. **Lantmäteriet**, som fallback om Trafikverket saknar höjd för en punkt

Det här är en bra grund för att visa hur spåret ser ut framför ett tåg på en given sträcka.

## Kör testfilen

```bash
python main.py
```
