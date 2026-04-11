---
description: Beoordeel een binnengekomen alert en advies of verdieping zinvol is
argument-hint: <pad naar alertbestand> of <gemeente> <dossier>
---

# Alert beoordelen

De gebruiker heeft een alert ontvangen en wil weten of die de moeite van een diepere analyse waard is.

$ARGUMENTS

## Instructies

**Stap 1 — Lees het alertbestand**

Als een pad is meegegeven, lees dat bestand. Anders zoek het meest recente alertbestand in:
`~/Documents/notulen/<orgaan>/alerts/`

**Stap 2 — Beoordeel de inhoud**

Geef een korte beoordeling op vier punten:

1. **Wat staat er?** Vat in twee zinnen samen wat de gevonden fragmenten zeggen.

2. **Is dit nieuw?** Beschrijf of dit een nieuwe ontwikkeling is of een herhaling van eerder besproken punten.

3. **Urgentie** — kies één van drie:
   - **Laag** — herhaling, procedureel, geen nieuw feit
   - **Middel** — relevante update, de moeite waard om te bewaren
   - **Hoog** — nieuw besluit, onverwachte wending, directe actie zinvol

4. **Aanbeveling** — één concrete vervolgstap:
   - Niets doen, volgende week verder
   - Alert bewaren als achtergrond
   - Claude-analyse draaien op de nieuwe stukken
   - Mogelijk WOB-verzoek overwegen (gebruik `/wob-verzoek`)

Wees kort en direct. De gebruiker wil snel weten of hij iets moet doen.
