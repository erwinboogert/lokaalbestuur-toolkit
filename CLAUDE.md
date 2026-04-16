# Lokaalbestuur Toolkit — context voor Claude Code

Een journalistiek onderzoekstool waarmee je openbare vergaderstukken van Nederlandse gemeenten, waterschappen en samenwerkingsverbanden kunt downloaden en doorzoeken met AI.

## Wat er in deze map staat

- `toolkit.py` — hoofdinterface: verkennen, onderzoek, nieuw-orgaan, nieuw-dossier, status, check
- `api.py` — gedeelde API-functies (ORI, Notubiz, iBabs) en utilities voor alle scrapers
- `scraper.py` — downloadt PDF's van gemeenten via Open Raadsinformatie API
- `scraper_waterschap.py` — downloadt vergaderstukken van waterschappen via ORI API
- `scraper_gr.py` — downloadt vergaderstukken van gemeenschappelijke regelingen
- `scraper_vr.py` — downloadt vergaderstukken van alle 25 veiligheidsregio's (website/Notubiz/iBabs)
- `analyse.py` — doorzoekt PDF's op trefwoorden, genereert wekelijkse alerts
- `index.py` — bouwt lokale full-text zoekindex (SQLite FTS5)
- `organen/` — configuratie per orgaan (JSON): naam, type, vergadertypen
- `dossiers/` — configuratiebestanden per monitoringsdossier (JSON): label, orgaan, trefwoorden
- `bronnen/` — catalogussen:
  - `waterschappen.json` — alle 21 waterschappen met gemeente-mapping
  - `veiligheidsregios.json` — alle 25 veiligheidsregio's met gemeente-mapping
  - `regelingen.json` — geconfigureerde GRs
  - `gemeenten_overheid.json` — gemeente → overheid.nl koppeling
- `prompts/` — analyseprompts voor gebruik in Claude Code-gesprekken:
  - `vrije-vraag.md` — brede onderzoeksvraag zonder vooraf bekende trefwoorden **(start hier)**
  - `raadsstukken-analyse.md` — gestructureerde analyse van een bekend dossier
  - `rode-vlaggen.md` — rode-vlaggen toets na een onderzoekssessie (7 categorieën)
  - `wederhoor.md` — gerichte vragen per partij op basis van de stukken
  - `bronnenbrief.md` — eerste contactbrief aan een bron of betrokkene
- `skills/` — systeembrede Claude Code skills (kopieer naar `~/.claude/commands/` voor gebruik)
- `.claude/commands/` — toolkit-specifieke slash commands, automatisch beschikbaar in dit project
- `checklists/` — rode-vlagchecklist voor lokaal bestuurlijk onderzoek

## Beschikbare skills in dit project

- `/rapport-opslaan` — sla de analyse op als rapport en bied de alert-instelling aan
- `/alert-beoordelen` — beoordeel een binnengekomen alert op urgentie en vervolgactie
- `/trefwoorden-verfijnen` — analyseer en verbeter de trefwoorden van een bestaand dossier
- `/woo-verzoek` — genereer een formeel Woo-verzoek op basis van een gevonden onderwerp

## Documenten staan hier

Na scrapen: `~/Documents/notulen/<orgaan>/`
Waterschappen: `~/Documents/notulen/waterschappen/<naam>/`
GRs: `~/Documents/notulen/regelingen/<naam>/`
Veiligheidsregio's: `~/Documents/notulen/veiligheidsregios/<naam>/`

## De primaire werkwijze

```
python3 toolkit.py verkennen <gemeente>          # vooronderzoek: VR, GRs, waterschap tonen
python3 scraper.py <gemeente>                    # raadsdocumenten downloaden
python3 scraper.py <gemeente> --jaren 2          # optioneel: begrens de periode
python3 scraper.py <gemeente> --vanaf 2024-01-01 # of vanaf een specifieke datum
python3 scraper_vr.py <slug>                     # optioneel: veiligheidsregio downloaden
python3 scraper_gr.py <slug>                     # optioneel: GR downloaden
python3 scraper_waterschap.py <slug>             # optioneel: waterschap downloaden
python3 toolkit.py onderzoek <gemeente>          # zoekindex + Claude-briefing
claude ~/Documents/notulen/<gemeente>            # Claude Code openen
```

Plak de gegenereerde briefing vóór je onderzoeksvraag. Claude weet dan welke bronnen er zijn (gemeente, GRs, waterschappen), hoe de zoekindex te gebruiken, en welk type organisatie relevant is voor welk onderwerp.

## Presentatie na verkennen

