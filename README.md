# Lokaalbestuur Toolkit

Een lokaal onderzoeksframework voor journalisten die openbare raadsdocumenten van Nederlandse gemeenten willen monitoren en analyseren. Werkt volledig lokaal op je eigen machine — geen API-sleutel, geen account, geen data naar buiten.

## Wat zit erin

| Bestand/map | Functie |
|---|---|
| `toolkit.py` | Hoofdinterface: dashboard, nieuwe dossiers, installatiecheck |
| `scraper.py` | Download raadsstukken van elke Nederlandse gemeente, waterschap of GR |
| `analyse.py` | Doorzoek gedownloade PDF's op trefwoorden en genereer alerts |
| `index.py` | Bouw een lokale full-text zoekindex (SQLite FTS5) |
| `tijdlijn.py` | Exporteer treffers chronologisch als Markdown-tijdlijn |
| `partijen.py` | Koppel fragmenten aan fracties op basis van sprekerdetectie |
| `organen/` | Configuratie per orgaan: vergadertypen, brontype |
| `dossiers/` | Configuratiebestanden per onderzoeksdossier |
| `prompts/` | Herbruikbare analyseprompts voor gebruik met Claude Code |
| `checklists/` | Rode-vlagchecklist voor lokaal bestuurlijk onderzoek |
| `skills/` | Claude Code skills voor bronnenonderzoek |
| `wikibrain/` | Kennisbank: bouwt automatisch wiki-artikelen uit raadsstukken (werkt samen met Obsidian) |

## Twee manieren van werken

De toolkit ondersteunt twee parallelle werkwijzen. Je kunt ze allebei gebruiken, of beginnen met één.

**Monitoring — wekelijks, geautomatiseerd**
Scraper downloadt nieuwe raadsstukken. `analyse.py` controleert op trefwoorden en stuurt een alert als er iets relevants in staat. Je hoeft niets te doen totdat er een treffer is.

**Kennisopbouw — continu, via Obsidian**
WikiBrain verwerkt dezelfde raadsstukken naar wiki-artikelen en toont die in Obsidian als een navigeerbaar kennisnetwerk. Geen zoekterm nodig — je ziet wat er speelt, welke concepten terugkomen, hoe een dossier zich ontwikkelt.

De twee sporen lopen parallel: dezelfde documenten voeden beide systemen.

---

## Beperkingen en eerlijke verwachtingen

Voordat je begint, is het goed om te weten wat dit instrument wel en niet kan.

**De tekstextractie is niet waterdicht.** Raadsstukken zijn als PDF notoir slecht van kwaliteit: gescand, slecht opgemaakt, soms letterlijk een foto van een pagina. De toolkit doet zijn best om tekst te extraheren, maar mist daardoor regelmatig passages. Dat betekent dat het alertsysteem geen garantie geeft — als een trefwoord niet wordt gevonden, kan dat betekenen dat het er niet in staat, maar ook dat de tekst er niet goed uitkwam. Behandel een lege alert dus niet als een bewijs van afwezigheid.

**De installatiedrempel is reëel.** Deze toolkit werkt via de terminal en vereist enige vertrouwdheid met Python en de commandoregel. Dat is bewust — het houdt alles lokaal en onder controle van de gebruiker — maar het betekent ook dat niet elke journalist er direct mee aan de slag kan.

**Het signaleert, maar beoordeelt niet.** De toolkit helpt je sneller bij de juiste vraag te komen. Wat een alert waard is, welke bronnen je raadpleegt en of er een verhaal zit: dat blijft volledig bij jou als journalist. Het systeem vervangt geen redactioneel oordeel.

**Dit is een startpunt, geen eindpunt.** Raadsstukken zijn één laag van de werkelijkheid. Ze vertellen wat er formeel is besloten, niet altijd waarom, en zeker niet wat er buiten de vergaderzaal is afgesproken. Gebruik de toolkit als ingang, niet als volledig beeld.

---

## Vereisten

- Python 3.10 of hoger
- `pdfplumber` voor PDF-tekstextractie

```bash
pip install pdfplumber
```

De scraper heeft geen extra bibliotheken nodig.

---

## Installatiecheck

Controleer na installatie of alles correct staat:

```bash
python3 toolkit.py check
```

Dit controleert automatisch je Python-versie, de benodigde bibliotheken, de verbinding met de API, aanwezige dossiers en crontab-regels. Je ziet direct wat er nog mist en wat je moet doen.

---

## De werkwijze in vier stappen

De toolkit volgt een vaste volgorde. Die volgorde is bewust: je begint altijd met begrijpen, dan pas met monitoren.

