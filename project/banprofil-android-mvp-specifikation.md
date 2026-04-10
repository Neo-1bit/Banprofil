# Banprofil, sammanhållet projektdokument för Android-baserat förarstöd

## 1. Dokumentets syfte

Detta dokument sammanfattar den rekommenderade inriktningen för Banprofil som en framtida Android-app för diskret förarstöd. Dokumentet fungerar som underlag för fortsatt produktdefinition, UX-arbete och teknisk implementation.

Dokumentet samlar fyra delar i en helhet:

- formell kravspecifikation för MVP
- wireframes i textform
- föreslagen datamodell mellan Banprofil och Android-appen
- rekommenderad genomförandeordning

Målet är att skapa en realistisk första produkt som ger praktisk nytta utan att bli för bred, för tekniskt tung eller säkerhetsmässigt otydlig.

---

## 2. Bakgrund och målbild

Banprofil-projektet har potential att ge förare bättre framförhållning genom att presentera kommande topografi och bana på ett tydligt och lättillgängligt sätt. Den planerade appen ska inte användas för vägval eller säkerhetskritiska beslut. Rutten är redan fastställd av trafikledningen.

Appens huvudsakliga nytta är i stället att stödja:

- energieffektiv körning
- minskat bromsslitage
- mjukare körning
- bättre framförhållning längs en bestämd rutt

Appen ska vara ett sekundärt, diskret informationsstöd. Den ska inte konkurrera med förarens primära uppmärksamhet på signalering, omvärld eller andra säkerhetskritiska informationskällor.

AR och kamera-overlay är därför uttryckligen uteslutna.

---

## 3. Produktprinciper

Följande principer ska styra både MVP och senare utveckling.

### 3.1 Ingen vägvalslogik
Appen ska inte välja väg i nätet. Den ska endast arbeta mot en redan vald eller importerad rutt.

### 3.2 Ingen säkerhetskritisk funktion
Appen ska inte ersätta ordinarie säkerhetsinformation, signalering eller regelstyrda beslutsunderlag.

### 3.3 Diskret presentation
Appen ska vara lågmäld, tydlig och snabb att läsa av. Den ska stödja föraren utan att dra onödig uppmärksamhet.

### 3.4 Ingen AR
Ingen kamera-overlay, ingen augmented reality och ingen visuellt dominant framåtlager över omvärlden.

### 3.5 Fokus på topografi och tågegenskaper
Appens kärna är att kombinera rutt, topografi och tågegenskaper till ett begripligt körstöd.

### 3.6 Offline först
Kärnfunktioner ska fungera utan aktiv nätuppkoppling.

---

## 4. MVP-definition

### 4.1 Produktdefinition

Banprofil MVP är en offline-kapabel Android-app där användaren väljer en fastställd rutt, anger tågets grundparametrar och får en enkel grafisk vy över aktuell position, kommande topografi och kommande bansträckning längs rutten.

### 4.2 Mål med MVP

MVP-versionen ska visa att följande är praktiskt möjligt:

- att representera en fast rutt på ett användbart sätt i mobilen
- att relatera användarens position till rutten
- att visa kommande profil och planvy på ett tydligt sätt
- att använda tågets grundparametrar som del av presentationen
- att göra detta i ett lugnt, diskret och användbart gränssnitt

---

## 5. Formell kravspecifikation, MVP

## 5.1 Funktionella krav

### FR1, val av rutt
Systemet ska låta användaren välja en fastställd rutt ur en lokal eller synkad lista.

### FR2, presentation av ruttmetadata
Systemet ska visa grundläggande information om vald rutt, minst:
- namn eller identifierare
- startpunkt
- slutpunkt
- eventuella mellanpunkter om sådana finns
- ungefärlig längd

### FR3, inmatning av tågegenskaper
Systemet ska låta användaren ange minst följande tåguppgifter:
- största tillåtna hastighet
- tåglängd
- tågvikt

### FR4, lagring av aktiv körning
Systemet ska hålla reda på vald rutt och aktuella tåguppgifter för den aktiva körningen.

### FR5, positionsinhämtning
Systemet ska läsa telefonens tillgängliga positionsdata och använda dem för att uppskatta användarens läge längs vald rutt.

### FR6, ruttprojektion
Systemet ska projicera användarens position mot den valda rutten och beräkna aktuell progress längs rutten.

### FR7, visning av positionsstatus
Systemet ska kunna visa om positioneringen bedöms som god eller osäker.

### FR8, planvy
Systemet ska visa en enkel planvy över aktiv rutt med aktuell position och riktning framåt.

### FR9, profilvy
Systemet ska visa kommande vertikal profil över ett framåtfönster längs rutten.