Na `toolkit.py verkennen` de resultaten altijd gestructureerd presenteren in het gesprek — niet de ruwe terminal-output tonen en doorvragen. Het juiste format:

**<Gemeente> — vooronderzoek**

**Veiligheidsregio:** <naam>
**Waterschap(pen):** <naam>
**Gemeenschappelijke regelingen (<n>):**
- <naam>
- <naam>
- …

Sluit af met: de raadsdocumenten worden sowieso gedownload — wil je daar ook een van bovenstaande bij? Alles is later alsnog op te halen.

## Werkwijze voor Claude na het downloaden

Na een succesvolle scraper-run altijd automatisch:
1. `python3 toolkit.py onderzoek <gemeente>` draaien (bijwerkt de zoekindex en genereert de bronnencheck)
2. De gevonden gemeenschappelijke regelingen en het relevante waterschap tonen
3. Aanbieden om de GRs en/of het waterschap ook te downloaden — de gebruiker beslist

Dit geldt ook na het downloaden van een waterschap of GR. Niet wachten tot de gebruiker erom vraagt.

## Optioneel: automatische monitoring

```
python3 toolkit.py nieuw-dossier            # dossier aanmaken met trefwoorden
python3 analyse.py --dossier <naam>         # handmatig draaien
```

Bij een match verschijnt een macOS-melding en staat een alertrapport klaar in `~/Documents/notulen/<orgaan>/alerts/`.

## Onderzoekswerkwijze bij open vragen

Bij een open vraag zoals "wat weten we over X?" of "vertel me over Y" altijd eerst alle relevante bestanden verkennen voordat je antwoord geeft. Dit geldt voor elk onderwerp, elke gemeente, elk dossier.

1. Gebruik Glob om alle relevante bestanden te identificeren
2. Lees de belangrijkste stukken
3. Antwoord pas daarna
4. Als niet alles gelezen is, vermeld expliciet welke stukken zijn overgeslagen en waarom

## Hoe te helpen

- Onderzoeksvraag stellen: gebruik `prompts/vrije-vraag.md` als sjabloon
- Gestructureerde analyse: gebruik `prompts/raadsstukken-analyse.md`
- Rapport opslaan: `/rapport-opslaan <onderwerp> <orgaan>`
- Alert beoordelen: `/alert-beoordelen <orgaan> <dossier>`
- Woo-verzoek opstellen: `/woo-verzoek <onderwerp>`
- Rode vlaggen beoordelen: verwijs naar `checklists/red-flag-lokale-overheid.md`
- Wederhoor voorbereiden: gebruik `prompts/wederhoor.md`
- Bronnen contacteren: gebruik `prompts/bronnenbrief.md`
- Nieuw orgaan toevoegen: `python3 toolkit.py nieuw-orgaan`

## Repo-hygiëne

Deze repository is publiek. Controleer altijd voor een commit:
- Geen dossier- of orgaan-configs met echte namen (tenzij meegeleverde voorbeeldbestanden)
- Geen alertrapporten, analyseresultaten of scraper-output
- Geen paden of bestandsnamen herleidbaar naar een specifieke gebruiker of gemeente

**Orgaan-configs horen niet in de projectmap.** Configs voor echte organen (zoals `veere.json`) worden aangemaakt in `~/Documents/notulen/organen/` — dat is de map die de toolkit daadwerkelijk leest. De `organen/`-map in de projectmap bevat alleen voorbeeldbestanden.

## Python-omgeving

Python: `sys.executable` (niet hardcoden)
Geïnstalleerde bibliotheken: `pdfplumber`

## Werkdiscipline bij code schrijven

Lees altijd eerst de volledige relevante code voordat je iets schrijft.
Schrijf geen regel totdat je de volgende vragen hebt beantwoord:

- Staan alle imports bovenaan, of zijn er lokale imports verstopt in functies?
- Zijn er hardcoded waarden die portabel moeten zijn (paden, versies)?
- Is er duplicatie die al bestaat en die ik herhaal?
- Wat zegt de instructie precies — en wat zegt hij *niet*?
  Generaliseer een instructie nooit stilzwijgend naar een bredere context.

Bij een code-review: doorlezen tot er niets meer te vinden is,
niet tot er genoeg gevonden is.

Fouten in eigen werk direct erkennen en herstellen — niet afwachten tot
de gebruiker ze signaleert.

Geef geen advies over bestanden of projectstructuur zonder eerst te
controleren wat vergelijkbare bestanden in hetzelfde project doen.
Niet redeneren vanuit een algemene vuistregel, maar vanuit de concrete situatie.

