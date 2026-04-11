---
description: Sla de huidige analyse op als rapport en bied de alert-instelling aan
argument-hint: <onderwerp> <orgaan>
---

# Rapport opslaan

De gebruiker wil de analyse vastleggen als Markdown-rapport.

Onderwerp en orgaan: $ARGUMENTS

## Instructies

**Stap 1 — Bepaal bestandsnaam en locatie**

Gebruik als locatie: `~/Documents/notulen/<orgaan>/`
Gebruik als bestandsnaam: `YYYY-MM-DD - onderzoek-<onderwerp>.md`

Gebruik de datum van vandaag. Leid orgaan en onderwerp af uit $ARGUMENTS of uit het gesprek als geen argumenten zijn meegegeven.

**Stap 2 — Schrijf het rapport**

Schrijf de volledige analyse als Markdown-bestand naar die locatie. Gebruik een heldere structuur met kopjes. Sluit af met een sectie **Bronnen** met de namen van de raadsstukken die zijn gebruikt.

**Stap 3 — Bied de alert aan**

Doe dit aanbod pas nadat het rapport is opgeslagen. Formuleer het zo:

> "Het rapport is opgeslagen in `<pad>`.
>
> Wil je dat ik een automatische alert instel die je waarschuwt als er nieuwe raadsstukken verschijnen over dit onderwerp?
>
> Op basis van de analyse stel ik deze trefwoorden voor:
> `[trefwoord1]`, `[trefwoord2]`, `[trefwoord3]` ...
>
> Pas de lijst aan als je wilt. Hoe vaak wil je een update: **wekelijks** of **maandelijks**?"

Destilleer 8 tot 12 trefwoorden uit de taal die de gemeente zelf gebruikt in de stukken — niet de termen die de journalist veronderstelde.

**Stap 4 — Maak de alert aan bij akkoord**

Voer dit commando uit vanuit de toolkit-map:

```bash
python3 /Users/erwin/Documents/lokaalbestuur-toolkit/toolkit.py nieuw-alert \
  --dossier <onderwerp> \
  --orgaan <orgaan> \
  --trefwoorden "<woord1>,<woord2>,<woord3>" \
  --frequentie <wekelijks|maandelijks>
```