### FR10, markering av aktuell position i profilen
Systemet ska tydligt markera aktuell position i profilvyn.

### FR11, framåtfönster
Systemet ska stödja ett definierat framåtfönster, initialt minst ett fast standardfönster om 3 km.

### FR12, kommande topografisk förändring
Systemet ska visa avstånd till nästa större topografiska förändring inom framåtfönstret.

### FR13, visning av grundstatus
Systemet ska i huvudvyn visa minst:
- vald rutt
- aktuell progress eller motsvarande lägesangivelse
- aktuell hastighet om tillförlitlig
- tågets angivna maxhastighet

### FR14, offlinefunktion
Systemet ska kunna användas för huvudfunktionerna utan aktiv internetuppkoppling efter att ruttdata finns lokalt.

---

## 5.2 Icke-funktionella krav

### NFR1, låg distraktion
Gränssnittet ska utformas för kort blicktid och låg visuell belastning.

### NFR2, läsbarhet
Text, symboler och grafiska markeringar ska vara tydliga och läsbara under snabb avläsning.

### NFR3, stabilitet
Appen ska fungera stabilt under längre användningspass utan att tappa aktiv rutt eller grundläggande visning.

### NFR4, återhållsam visuell design
Appen ska använda lugn och konsekvent visuell design utan onödiga animationer eller starkt störande färger.

### NFR5, transparens vid osäkerhet
Systemet ska hellre visa osäkerhet än ge sken av exakt precision när underlaget inte räcker.

### NFR6, modularitet
Datahantering, positionering och presentation ska hållas modulärt separerade för att stödja vidare utveckling.

### NFR7, offline först
Appens kärnfunktioner ska inte förutsätta molnberoende i realtid.

---

## 5.3 Avgränsningar för MVP

Följande ska inte ingå i MVP:

- AR
- kamera-overlay
- vägvalsbeslut
- automatisk ruttplanering
- säkerhetskritiska funktioner
- avancerade körrekommendationer
- realtidskoppling till trafikledning
- full energisimulering
- komplex 3D-rendering

---

## 6. Användarflöden

## 6.1 Flöde A, start av körning

1. Användaren öppnar appen.
2. Användaren väljer rutt.
3. Användaren anger tågets maxhastighet, längd och vikt.
4. Appen laddar rutt och profil lokalt.
5. Appen börjar läsa position.
6. Appen projicerar användaren mot rutten.
7. Huvudvyn visas.

## 6.2 Flöde B, aktiv körning

1. Huvudvyn visar aktuell position och framåtfönster.
2. Planvyn visar närmaste del av rutten.
3. Profilvyn visar kommande topografi.
4. Systemet uppdaterar läge och progress fortlöpande.
5. Appen visar nästa större topografiska förändring.
6. Vid låg positionssäkerhet visas detta tydligt men lågmält.

## 6.3 Flöde C, byte av körning

1. Användaren lämnar aktiv körning.
2. Användaren väljer ny rutt eller ändrar tåguppgifter.
3. Appen skapar ny aktiv körning.

---

## 7. Wireframes i textform

## 7.1 Skärm 1, ruttval

### Syfte
Låta användaren välja rätt fastställd rutt.

### Innehåll
- sidtitel: Välj rutt
- sökfält eller filter
- lista med rutter
- varje ruttkort visar:
  - ruttnamn
  - startpunkt
  - slutpunkt
  - mellanpunkter om tillgängligt
  - total längd
- primär knapp: Starta

### Textwireframe

```text
+--------------------------------------------------+
| Välj rutt                                        |
| [ Sök rutt...                             ]      |
|--------------------------------------------------|
| Hallsberg -> Mjölby                              |
| Via: Degerön                                     |
| Längd: 83 km                                     |
| [Välj]                                           |
|--------------------------------------------------|
| Mjölby -> Nässjö                                 |
| Via: Tranås                                      |
| Längd: 96 km                                     |
| [Välj]                                           |
+--------------------------------------------------+
```

---

## 7.2 Skärm 2, tåguppgifter

### Syfte
Låta användaren ange tågets grundparametrar.

### Innehåll
- sidtitel: Tåguppgifter
- inputfält för:
  - maxhastighet
  - längd
  - vikt
- primär knapp: Starta körning

### Textwireframe

```text
+--------------------------------------------------+
| Tåguppgifter                                     |
|--------------------------------------------------|
| Maxhastighet: [ 120 ] km/h                       |
| Längd:        [ 630 ] m                          |
| Vikt:         [ 1850 ] ton                       |
|                                                  |
| [ Starta körning ]                               |
+--------------------------------------------------+
```

---

## 7.3 Skärm 3, huvudvy

### Syfte
Vara den centrala körvyn.

