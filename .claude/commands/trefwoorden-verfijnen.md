---
description: Analyseer een bestaand dossier en stel verbeterde trefwoorden voor
argument-hint: <dossier-naam>
---

# Trefwoorden verfijnen

De gebruiker wil de trefwoorden van een bestaand dossier verbeteren. Deze trefwoorden zijn eerder automatisch gedestilleerd via `/rapport-opslaan` — gebaseerd op de taal die de gemeente zelf gebruikt in de vergaderstukken. Nu het dossier al een tijdje draait, kan op basis van de daadwerkelijke alertresultaten worden bijgesteld.

Dossier: $ARGUMENTS

## Instructies

**Stap 0 — Bepaal de paden**

Lees `config.local.json` in de toolkit-map om te weten waar dossiers en notulen staan:
- Als `data_map` aanwezig is: gebruik `<data_map>/dossiers/` en `<data_map>/<orgaan>/`
- Anders: gebruik `<toolkit-map>/dossiers/` en `~/Documents/notulen/<orgaan>/`

**Stap 1 — Lees het huidige dossier**

Lees het configuratiebestand `<dossiers-map>/<dossier-naam>.json` en noteer de huidige trefwoorden en orgaan.

**Stap 2 — Lees de alerts**

Lees alle alertbestanden in `<notulen-map>/<orgaan>/alerts/`.

Lees ook het meest recente analyserapport als dat aanwezig is in `<notulen-map>/<orgaan>/`.

**Stap 3 — Analyseer en stel voor**

Geef een overzicht in drie categorieën:

**Te breed of te weinig treffers**
Trefwoorden die bijna altijd voorkomen maar zelden iets relevants opleveren. Overweeg te verwijderen of te vervangen door een specifiekere variant.

**Goede trefwoorden**
Trefwoorden die consistent relevante fragmenten opleveren. Behouden.

**Ontbrekende termen**
Termen die opvallen in de gevonden fragmenten maar nog niet in het dossier staan. Voorstel om toe te voegen.

**Stap 4 — Voer door bij akkoord**

Als de gebruiker akkoord gaat met de voorgestelde wijzigingen, pas dan `<dossiers-map>/<dossier-naam>.json` direct aan en bevestig welke trefwoorden zijn toegevoegd, verwijderd of gewijzigd.
