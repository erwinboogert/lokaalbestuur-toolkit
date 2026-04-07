# Lokaalbestuur Toolkit — context voor Claude Code

Een journalistiek onderzoekstool waarmee je openbare vergaderstukken van Nederlandse gemeenten, waterschappen en samenwerkingsverbanden kunt downloaden en doorzoeken met AI.

## Wat er in deze map staat

- `toolkit.py` — hoofdinterface: onderzoek, nieuw-orgaan, nieuw-dossier, status, check
- `scraper.py` — downloadt PDF's van gemeenten via Open Raadsinformatie API
- `scraper_waterschap.py` — downloadt vergaderstukken van waterschappen via ORI API
- `scraper_gr.py` — downloadt vergaderstukken van gemeenschappelijke regelingen
- `analyse.py` — doorzoekt PDF's op trefwoorden, genereert wekelijkse alerts
- `index.py` — bouwt lokale full-text zoekindex (SQLite FTS5)
- `organen/` — configuratie per orgaan (JSON): naam, type, vergadertypen
- `dossiers/` — configuratiebestanden per monitoringsdossier (JSON): label, orgaan, trefwoorden
- `bronnen/` — catalogussen: waterschappen, GRs, gemeenten
- `prompts/` — analyseprompts voor gebruik in Claude Code-gesprekken:
  - `vrije-vraag.md` — brede onderzoeksvraag zonder vooraf bekende trefwoorden **(start hier)**
  - `raadsstukken-analyse.md` — gestructureerde analyse van een bekend dossier
  - `rode-vlaggen.md` — rode-vlaggen toets na een onderzoekssessie (7 categorieën)
  - `wederhoor.md` — gerichte vragen per partij op basis van de stukken
  - `bronnenbrief.md` — eerste contactbrief aan een bron of betrokkene
- `skills/` — systeembrede Claude Code skills (kopieer naar `~/.claude/skills/` voor gebruik)
- `.claude/skills/` — toolkit-specifieke skills, automatisch beschikbaar in dit project
- `checklists/` — rode-vlagchecklist voor lokaal bestuurlijk onderzoek

## Beschikbare skills in dit project

- `/rapport-opslaan` — sla de analyse op als rapport en bied de alert-instelling aan
- `/alert-beoordelen` — beoordeel een binnengekomen alert op urgentie en vervolgactie
- `/trefwoorden-verfijnen` — analyseer en verbeter de trefwoorden van een bestaand dossier
- `/wob-verzoek` — genereer een formeel WOO/WOB-verzoek op basis van een gevonden onderwerp

## Documenten staan hier

Na scrapen: `~/Documents/notulen/<orgaan>/`
Waterschappen: `~/Documents/notulen/waterschappen/<naam>/`
GRs: `~/Documents/notulen/regelingen/<naam>/`

## De primaire werkwijze

```
python3 scraper.py <gemeente>               # documenten downloaden
python3 toolkit.py onderzoek <gemeente>     # bronnencheck + zoekindex + Claude-briefing
claude ~/Documents/notulen/<gemeente>       # Claude Code openen
```

Plak de gegenereerde briefing vóór je onderzoeksvraag. Claude weet dan welke bronnen er zijn (gemeente, GRs, waterschappen), hoe de zoekindex te gebruiken, en welk type organisatie relevant is voor welk onderwerp.

## Optioneel: automatische monitoring

```
python3 toolkit.py nieuw-dossier            # dossier aanmaken met trefwoorden
python3 analyse.py --dossier <naam>         # handmatig draaien
```

Bij een match verschijnt een macOS-melding en staat een alertrapport klaar in `~/Documents/notulen/<orgaan>/alerts/`.

## Hoe te helpen

- Onderzoeksvraag stellen: gebruik `prompts/vrije-vraag.md` als sjabloon
- Gestructureerde analyse: gebruik `prompts/raadsstukken-analyse.md`
- Rapport opslaan: `/rapport-opslaan <onderwerp> <orgaan>`
- Alert beoordelen: `/alert-beoordelen <orgaan> <dossier>`
- WOB-verzoek opstellen: `/wob-verzoek <onderwerp>`
- Rode vlaggen beoordelen: verwijs naar `checklists/red-flag-lokale-overheid.md`
- Wederhoor voorbereiden: gebruik `prompts/wederhoor.md`
- Bronnen contacteren: gebruik `prompts/bronnenbrief.md`
- Nieuw orgaan toevoegen: `python3 toolkit.py nieuw-orgaan`

## Repo-hygiëne

Deze repository is publiek. Controleer altijd voor een commit:
- Geen dossier- of orgaan-configs met echte namen (tenzij meegeleverde voorbeeldbestanden)
- Geen alertrapporten, analyseresultaten of scraper-output
- Geen paden of bestandsnamen herleidbaar naar een specifieke gebruiker of gemeente

## Python-omgeving

Python: `/opt/homebrew/bin/python3`
Geïnstalleerde bibliotheken: `pdfplumber`