### Innehåll
#### Statusrad
- ruttnamn
- progress längs rutt
- hastighet
- maxhastighet
- positionsstatus

#### Planvy
- enkel karta över närmaste ruttdel
- markering av användarens position
- riktning framåt

#### Profilvy
- kommande topografi över valt framåtfönster
- tydlig markering av aktuell position
- färgkodad eller markerad lutningskaraktär

#### Kort infopanel
- nästa större topografiska förändring
- avstånd dit
- framåtfönstrets längd

### Textwireframe

```text
+--------------------------------------------------+
| Rutt: Hallsberg -> Mjölby                        |
| Pos: 42.3 km   Hast: 118   Max: 120   Status: OK |
|--------------------------------------------------|
|                                                  |
|                 PLANVY / KARTA                   |
|          -----> riktning framåt                  |
|             o aktuell position                   |
|                                                  |
|--------------------------------------------------|
|               PROFIL 3 KM FRAMÅT                 |
|        /
|   ____/  \___       ___                          |
|  /          \_____ /   \__                       |
|        ^ aktuell position                        |
|--------------------------------------------------|
| Nästa förändring: fall börjar om 650 m           |
| Framåtfönster: 3 km                              |
+--------------------------------------------------+
```

---

## 7.4 Skärm 4, detaljvy

### Syfte
Visa utökad information utan att belasta huvudvyn.

### Innehåll
- full ruttöversikt
- längre profil
- tåguppgifter
- sammanfattning av aktiv körning

### Textwireframe

```text
+--------------------------------------------------+
| Körningsdetaljer                                 |
|--------------------------------------------------|
| Rutt: Hallsberg -> Mjölby                        |
| Längd: 83 km                                     |
| Tåg: 120 km/h, 630 m, 1850 ton                  |
|--------------------------------------------------|
| Full profil                                      |
| [----------------------------------------------] |
|--------------------------------------------------|
| Kommande punkter                                 |
| - Fall om 650 m                                  |
| - Stigning om 2.1 km                             |
+--------------------------------------------------+
```

---

## 8. Datamodell mellan Banprofil och Android-appen

## 8.1 Syfte med datamodellen

Datamodellen ska vara tillräckligt enkel för mobil användning men tillräckligt rik för att stödja framtida utveckling. Den ska möjliggöra att Banprofil producerar ruttbaserad data som Android-appen kan läsa lokalt.

Den centrala idén är att appen inte ska behöva bygga rutter från råa nätdata i första hand. Appen bör konsumera färdigpaketerad, ruttbunden data.

---

## 8.2 Grundobjekt

### RouteDefinition
Beskriver en fastställd rutt.

Fält:
- route_id
- name
- start_location
- end_location
- via_points
- total_length_m
- geometry
- profile_segments
- horizontal_segments
- reference_points
- metadata

### TrainProfile
Beskriver användarens tåguppgifter.

Fält:
- train_profile_id
- name, valfritt
- max_speed_kmh
- length_m
- weight_ton
- vehicle_type, valfritt
- metadata

### ActiveRun
Beskriver aktiv körning i appen.

Fält:
- active_run_id
- route_id
- train_profile_id
- started_at
- current_progress_m
- current_position_confidence
- selected_lookahead_m
- direction

---

## 8.3 Geometri- och profilobjekt

### RouteGeometryPoint
Punkt längs ruttens centerlinje.

Fält:
- chainage_m
- lat
- lon
- optional_altitude_m

### ProfileSegment
Vertikalt segment längs rutten.

Fält:
- start_m
- end_m
- start_elevation_m
- end_elevation_m
- gradient_permille, om tillgängligt
- segment_type

Exempel på segment_type:
- uphill
- downhill
- level
- crest_transition
- sag_transition

### HorizontalSegment
Horisontellt avsnitt längs rutten.

Fält:
- start_m
- end_m
- geometry_type
- turn_direction
- optional_radius_m

Exempel på geometry_type:
- straight
- curve
- transition

### ReferencePoint
Viktiga ruttrelaterade punkter.

Fält:
- chainage_m
- label
- category
- metadata

Exempel på category:
- station
- driftplats
- profile_change
- control_point

---

## 8.4 Förslag på JSON-struktur

Ett möjligt första dataformat från Banprofil till appen är JSON, exempelvis en fil per rutt.