### Stap 0 — Orgaan toevoegen (eenmalig per orgaan)

```bash
python3 toolkit.py nieuw-orgaan
```

De wizard vraagt naar de naam, het type (gemeente, waterschap of GR) en de vergadertypen. De configuratie wordt opgeslagen in `organen/<naam>.json` en is herbruikbaar voor alle dossiers die je later aanmaakt voor dit orgaan. De wizard stelt ook de crontab-regels in voor automatisch wekelijks downloaden, indexeren en analyseren.

### Stap 1 — Documenten downloaden

```bash
# Bekijk welke organen beschikbaar zijn
python3 scraper.py

# Download raadsstukken
python3 scraper.py rotterdam

# Droog uitvoeren (wat zou er gedownload worden?)
python3 scraper.py rotterdam --droog
```

Documenten worden opgeslagen in `~/Documents/notulen/<orgaan>/`.

### Stap 2 — Analyseren met Claude Code

Open Claude Code in de map met de gedownloade documenten:

```bash
claude ~/Documents/notulen/rotterdam
```

Gebruik de prompt uit `prompts/raadsstukken-analyse.md`. Vervang `[onderwerp]` door jouw dossier. Draai zoveel prompts als je nodig hebt — er verschijnt geen tussentijds aanbod of onderbreking.

Wanneer je tevreden bent met de analyse, geef je de opdracht het rapport op te slaan:

> "Leg dit vast als rapport."

Claude schrijft het rapport als Markdown-bestand naar de documentenmap en biedt daarna **eenmalig** aan om een wekelijkse alert in te stellen. Claude stelt trefwoorden voor op basis van de taal die in de stukken zelf wordt gebruikt, en vraagt hoe vaak je een update wilt.

### Stap 3 — Wekelijkse alert

Zodra je akkoord gaat met het alert-voorstel, maakt Claude het dossier aan en stelt de automatische monitoring in. Vanaf dat moment hoef je niets meer te doen.

Elke woensdag wordt automatisch uitgevoerd:

```
09:00  scraper.py         — nieuwe PDF's downloaden
09:15  wikibrain ingest   — raadsstukken verwerken naar kennisbank
09:30  analyse.py         — trefwoorden checken, alert schrijven
09:45  wikibrain compile  — wiki-artikelen bijwerken
```

Als er treffers zijn, verschijnt er een melding rechtsboven in macOS en staat het alertrapport klaar in:

```
~/Documents/notulen/<orgaan>/alerts/alert-YYYY-MM-DD.md
```

Open het bestand, lees de fragmenten, en beoordeel zelf of er iets in zit dat verdieping verdient. Als dat zo is, ga je terug naar stap 2 en draai je opnieuw een Claude-analyse — nu gericht op de nieuwe ontwikkeling.

---

## Toolkit-interface

Alle functies zijn bereikbaar via `toolkit.py`:

```bash
python3 toolkit.py                      # dashboard: overzicht van actieve dossiers
python3 toolkit.py check                # installatiecheck
python3 toolkit.py nieuw-orgaan         # nieuw orgaan toevoegen (gemeente, waterschap of GR)
python3 toolkit.py nieuw-dossier        # nieuw dossier aanmaken (interactieve wizard)
python3 toolkit.py status               # uitgebreid overzicht van dossiers en archieven
python3 toolkit.py wikibrain-ingest     # verwerk nieuwe raadsstukken naar kennisbank
python3 toolkit.py wikibrain-compile    # update wiki-artikelen
python3 toolkit.py wikibrain-query      # stel een vraag aan de kennisbank
```

Het commando `nieuw-alert` wordt door Claude automatisch aangeroepen na het opslaan van een rapport — je hoeft dat zelf niet te doen.

---

## Meerdere dossiers monitoren

Elk dossier heeft een eigen configuratiebestand in `dossiers/`. Gebruik de wizard om een nieuw dossier aan te maken:

```bash
python3 toolkit.py nieuw-dossier
```

Of laat Claude het aanmaken na een analyse — dat is de aanbevolen werkwijze, omdat de trefwoorden dan zijn afgeleid uit de stukken zelf.

Elk dossier kan gericht zijn op hetzelfde orgaan of op een ander. De analyse houdt per dossier bij welke PDF's al zijn verwerkt, zodat dossiers elkaar niet in de weg zitten.

---

## Onderzoekstools

Naast de automatische monitoring biedt de toolkit drie scripts voor diepgaand onderzoek, plus WikiBrain voor kennisopbouw.

