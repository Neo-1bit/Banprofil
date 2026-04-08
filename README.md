# Banprofil

Python-modul för kommunikation med Lantmäteriets Markhöjd Direkt API och läsning av Trafikverkets GeoPackage-data.

## Innehåll

- `banprofil/lantmateriet_client.py` - klient för tokenhämtning, höjdanrop, batchstöd och felhantering
- `banprofil/coordinate_transform.py` - omvandling från WGS84 (EPSG:4326) till SWEREF 99 TM (EPSG:3006)
- `banprofil/trafikverket_gpkg.py` - läsare för Trafikverkets GeoPackage-lager
- `banprofil/profile_chain.py` - km-tal och profilkedja längs spåret
- `main.py` - enkel körbar testfil
- `config.example.json` - mall för credentials och API-inställningar
- `.gitignore` - skyddar lokala hemligheter

## Kom igång

1. Kopiera `config.example.json` till `config.json`
2. Fyll i `consumer_key` och `consumer_secret`
3. Installera beroenden:

```bash
pip install requests
```

## Exempel, en punkt i SWEREF 99 TM

```python
from banprofil.lantmateriet_client import LantmaterietClient

client = LantmaterietClient.from_config_file("config.json")
height = client.get_elevation_value(e=667552, n=6983948, srid=3006)
print(height)
```

## Exempel, läs Trafikverkets GeoPackage

```python
from banprofil.trafikverket_gpkg import TrafikverketGeoPackage

gpkg = TrafikverketGeoPackage("../filelibrary/trafikverket/Trafikverket_Sweref_Geopackage_677446/Trafikverket_Sweref_677446.gpkg")
summary = gpkg.summarize_default_layers()
raklinjer = gpkg.fetch_named_layer("raklinje", limit=5)
```

## Exempel, bygg framåtvyn längs spåret

```python
from banprofil.profile_chain import ProfileChainIndex
from banprofil.trafikverket_gpkg import TrafikverketGeoPackage

gpkg = TrafikverketGeoPackage("../filelibrary/trafikverket/Trafikverket_Sweref_Geopackage_677446/Trafikverket_Sweref_677446.gpkg")
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

## Kör testfilen

```bash
python main.py
```
