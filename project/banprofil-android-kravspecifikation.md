# Banprofil, kravspecifikation för Android MVP

## 1. Syfte

Detta dokument beskriver kravbilden för en första Android-baserad MVP av Banprofil. Appen ska fungera som ett diskret förarstöd för energieffektiv och skonsam körning längs en redan fastställd rutt.

Appen ska inte användas för vägval, signalering eller andra säkerhetskritiska beslut.

---

## 2. Produktmål

MVP:n ska göra det möjligt att:

- välja en fastställd rutt
- ange tågets grundegenskaper
- visa aktuell position längs rutten
- visa kommande topografi i profilvy
- visa rutten i planvy
- ge användaren bättre framförhållning inför kommande stigning, fall och andra tydliga profilförändringar

---

## 3. Funktionella krav

### KR-01 Ruttval
Appen ska låta användaren välja en förberedd rutt.

### KR-02 Ruttöversikt
Appen ska visa grundläggande metadata för vald rutt.

### KR-03 Tåguppgifter
Appen ska låta användaren ange:
- maxhastighet
- längd
- vikt

### KR-04 Aktiv körning
Appen ska kunna spara en aktiv körning bestående av vald rutt och tåguppgifter.

### KR-05 Positionsdata
Appen ska kunna läsa telefonens positionsdata.

### KR-06 Projektion mot rutt
Appen ska kunna uppskatta användarens läge längs vald rutt.

### KR-07 Progress längs rutt
Appen ska kunna visa aktuell progress längs rutten i meter eller annan lämplig representation.

### KR-08 Planvy
Appen ska visa närmaste delen av rutten i planvy med aktuell position markerad.

### KR-09 Profilvy
Appen ska visa kommande vertikal profil längs rutten.

### KR-10 Markering av aktuell position
Aktuell position ska markeras tydligt i profilvyn.

### KR-11 Framåtfönster
Appen ska visa ett framåtfönster om minst 3 km som standard.

### KR-12 Nästa tydliga förändring
Appen ska visa nästa större topografiska förändring inom framåtfönstret.

### KR-13 Positionsstatus
Appen ska visa om positionsbestämningen är god eller osäker.

### KR-14 Offline-stöd
Appens kärnfunktioner ska fungera utan aktiv uppkoppling när ruttdata redan finns lokalt.

---

## 4. Icke-funktionella krav

### IKR-01 Låg distraktion
Gränssnittet ska kunna läsas av med kort blicktid.

### IKR-02 Låg visuell belastning
Designen ska vara lugn, återhållsam och konsekvent.

### IKR-03 Tydlighet
Text, status och grafiska markeringar ska vara lättolkade.

### IKR-04 Robusthet
Appen ska tåla längre användningspass utan att tappa grundfunktionalitet.

### IKR-05 Transparens
Appen ska visa osäkerhet när positionsunderlaget inte räcker.

### IKR-06 Modularitet
Lösningen ska delas upp i tydliga tekniska moduler.

---

## 5. Avgränsningar

Följande ska inte ingå i MVP:

- AR
- kamera-overlay
- automatisk ruttplanering
- vägvalslogik
- säkerhetskritiska funktioner
- avancerade energiberäkningar
- kompletta körrekommendationer
- tung 3D-rendering

---

## 6. Acceptanskriterier

MVP:n är godkänd när:

- användaren kan välja rutt
- användaren kan ange tåguppgifter
- appen kan visa position längs rutt
- appen kan visa planvy och profilvy
- appen kan visa nästa större topografiska förändring
- appen fungerar offline med lokalt laddad data
- gränssnittet upplevs som lugnt och begripligt
