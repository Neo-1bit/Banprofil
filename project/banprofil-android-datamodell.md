# Banprofil, datamodell mellan Banprofil och Android-appen

## 1. Syfte

Detta dokument beskriver den rekommenderade datamodellen mellan Banprofil och en framtida Android-app. Målet är att Banprofil ska exportera färdiga ruttpaket som mobilappen kan läsa lokalt utan att själv behöva bygga tunga nätanalyser från rådata.

---

## 2. Grundprincip

Mobilappen ska arbeta mot färdigpreparerade ruttdefinitioner. Varje rutt ska beskrivas som en sammanhängande kedja med gemensamt avståndsmått, så att geometri, profil och referenspunkter kan relateras till samma chainage.

---

## 3. Kärnobjekt

## 3.1 RouteDefinition
Beskriver en körbar rutt.

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
- version
- metadata

## 3.2 TrainProfile
Beskriver tågets grundegenskaper.

Fält:
- train_profile_id
- name
- max_speed_kmh
- length_m
- weight_ton
- vehicle_type
- metadata

## 3.3 ActiveRun
Beskriver aktiv körning i appen.

Fält:
- active_run_id
- route_id
- train_profile_id
- started_at
- current_progress_m
- selected_lookahead_m
- direction
- position_confidence

---

## 4. Geometriobjekt

## 4.1 RouteGeometryPoint
Punkt längs ruttens centerlinje.

Fält:
- chainage_m
- lat
- lon
- altitude_m, valfritt

## 4.2 ProfileSegment
Vertikalt segment längs rutten.

Fält:
- start_m
- end_m
- start_elevation_m
- end_elevation_m
- gradient_permille
- segment_type

Exempel på segment_type:
- uphill
- downhill
- level
- crest_transition
- sag_transition

## 4.3 HorizontalSegment
Horisontellt segment längs rutten.

Fält:
- start_m
- end_m
- geometry_type
- turn_direction
- radius_m, valfritt

Exempel på geometry_type:
- straight
- curve
- transition

## 4.4 ReferencePoint
Referenspunkt längs rutten.

Fält:
- chainage_m
- label
- category
- metadata

Exempel på category:
- station
- driftplats
- control_point
- profile_change

---

## 5. Rekommenderat JSON-format

Ett första datautbyte kan ske som JSON-fil per rutt.

```json
{
  "route_id": "route-hallsberg-mjolby",
  "name": "Hallsberg -> Mjölby",
  "start_location": "Hallsberg",
  "end_location": "Mjölby",
  "via_points": ["Degerön"],
  "total_length_m": 83000,
  "version": "1.0",
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

## 6. Rekommenderat dataflöde

### I Banprofil
Banprofil bör:
- skapa sammanhängande ruttkedja
- exportera geometri och profil mot samma chainage
- paketera ruttfiler med versionsnummer

### I Android-appen
Appen bör:
- läsa ruttfil lokalt
- projicera GNSS-position mot route geometry
- beräkna current_progress_m
- extrahera aktivt framåtfönster
- visa profil, planvy och kommande förändringar

---

## 7. Viktiga designregler

- chainage ska vara den gemensamma nyckeln mellan geometri, profil och referenspunkter
- appen ska konsumera färdig ruttdata, inte rå nätdata
- datamodellen ska vara versionsbar
- metadatafält ska finnas för framtida utbyggnad utan att bryta formatet
