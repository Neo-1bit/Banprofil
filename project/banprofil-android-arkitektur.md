# Banprofil, hög nivå för Android-arkitektur

## 1. Syfte

Detta dokument beskriver en rekommenderad hög-nivå-arkitektur för en framtida Android-app för Banprofil.

Arkitekturen ska stödja:
- offline-funktion
- tydlig separation mellan data, positionering och presentation
- stegvis utveckling från MVP till mer avancerat stöd

---

## 2. Arkitekturöversikt

Appen bör delas upp i följande huvuddelar:

1. Route Repository
2. Train Profile Repository
3. Positioning Engine
4. Corridor Engine
5. Presentation Layer
6. Session State

---

## 3. Moduler

## 3.1 Route Repository
Ansvarar för:
- inläsning av ruttfiler
- lokal lagring
- versionshantering av rutter
- åtkomst till route geometry, profile segments och reference points

## 3.2 Train Profile Repository
Ansvarar för:
- lagring av tåguppgifter
- val av aktiv tåguppsättning
- eventuell framtida hantering av sparade fordonsprofiler

## 3.3 Positioning Engine
Ansvarar för:
- GNSS-position
- riktning och hastighet när tillgängligt
- projektion mot vald rutt
- positionssäkerhet

Input:
- telefonens position och rörelsedata
- aktiv rutt

Output:
- current_progress_m
- direction
- position_confidence

## 3.4 Corridor Engine
Ansvarar för att utifrån aktiv position extrahera relevant utsnitt av rutten.

Input:
- route definition
- current_progress_m
- selected_lookahead_m

Output:
- geometry slice
- profile slice
- horizontal slice
- next major change

## 3.5 Presentation Layer
Ansvarar för:
- ruttvalsskärm
- tåguppgiftsskärm
- huvudvy
- detaljvy

Denna del ska enbart konsumera färdig app-state och inte innehålla tung domänlogik.

## 3.6 Session State
Ansvarar för:
- aktiv körning
- vald rutt
- tåguppgifter
- lookahead
- aktuell positioneringsstatus

---

## 4. Rekommenderad teknikstack

- Kotlin
- Jetpack Compose
- lokal lagring, exempelvis Room eller enkel filbaserad cache beroende på MVP-omfång
- kartkomponent med MapLibre eller liknande

---

## 5. Dataflöde

1. användaren väljer rutt
2. appen laddar RouteDefinition
3. användaren anger tåguppgifter
4. Session State skapar aktiv körning
5. Positioning Engine läser GNSS-data
6. position projiceras mot rutten
7. Corridor Engine hämtar aktivt utsnitt
8. Presentation Layer visar karta, profil och status

---

## 6. Arkitekturprinciper

- håll domänlogik utanför UI
- låt appen konsumera färdigpaketerad ruttdata
- bygg med tydliga kontrakt mellan moduler
- visa osäkerhet öppet i stället för att gissa för hårt
- optimera för läsbarhet och stabilitet före avancerad grafik

---

## 7. Rekommenderad utvecklingsordning

1. datakontrakt och modellobjekt
2. UI med dummydata
3. lokal lagring och inläsning av riktiga rutter
4. positionering mot rutt
5. profil- och planvy med aktiv data
6. förfining av positionslogik och UX
