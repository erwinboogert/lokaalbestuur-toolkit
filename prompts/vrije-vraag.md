# Vrije onderzoeksvraag — raadsstukken en bestuursdocumenten

Gebruik deze prompt als je een brede, open onderzoeksvraag wilt voorleggen aan Claude Code op basis van gedownloade raadsstukken, GR-documenten of waterschapstukken.

## Voorbereiding

Genereer eerst de onderzoekscontext via de toolkit:

```bash
python3 toolkit.py onderzoek <gemeente>
```

Dit commando:
1. Controleert welke bronnen beschikbaar zijn (gemeente, GRs, waterschappen)
2. Bouwt de zoekindex bij voor de gemeente
3. Genereert een contextbriefing die je aan Claude kunt geven

Open daarna Claude Code in de documentenmap:

```bash
claude ~/Documents/notulen/<gemeente>
```

## Opbouw van je vraag aan Claude

Plak de gegenereerde briefing (uit `toolkit.py onderzoek`) vóór je vraag, gevolgd door dit sjabloon:

---

[BRIEFING UIT TOOLKIT HIER PLAKKEN]

---

**Mijn onderzoeksvraag:**

[Beschrijf hier je vraag zo concreet mogelijk. Geef aan:]
- Wat je al weet of vermoedt
- Over welke periode je wil kijken
- Of je een specifiek verband wil aantonen, of juist wil verkennen wat er speelt

**Verwacht resultaat:**

Geef me een beeld van wat de documenten zeggen over dit onderwerp. Ik wil:
- Concrete besluiten of uitspraken die relevant zijn
- Welke organen (gemeente, GR, waterschap) iets over dit onderwerp zeggen
- Wat er *niet* in de stukken staat maar misschien wel verwacht zou worden
- Suggesties voor vervolgvragen of bronnen die ik nog niet heb

---

## Tips

**Wees specifiek over het tijdvak.** "De afgelopen vijf jaar" werkt beter dan "recent". Claude kan treffers dateren op basis van de mapstructuur (`/<vergadertype>/YYYY-MM-DD/`).

**Gebruik de zoekindex voor verkenning.** Als je vermoedt dat een trefwoord relevant is, laat Claude eerst zoeken via:
```bash
python3 index.py <gemeente> "trefwoord"
```
Daarna kan Claude de meest relevante PDF's lezen voor context.

**GRs en waterschappen zijn aanvullend, niet vervangend.** Formele raadsbesluiten staan bij de gemeente. Uitvoering, monitoring en regionale samenwerking staan vaak bij GRs. Vraag Claude expliciet om ook daar te zoeken als het onderwerp dat raakt.

**Signaleer leemtes.** Als iets wél verwacht zou worden in de stukken maar er niet in staat, is dat ook informatie. Vraag Claude dit expliciet te benoemen.

## Voorbeeld

> De gemeente heeft de afgelopen jaren bezuinigd op sportaccommodaties voor lokale verenigingen. Tegelijk loopt het aantal jeugdsporters terug. Ik wil weten: is er in de raadsstukken een verband te vinden tussen deze bezuinigingen en de stijgende obesitascijfers onder jongeren? Kijk ook of de GGD of een jeugdhulp-GR hier iets over zegt.