**Twee manieren om te zoeken:**
- **`index.py`** — snel, exact, via de terminal. Je weet wat je zoekt en wil het direct vinden.
- **WikiBrain + Obsidian** — bouwt begrip op over tijd. Concepten, verbanden, tijdlijnen — navigeerbaar als kennisnetwerk. Geschikt voor ontdekkend werk en langlopende dossiers.

### Zoekindex (CLI)

```bash
python3 index.py rotterdam                          # bouw/update de index
python3 index.py rotterdam "grondtransactie"        # zoek
python3 index.py rotterdam "grond OR woningbouw" --uitvoer  # exporteer naar Markdown
python3 index.py rotterdam --status                 # toon statistieken
```

Bouwt een lokale SQLite-database van alle tekst in het archief. Eenmalig opbouwen, daarna doorzoekbaar in milliseconden. Zoeksyntaxis: `woord1 OR woord2`, `"exacte zin"`, `woord1 NOT woord2`.

### Tijdlijn

```bash
python3 tijdlijn.py rotterdam "woningbouw"
python3 tijdlijn.py --dossier asielopvang "spreidingswet"
```

Doorzoekt het archief en exporteert alle treffers chronologisch als Markdown — handig voor het reconstrueren hoe een dossier zich door de jaren heeft ontwikkeld.

### Partijposities

```bash
python3 partijen.py rotterdam "woningbouw"
python3 partijen.py --dossier asielopvang "spreidingswet" --uitvoer
```

Detecteert sprekers in vergaderverslagen en koppelt fragmenten aan fracties. Werkt het best bij goed opgemaakte verslagen; het script waarschuwt als de opmaak niet herkenbaar is.

---

## WikiBrain — kennisbank met Obsidian

WikiBrain bouwt een kennisbank op uit de gedownloade raadsstukken en toont die in **Obsidian**. Het is het tegendeel van `index.py`: niet zoeken op een woord dat je al kent, maar begrijpen wat er speelt — over langere tijd, over meerdere vergaderingen, in samenhang.

WikiBrain leest nieuwe documenten, herkent concepten (zoals "woningbouwprogramma" of "participatieverordening"), schrijft er wiki-artikelen over en koppelt ze aan elkaar. In Obsidian zie je de verbanden als een navigeerbaar netwerk.

**Obsidian** is een gratis Markdown-editor. Je opent de `wikibrain/wiki/` map als vault en hebt direct toegang tot de kennisbank met backlinks, graafweergave en zoekfunctie.

```bash
python3 toolkit.py wikibrain-ingest     # verwerk nieuwe raadsstukken
python3 toolkit.py wikibrain-compile    # schrijf of update wiki-artikelen
python3 toolkit.py wikibrain-query "Welke besluiten zijn genomen over woningbouw?"
```

Zie `wikibrain/README.md` voor de volledige documentatie.

---

## Prompts

De map `prompts/` bevat analyseprompts voor gebruik in Claude Code. Alle prompts werken zelfstandig maar zijn sterker in combinatie.

| Prompt | Gebruik |
|---|---|
| `raadsstukken-analyse.md` | Huidige stand van zaken en vooruitblik per dossier |
| `wederhoor.md` | Gerichte vragen per partij op basis van passages uit de stukken |
| `bronnenbrief.md` | Eerste contactbrief aan een bron of betrokkene |
| `vergelijking.md` | Vergelijk meerdere gemeenten op hetzelfde onderwerp |
| `budget.md` | Analyseer begrotingsposten en financiële keuzes |

---

## Mapstructuur na gebruik

```
lokaalbestuur-toolkit/
├── organen/
│   └── rotterdam.json          vergadertypen en brontype
└── dossiers/
    └── asielopvang.json        trefwoorden en orgaan-referentie

~/Documents/notulen/
└── rotterdam/
    ├── gemeenteraad/
    │   └── 2026-01-27/
    │       └── *.pdf
    ├── commissie-ruimte/
    ├── alerts/
    │   └── alert-2026-03-26.md
    ├── tijdlijnen/
    │   └── tijdlijn-woningbouw-2026-03-30.md
    ├── zoekresultaten/
    │   └── zoek-grondtransactie-2026-03-30.md
    ├── partijposities/
    │   └── partijen-woningbouw-2026-03-30.md
    ├── index.db
    └── logs/
        ├── scraper.log
        ├── index.log
        ├── analyse.log
        └── analyse-staat-asielopvang.json
```

---

## Databron

Raadsstukken komen van de [Open Raadsinformatie API](https://openraadsinformatie.nl), een initiatief van de Open State Foundation. Niet alle gemeenten zijn beschikbaar; gebruik `python3 scraper.py` zonder argument voor de actuele lijst.
