# Banprofil

Python-modul för kommunikation med Lantmäteriets Markhöjd Direkt API.

## Innehåll

- `banprofil/lantmateriet_client.py` - klient för tokenhämtning och höjdanrop
- `config.example.json` - mall för credentials och API-inställningar
- `.gitignore` - skyddar lokala hemligheter

## Kom igång

1. Kopiera `config.example.json` till `config.json`
2. Fyll i `consumer_key` och `consumer_secret`
3. Installera beroenden:

```bash
pip install requests
```

## Exempel

```python
from banprofil.lantmateriet_client import LantmaterietClient

client = LantmaterietClient.from_config_file("config.json")
height = client.get_height(e=667552, n=6983948, srid=3006)
print(height)
```
