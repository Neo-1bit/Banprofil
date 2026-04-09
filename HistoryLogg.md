# HistoryLogg.md

Det här dokumentet är projektets dagbok.

Syftet är att hjälpa framtida utvecklare att förstå:
- vad som har provats
- vad som fungerade
- vad som inte fungerade
- vilka misstag som inte bör upprepas

---

## 2026-04-08 till 2026-04-09, första stora genombrottet

### Grundidé

Banprofil ska analysera en verklig järnvägskorridor och senare kunna visa hur banan ser ut framåt, inklusive höjdprofil.

Tidigt stod det klart att projektet måste vara **nätverksförst**:
- `Net_JVG_Node`
- `Net_JVG_Link`
- `Net_JVG_LinkSequence`

Dessa ska vara ryggraden.

---

## Viktiga tidiga lärdomar

### 1. Km-tal räcker inte som nyckel

Det blev tidigt tydligt att km-tal **inte är globalt unika** i Trafikverkets data.

Samma km-tal eller km-intervall kan återkomma i olika geografier.

**Konsekvens:**
Man kan inte bygga kedjor eller profiler bara utifrån km-tal.

**Praktisk lärdom:**
Knyt alltid analysen till verklig geometri och nätverk, inte bara till textfält som ser kedjelika ut.

---

### 2. Net_JVG måste vara ryggrad, inte BIS-featurelager

Ett tidigare spår var mer feature-först, där objekt som `Raklinje`, `Lutning` och andra lager stod i centrum.

Det ledde till att projektet saknade en stabil topologisk bas.

**Beslut:**
Arkitekturen städades om till **Net_JVG-först**.

**Konsekvens:**
Alla viktiga analyser ska först hitta eller verifiera en korridor i `Net_JVG`, och sedan projicera andra lager ovanpå den.

---

## Misstag som kostade mycket tid

### 3. Felaktig tolkning av GeoPackage-geometri

Detta var den största felkällan hittills.

Under en lång period tydde analyserna på att level1-rutten hade flera stora gap. Det ledde till:
- constrained routing
- lokal gap-analys
- connector-sökning
- repair graph-idéer
- teorier om trasig eller ofullständig data

Mycket av detta byggde på ett dolt grundfel:

> GeoPackageBinary för `Net_JVG_Link` och `Net_JVG_LinkSequence` lästes fel.

Den tidigare handskrivna dekodningen antog i praktiken fel offset för WKB-delen och gav därmed alltför korta eller felaktigt tolkade geometrier.

### Det som till slut verifierades

GeoPackage-inspektion visade:
- `Net_JVG_Node` → `wkb_offset = 8`
- `Net_JVG_Link` → `wkb_offset = 56`
- `Net_JVG_LinkSequence` → `wkb_offset = 56`

När geometrierna började läsas korrekt med verifierad header + WKB försvann de flesta tidigare "gapen" i level1.

**Praktisk regel för framtiden:**
- skriv inte fler sköra byte-offset-hack för GeoPackageBinary om det går att undvika
- verifiera alltid header, envelope och WKB-offset först
- använd en dedikerad geometrihjälpare

---

## Visualisering som metod

### 4. Visuell kontroll var avgörande

Användarens visuella kontroll av KML visade flera gånger att något var fel långt innan koden själv kunde bevisa det.

Det räddade projektet från att gå djupare in i falska antaganden.

**Lärdom:**
Bygg KML tidigt och ofta.

### KML-spår som etablerades

- **level1 corridor check** blev första stabila referensen
- **level2 corridor check** blev avsiktligt svårare testfall
- bakgrunds-KML för nätlagren i level2 hjälper till att se om traversal och urval verkligen följer datat

---

## Level1 och level2

### 5. Level1 blev första verifierade korridoren

När GeoPackageBinary lästes korrekt blev level1 visuellt trovärdig och tillräckligt stabil för vidare analys.

Det möjliggjorde:
- bättre KML
- första höjdprofil
- större tillit till projektets grund

### 6. Level2 är fortfarande det bättre stresstestet

Level2 ser ut att ligga på rätt korridor, men glapp kan fortfarande uppstå.

Det betyder att level2 är värdefullt som nästa svårare fall.

**Lärdom:**
Behåll både level1 och level2.
- level1 = verifierad fungerande korridor
- level2 = svårare test som avslöjar svagheter i routing eller urval

---

## Nätverk, graf och topologi

### 7. Ett grafbibliotek hjälpte tänkandet även när datat var ofullständigt

`networkx` installerades och en första grafmodell byggdes.

Det gav viktiga insikter:
- nätet såg fragmenterat ut
- många länkar verkade sakna noder
- strikt grafväg saknades i vissa fall

En del av detta var påverkat av geometritolkningsproblem, men arbetet var ändå värdefullt.

**Lärdom:**
Ett grafverktyg är fortfarande rätt väg, men geometri- och topologitolkningen måste vara korrekt först.

---

## GeoPackage och RTree

### 8. RTree-indexen finns redan i datat och ska användas

`gpkg_extensions` visade att:
- `Net_JVG_Link`
- `Net_JVG_Node`
- `Net_JVG_LinkSequence`

alla har `gpkg_rtree_index`.

Det betyder att lokal extraktion inte ska fullscanna hela lagren om det går att undvika.

**Lärdom:**
Använd RTree för:
- lokala KML-exporter
- korridoruttag
- höjdprofilens kandidatsökning
- framtida adaptiv sökning

---

## Höjdprofilen

### 9. Första höjdprofilen byggdes från `BIS_DK_O_4015_Lutning`

Efter att level1 stabiliserats byggdes första verkliga höjdprofilen längs korridoren.

Den:
- använder den korrigerade level1-rutten
- använder `Lutning`-lagret
- projicerar objektens start/slutpunkter mot korridoren
- begränsar sökningen med RTree

Resultatet blev:
- cirka 28.1 km rutt
- 155 profilpunkter
- första visuellt trovärdiga höjdprofilen

**Lärdom:**
Det går att få användbara profiler redan innan all kedjlogik är perfekt, om korridoren först är tillräckligt verifierad.

---

## Vad som bör göras framöver

### 10. Undvik att upprepa följande misstag

Gör inte detta igen utan stark verifiering:
- anta att data har gap bara för att KML visar gap
- anta att kort bytekodstolkning är rätt utan headerverifiering
- anta att rak bbox mellan två punkter är tillräcklig när verklig järnväg går i båge
- anta att km-tal ensamt kan identifiera en profilkedja

### 11. Rekommenderat arbetssätt framåt

1. verifiera geometri först
2. bygg visuell KML för kontroll
3. verifiera korridor mot verkligheten
4. projicera features ovanpå verifierad korridor
5. bygg höjdprofil
6. först därefter förfina routing/logik för svårare fall

---

## Projektets arbetsprincip

En viktig princip formulerades under arbetet och bör bevaras:

> Det måste vara tillåtet att göra fel, för det är så vi lär oss att göra rätt.

Det här dokumentet finns just därför.
