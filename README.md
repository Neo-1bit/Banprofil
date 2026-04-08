# Banprofil

Python-modul för kommunikation med Lantmäteriets Markhöjd Direkt API och läsning av Trafikverkets GeoPackage-data.

## Innehåll

- `banprofil/lantmateriet_client.py` - klient för tokenhämtning, höjdanrop, batchstöd och felhantering
- `banprofil/coordinate_transform.py` - omvandling från WGS84 (EPSG:4326) till SWEREF 99 TM (EPSG:3006)
- `banprofil/trafikverket_gpkg.py` - läsare för Trafikverkets GeoPackage-lager
- `banprofil/profile_chain.py` - km-tal och profilkedja längs spåret
- `main.py` - enkel körbar testfil
- `config.example.json` - mall för credentials och lokala datakällor
- `.gitignore` - skyddar lokala hemligheter

## Kom igång

1. Kopiera `config.example.json` till `config.json`
2. Fyll i `consumer_key` och `consumer_secret`
3. Uppdatera `trafikverket_gpkg_path` eller `trafikverket_gpkg_glob` så att den pekar på din lokala GeoPackage-fil
4. Installera beroenden:

```bash
pip install requests
```

## Konfiguration

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

## Exempel, läs Trafikverkets GeoPackage

```python
from banprofil.trafikverket_gpkg import TrafikverketGeoPackage

gpkg = TrafikverketGeoPackage.from_config_file("config.json")
summary = gpkg.summarize_default_layers()
raklinjer = gpkg.fetch_named_layer("raklinje", limit=5)
```

## Exempel, bygg framåtvyn längs spåret

```python
from banprofil.profile_chain import ProfileChainIndex
from banprofil.trafikverket_gpkg import TrafikverketGeoPackage

gpkg = TrafikverketGeoPackage.from_config_file("config.json")
profile_index = ProfileChainIndex(gpkg)

forward_view = profile_index.build_forward_view(
    start_km="1180+200",
    end_km="1180+320",
)
```

Det här ger ett första skelett för att beskriva vad som finns framför tåget på en viss sträcka, till exempel:
- raklinjer
- cirkulärkurvor
- övergångskurvor
- vertikalkurvor
- lutningar
- rälsförhöjning

## Om höjddata

Trafikverkets GeoPackage innehåller redan höjdrelaterad information i flera lager, till exempel:
- `Koordinater_start` och `Koordinater_slut` med Z-värden i:
  - `raklinje`
  - `cirkularkurva`
  - `overgangskurva`
  - `vertikalkurva`
  - `lutning`
- `Lutning_promille` i `lutning`
- `Ralsforhojning_i_startpkt` och `Ralsforhojning_i_slutpkt` i `ralsforhojning`

Det gör att Trafikverkets data bör vara primär källa för banans vertikalgeometri där den finns. Lantmäteriet passar bra som komplettering där Trafikverkets data saknas eller behöver fyllas ut mellan objekt.

## Kör testfilen

```bash
python main.py
```
