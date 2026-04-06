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
- `wikibrain/` — WikiBrain kennisbank: verwerkt raadsstukken naar wiki-artikelen, doorzoekbaar via Obsidian
  - `wikibrain-ingest` / `wikibrain-compile` / `wikibrain-query` via `toolkit.py`
  - Obsidian-vault: open `wikibrain/wiki/` als vault

## Twee gebruikersinterfaces

De toolkit heeft twee visuele lagen:

- **Terminal** — voor alles in `toolkit.py`, `scraper.py`, `analyse.py`, `index.py`, `tijdlijn.py`, `partijen.py`. Snelle, gerichte acties.
- **Obsidian** — voor WikiBrain-output (`wikibrain/wiki/`). Kennisnetwerk, backlinks, graafweergave, navigeerbaar over tijd.

Bij vragen over zoeken: `index.py` is voor exacte trefwoorden via de terminal; WikiBrain + Obsidian voor ontdekkend werk en langlopende dossiers. Ze vullen elkaar aan.

## Beschikbare skills in dit project

Deze skills zijn alleen actief binnen deze toolkit-map:

- `/rapport-opslaan` — sla de analyse op als rapport en bied de alert-instelling aan
- `/alert-beoordelen` — beoordeel een binnengekomen alert op urgentie en vervolgactie
- `/trefwoorden-verfijnen` — analyseer en verbeter de trefwoorden van een bestaand dossier
- `/wob-verzoek` — genereer een formeel WOO/WOB-verzoek op basis van een gevonden onderwerp

## Documenten staan hier

Na scrapen: `~/Documents/notulen/<orgaan>/`

## De werkwijze

Het systeem heeft twee parallelle sporen.

**Spoor 1 — Monitoring (geautomatiseerd)**
1. Analyse draaien met de prompts in `prompts/raadsstukken-analyse.md`
2. Rapport opslaan: gebruik `/rapport-opslaan`
3. Alert instellen via `toolkit.py nieuw-alert` (Claude biedt dit eenmalig aan)
4. Alerts verschijnen wekelijks in `~/Documents/notulen/<orgaan>/alerts/`
5. Alert ontvangen? Gebruik `/alert-beoordelen` om urgentie te bepalen

**Spoor 2 — Kennisopbouw (via Obsidian)**
1. `python3 toolkit.py wikibrain-ingest` — verwerk nieuwe raadsstukken
2. `python3 toolkit.py wikibrain-compile` — schrijf of update wiki-artikelen
3. Open `wikibrain/wiki/` als Obsidian-vault om de kennisbank te verkennen
4. Gerichte zoekvraag? `python3 toolkit.py wikibrain-query "jouw vraag"`

Beide sporen gebruiken dezelfde gedownloade documenten.

## Hoe te helpen

**Monitoring-spoor:**
- Raadsstukken analyseren: gebruik de prompts in `prompts/raadsstukken-analyse.md`
- Rapport opslaan: `/rapport-opslaan <onderwerp> <orgaan>`
- Alert beoordelen: `/alert-beoordelen <orgaan> <dossier>`
- Trefwoorden verbeteren: `/trefwoorden-verfijnen <dossier-naam>`
- WOB-verzoek opstellen: `/wob-verzoek <onderwerp>`

**Kennisopbouw-spoor:**
- Kennisbank bijwerken: `python3 toolkit.py wikibrain-ingest` + `wikibrain-compile`
- Vraag stellen aan de kennisbank: `python3 toolkit.py wikibrain-query "vraag"`
- Snel zoeken op trefwoord: `python3 index.py <orgaan> "trefwoord"`
- Tijdlijn reconstrueren: `python3 tijdlijn.py <orgaan> "trefwoord"`
- Partijposities opzoeken: `python3 partijen.py <orgaan> "trefwoord"`

**Algemeen:**
- Nieuw orgaan toevoegen: `python3 toolkit.py nieuw-orgaan`
- Rode vlaggen beoordelen: verwijs naar `checklists/red-flag-lokale-overheid.md`
- Wederhoor voorbereiden: gebruik `prompts/wederhoor.md`
- Bronnen contacteren: gebruik `prompts/bronnenbrief.md`

## Repo-hygiëne

Deze repository is publiek bedoeld. Iemand die de repo kloont ziet alleen code en een lege structuur — geen persoonlijke data, geen testwerk.

Controleer dit altijd voordat je iets commit:
- Geen dossier- of orgaan-configs met echte namen (tenzij het meegeleverde voorbeeldbestanden zijn)
- Geen bestanden in `wikibrain/raw/` of `wikibrain/wiki/concepts/` (staan in `.gitignore`, maar check het)
- Geen alertrapporten, analyseresultaten of scraper-output
- Geen paden of bestandsnamen die herleidbaar zijn naar een specifieke gebruiker of gemeente

Bij twijfel: vraag of iets thuishoort in de repo of alleen lokaal.

## Python-omgeving

Python: `/opt/homebrew/bin/python3`
Geïnstalleerde bibliotheken: `pdfplumber`
