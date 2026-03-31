---
description: Analyseer een bestaand dossier en stel verbeterde trefwoorden voor
argument-hint: <dossier-naam>
---

# Trefwoorden verfijnen

De gebruiker wil de trefwoorden van een bestaand dossier verbeteren op basis van wat er tot nu toe gevonden is.

Dossier: $ARGUMENTS

## Instructies

**Stap 1 — Lees het huidige dossier**

Lees het configuratiebestand:
`/Users/erwin/Documents/lokaalbestuur-toolkit/dossiers/<dossier-naam>.json`

Noteer de huidige trefwoorden en orgaan.

**Stap 2 — Lees de alerts**

Lees alle alertbestanden in:
`~/Documents/notulen/<orgaan>/alerts/`

Lees ook het meest recente analyserapport als dat aanwezig is in:
`~/Documents/notulen/<orgaan>/`

**Stap 3 — Analyseer en stel voor**

Geef een overzicht in drie categorieën:

**Te breed of te weinig treffers**
Trefwoorden die bijna altijd voorkomen maar zelden iets relevants opleveren. Overweeg te verwijderen of te vervangen door een specifiekere variant.

**Goede trefwoorden**
Trefwoorden die consistent relevante fragmenten opleveren. Behouden.

**Ontbrekende termen**
Termen die opvallen in de gevonden fragmenten maar nog niet in het dossier staan. Voorstel om toe te voegen.

**Stap 4 — Voer door bij akkoord**

Als de gebruiker akkoord gaat met de voorgestelde wijzigingen, pas dan het JSON-bestand direct aan:
`/Users/erwin/Documents/lokaalbestuur-toolkit/dossiers/<dossier-naam>.json`

Bevestig welke trefwoorden zijn toegevoegd, verwijderd of gewijzigd.