```json
{
  "route_id": "route-hallsberg-mjolby",
  "name": "Hallsberg -> Mjölby",
  "start_location": "Hallsberg",
  "end_location": "Mjölby",
  "via_points": ["Degerön"],
  "total_length_m": 83000,
  "geometry": [
    {"chainage_m": 0, "lat": 59.065, "lon": 15.109},
    {"chainage_m": 50, "lat": 59.064, "lon": 15.112}
  ],
  "profile_segments": [
    {
      "start_m": 0,
      "end_m": 800,
      "start_elevation_m": 88.2,
      "end_elevation_m": 93.4,
      "gradient_permille": 6.5,
      "segment_type": "uphill"
    }
  ],
  "horizontal_segments": [
    {
      "start_m": 0,
      "end_m": 1200,
      "geometry_type": "straight",
      "turn_direction": "none"
    }
  ],
  "reference_points": [
    {
      "chainage_m": 0,
      "label": "Hallsberg",
      "category": "station"
    }
  ]
}
```

---

## 8.5 Datapipeline, rekommenderad riktning

### I Banprofil-repot
Banprofil bör producera färdiga ruttpaket som innehåller:
- ruttgeometri
- sammanhängande chainage längs rutt
- profilsegment
- horisontella segment
- relevanta referenspunkter

### I Android-appen
Appen bör:
- läsa ruttpaketet
- lagra det lokalt
- projicera användarens position mot route geometry
- beräkna current_progress_m
- extrahera framåtfönster för profil och planvy

Detta minskar mobil app-komplexitet och gör det lättare att kvalitetssäkra data innan den når användaren.

---

## 9. Rekommenderad teknisk arkitektur för appen

## 9.1 Huvudmoduler

### Route Repository
Ansvarar för att läsa och lagra RouteDefinition lokalt.

### Train Profile Repository
Ansvarar för sparade eller aktiva tåguppgifter.

### Positioning Engine
Ansvarar för:
- GNSS-inhämtning
- kurs och riktning
- projektion mot vald rutt
- confidence-bedömning

### Corridor Engine
Ansvarar för att, utifrån current_progress_m och lookahead, hämta rätt del av:
- geometry
- profile_segments
- horizontal_segments
- reference_points

### Presentation Layer
Ansvarar för:
- planvy
- profilvy
- statusrad
- detaljpanel

### Session State
Ansvarar för aktiv körning och aktuell appstatus.

---

## 10. Genomförandeordning

## Fas 1, datakontrakt

Mål:
Definiera exakt vilket format Banprofil ska exportera till appen.

Leveranser:
- RouteDefinition-schema
- exempelrutter i JSON
- tydlig definition av chainage och segmenttyper

## Fas 2, klickbar UX-prototyp

Mål:
Validera att huvudskärmarna fungerar informationsmässigt.

Leveranser:
- wireframes
- enkel klickbar prototyp
- validerad layout för huvudvy

## Fas 3, första Android-skelett

Mål:
Skapa fungerande appstruktur med lokal dataläsning.

Leveranser:
- ruttvalsskärm
- tåguppgiftsskärm
- huvudvy med dummydata
- detaljvy

## Fas 4, positionering mot rutt

Mål:
Koppla telefonens position till vald rutt.

Leveranser:
- projektion mot route geometry
- current_progress_m
- enkel confidence-logik

## Fas 5, verklig profil- och planvy

Mål:
Visa korrekt utsnitt av data runt aktuell position.

Leveranser:
- profil över aktivt framåtfönster
- planvy med aktiv position
- nästa topografiska förändring

## Fas 6, användbarhetsförfining

Mål:
Göra lösningen lugn, begriplig och stabil.

Leveranser:
- finjusterad layout
- förbättrad läsbarhet
- hantering av osäker position
- bättre detaljvy

---

## 11. Rekommenderade beslut att ta härnäst

Projektet bör härnäst besluta om följande:

1. exakt mapp och dokumentstruktur för produktdokument i repot
2. vilket dataformat Banprofil ska exportera för mobilen
3. hur rutter ska identifieras och versioneras
4. om tåguppgifter ska sparas som profiler eller endast per körning
5. hur positionssäkerhet ska uttryckas i UI
6. om framåtfönstret i MVP ska vara fast eller valbart

---

## 12. Sammanfattning

Den rekommenderade vägen framåt är att utveckla Banprofil som ett diskret, offline-kapabelt Android-förarstöd utan AR, där en redan fastställd rutt kombineras med topografi och tågegenskaper för att ge bättre framförhållning inför energieffektiv och skonsam körning.

MVP:n bör fokusera på:

- ruttval
- inmatning av tåguppgifter
- positionering längs vald rutt
- planvy
- profilvy
- enkel information om nästa topografiska förändring

Den viktigaste arkitekturprincipen är att Banprofil-repot producerar färdiga ruttpaket och att mobilappen konsumerar dessa, i stället för att försöka bygga tung nätlogik på telefonen.

Detta ger den bästa balansen mellan nytta, realism, säkerhetsmässig återhållsamhet och teknisk genomförbarhet.
