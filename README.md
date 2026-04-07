# Banprofil

Python-modul för kommunikation med Lantmäteriets Markhöjd Direkt API.

## Innehåll

- `banprofil/lantmateriet_client.py` - klient för tokenhämtning, höjdanrop, batchstöd och felhantering
- `banprofil/coordinate_transform.py` - omvandling från WGS84 (EPSG:4326) till SWEREF 99 TM (EPSG:3006)
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

## Exempel, omvandla från WGS84 och hämta höjd

```python
from banprofil.lantmateriet_client import LantmaterietClient

client = LantmaterietClient.from_config_file("config.json")
result = client.get_height_from_wgs84(latitude=63.32080149399089, longitude=18.760988434450987)
print(result)
```

## Exempel, flera punkter

```python
from banprofil.lantmateriet_client import LantmaterietClient

client = LantmaterietClient.from_config_file("config.json")
results = client.get_many_heights([
    {"e": 667552, "n": 6983948, "srid": 3006},
    {"latitude": 63.32080149399089, "longitude": 18.760988434450987},
])
print(results)
```

## Kör testfilen

```bash
python main.py
```
