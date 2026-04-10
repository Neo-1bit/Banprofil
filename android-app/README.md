# Banprofil Android App Scaffold

Detta är ett första scaffold för en framtida native Android-app till Banprofil.

Syfte:
- ge projektet en tydlig startstruktur
- skilja mobilappen från Python-delen i repot
- dokumentera rekommenderad modulindelning
- förbereda nästa steg när Android-byggmiljö finns tillgänglig

## Status

Detta scaffold är medvetet lättviktigt. Byggfiler för faktisk Gradle/Android Studio-uppsättning har ännu inte genererats här, eftersom aktuell miljö saknar Java/Android toolchain.

Strukturen och filerna i denna mapp fungerar därför som:
- arkitekturstart
- kodskelett
- UI-spec nära implementation
- underlag för senare riktig Android Studio-initiering

## Rekommenderad nästa implementation

När Android-miljö finns:
1. initiera ett nytt Kotlin/Compose-projekt i denna mapp
2. behåll paketstruktur och skärmindelning
3. börja med ruttval, tåguppgifter och huvudvy med mockdata
4. koppla sedan in JSON-läsning från Banprofil-route-formatet
5. anslut därefter positionering längs vald rutt
