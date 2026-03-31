# Lokaalbestuur Toolkit — context voor Claude Code

Dit is een journalistiek onderzoeksframework voor het monitoren van openbare raadsdocumenten van Nederlandse gemeenten.

## Wat er in deze map staat

- `toolkit.py` — hoofdinterface: dashboard, nieuw-dossier, nieuw-orgaan, status, check, nieuw-alert
- `scraper.py` — downloadt PDF's van Open Raadsinformatie API (geen extra bibliotheken)
- `analyse.py` — doorzoekt PDF's op trefwoorden, genereert alerts (vereist: `pdfplumber`)
- `organen/` — configuratie per orgaan (JSON): naam, type, bron, vergadertypen
- `dossiers/` — configuratiebestanden per dossier (JSON): label, orgaan, trefwoorden
- `prompts/` — analyseprompts voor gebruik in Claude Code-gesprekken:
  - `raadsstukken-analyse.md` — stand van zaken en vooruitblik
  - `wederhoor.md` — gerichte vragen per partij op basis van de stukken
  - `bronnenbrief.md` — eerste contactbrief aan een bron of betrokkene
  - `vergelijking.md` — vergelijk meerdere gemeenten op hetzelfde onderwerp
  - `budget.md` — analyseer financiële keuzes en begrotingsposten
- `skills/` — systeembrede Claude Code skills (kopieer naar `~/.claude/skills/` voor gebruik)
- `.claude/skills/` — toolkit-specifieke skills, automatisch beschikbaar in dit project
- `checklists/` — rode-vlagchecklist voor lokaal bestuurlijk onderzoek

## Beschikbare skills in dit project

Deze skills zijn alleen actief binnen deze toolkit-map:

- `/rapport-opslaan` — sla de analyse op als rapport en bied de alert-instelling aan
- `/alert-beoordelen` — beoordeel een binnengekomen alert op urgentie en vervolgactie
- `/trefwoorden-verfijnen` — analyseer en verbeter de trefwoorden van een bestaand dossier
- `/wob-verzoek` — genereer een formeel WOO/WOB-verzoek op basis van een gevonden onderwerp

## Documenten staan hier

Na scrapen: `~/Documents/notulen/<orgaan>/`

## De werkwijze

1. Analyse draaien met de prompts in `prompts/raadsstukken-analyse.md`
2. Als de gebruiker het rapport wil opslaan: gebruik `/rapport-opslaan`
3. Claude biedt daarna eenmalig aan de alert in te stellen via `toolkit.py nieuw-alert`
4. Alerts verschijnen wekelijks in `~/Documents/notulen/<orgaan>/alerts/`
5. Alert ontvangen? Gebruik `/alert-beoordelen` om te bepalen of verdieping zinvol is

## Hoe te helpen

- Raadsstukken analyseren: gebruik de prompts in `prompts/raadsstukken-analyse.md`
- Rapport opslaan: `/rapport-opslaan <onderwerp> <orgaan>`
- Alert beoordelen: `/alert-beoordelen <orgaan> <dossier>`
- Trefwoorden verbeteren: `/trefwoorden-verfijnen <dossier-naam>`
- WOB-verzoek opstellen: `/wob-verzoek <onderwerp>`
- Nieuw orgaan toevoegen: `python3 toolkit.py nieuw-orgaan`
- Rode vlaggen beoordelen: verwijs naar `checklists/red-flag-lokale-overheid.md`

## Python-omgeving

Python: `/opt/homebrew/bin/python3`
Geïnstalleerde bibliotheken: `pdfplumber`
