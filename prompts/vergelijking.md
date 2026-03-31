# Prompt: Vergelijking tussen gemeenten

Gebruik deze prompt om te vergelijken hoe meerdere gemeenten hetzelfde onderwerp aanpakken. Dat kan onthullen dat de ene gemeente verder is, minder uitgeeft, harder optreedt of een afwijkende koers vaart — en dat is journalistiek waardevol.

Zorg dat je de raadsstukken van alle te vergelijken gemeenten hebt gedownload voordat je deze prompt uitvoert.

Vervang de tekst tussen `[rechte haken]` door de invulling voor jouw situatie.

---

## Prompt 1 — Feitelijke vergelijking

```
Je hebt toegang tot raadsstukken van de volgende gemeenten:
[gemeente A], [gemeente B], [gemeente C eventueel meer]

Vergelijk hoe deze gemeenten omgaan met [onderwerp].

Geef per gemeente eerst een korte schets (3-5 zinnen) van de huidige aanpak,
en stel daarna een vergelijkende analyse op aan de hand van deze vragen:

1. **Aanpak en beleid**: Welke gemeente heeft het meest uitgewerkte beleid?
   Welke gemeente heeft nog geen of nauwelijks beleid vastgesteld?

2. **Besluitvorming**: Zijn de besluiten vergelijkbaar, of zijn er
   opvallende verschillen in wat er is vastgesteld?

3. **Politieke steun**: Is er in alle gemeenten brede steun voor het beleid,
   of zijn er gemeenten waar het omstreden is? Welke partijen liggen dwars?

4. **Financiën**: Zijn er vergelijkbare budgetten ingezet? Zijn er gemeenten
   die opvallend meer of minder uitgeven?

5. **Uitvoering en voortgang**: Waar staat elke gemeente in de uitvoering?
   Zijn er achterstanden, conflicten of juist opmerkelijke successen?

Gebruik een overzichtstabel aan het einde met de belangrijkste vergelijkpunten.
Vermeld bij elke bevinding de bron (gemeente, vergadering, datum).
```

---

## Prompt 2 — Verklaring van de verschillen

```
Je hebt zojuist de aanpak van [gemeente A], [gemeente B] en [gemeente C]
vergeleken op het gebied van [onderwerp].

Ik wil nu begrijpen waarom er verschillen zijn. Analyseer:

1. **Structurele verklaringen**: Zijn er voor de hand liggende redenen
   voor de verschillen — omvang van de gemeente, financiële positie,
   samenstelling van de coalitie, lokale context?

2. **Opvallende uitschieters**: Welke gemeente wijkt het meest af van
   de anderen? In positieve of negatieve zin? Wat zou dat kunnen verklaren?

3. **Wat de stukken niet zeggen**: Welke verklaringen zijn niet terug
   te vinden in de formele stukken, maar liggen voor de hand op basis
   van wat er wél staat?

4. **Journalistieke ingang**: Welk verschil is het meest de moeite waard
   om verder uit te zoeken? Wat is het sterkste verhaal dat uit deze
   vergelijking naar voren komt?
```

---

## Instructies voor hergebruik

1. **Download eerst de stukken** van alle gemeenten via `python3 scraper.py <gemeente>`
2. **Open Claude Code in een map die toegang heeft tot alle archieven**, of verwijs expliciet naar de paden
3. **Begin met Prompt 1** voor de feitelijke vergelijking, gebruik daarna Prompt 2 voor de verdieping
4. **Twee gemeenten vergelijken** werkt goed; meer dan vier wordt onoverzichtelijk
