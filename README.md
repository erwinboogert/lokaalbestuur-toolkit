# Lokaalbestuur Toolkit

Nederlandse gemeenten, waterschappen en samenwerkingsverbanden publiceren duizenden vergaderstukken per jaar. Ze zijn openbaar, maar in de praktijk onvindbaar: verspreid over honderden websites, als slecht doorzoekbare PDF's, zonder centrale index.

Deze toolkit downloadt die stukken automatisch en maakt ze doorzoekbaar — lokaal op je eigen machine, zonder account of API-sleutel. Je kunt er vervolgens open onderzoeksvragen over stellen: niet "zoek het woord woningbouw", maar "is er een verband tussen de bezuinigingen op sport en de stijgende obesitascijfers onder jongeren?"

---

## Wat de toolkit doet

De toolkit bestaat uit drie lagen die je los of samen kunt gebruiken:

**1. Downloaden** — De scraper haalt vergaderstukken op via de [Open Raadsinformatie API](https://openraadsinformatie.nl) (een initiatief van de Open State Foundation). Eerste keer duurt even; daarna haalt hij alleen nieuwe stukken op.

**2. Doorzoekbaar maken** — Uit de gedownloade PDF's bouwt de toolkit een lokale zoekindex (SQLite FTS5). Je kunt die direct bevragen via de terminal, of als startpunt gebruiken in een AI-gesprek.

**3. Onderzoeken** — De toolkit genereert een contextbriefing die beschrijft welke bronnen beschikbaar zijn, hoe ze doorzoekbaar zijn, en welk type organisatie relevant is voor welk onderwerp. Die briefing geef je mee aan een AI — het werkt met elke AI-assistent die tekst kan lezen, maar profiteert het meest van een AI die zelf bestanden kan openen en doorzoeken, zoals [Claude Code](https://claude.ai/code).

---

## Wat je nodig hebt

- Python 3.10 of hoger
- `pdfplumber` voor tekstextractie

```bash
pip install pdfplumber
python3 toolkit.py check    # controleert of alles klopt
```

**Optioneel maar aanbevolen:** [Claude Code](https://claude.ai/code) — een AI-assistent die je installeert als CLI en die zelf bestanden en mappen kan doorzoeken. Daarmee kun je de toolkit zijn volledige potentieel benutten (zie verderop).

---

## Aan de slag — in drie stappen

### Stap 1 — Gemeente instellen en documenten downloaden

```bash
python3 toolkit.py nieuw-orgaan
```

Een wizard vraagt naar naam en type. Voor gemeenten zoekt de toolkit daarna automatisch op welke gemeenschappelijke regelingen (GRs) erbij horen en stelt die voor om toe te voegen. Daarna download je de documenten:

```bash
python3 toolkit.py scrape rotterdam
```

Documenten komen in `~/Documents/notulen/rotterdam/`. Wil je eerst zien wat er gedownload wordt zonder iets op te slaan:

```bash
python3 toolkit.py scrape rotterdam --droog
```

### Stap 2 — Onderzoeksomgeving voorbereiden

```bash
python3 toolkit.py onderzoek rotterdam
```

Dit commando:
- Controleert welke bronnen beschikbaar zijn (gemeente, plus eventuele GRs en waterschappen)
- Bouwt de zoekindex bij
- Schrijft een **contextbriefing** naar `~/Documents/notulen/rotterdam/context.md`

De briefing beschrijft voor een AI welke bronnen er zijn, hoe ze doorzoekbaar zijn, en welk type organisatie relevant is voor welk onderwerp. Aan het einde staat ook een overzicht van beschikbare prompts en skills.

### Stap 3 — Onderzoeken

**Zonder AI — direct via de terminal:**

```bash
python3 index.py rotterdam "sportaccommodaties"
```

Geeft je een lijst van documenten met die term, inclusief datum en vergadertype. Nuttig voor gerichte zoekopdrachten als je al weet waar je naar zoekt.

**Met Claude Code:**

```bash
claude ~/Documents/notulen/rotterdam
```

Open Claude Code in de documentenmap. Typ dan:

```
Lees context.md
```

Claude leest de briefing en weet meteen welke bronnen er zijn en hoe hij moet zoeken. Stel daarna je vraag. Zie `prompts/vrije-vraag.md` voor een sjabloon.

Het verschil: zonder AI krijg je treffers op trefwoorden. Met Claude Code kun je vragen stellen als: "welke besluiten over jeugdhulp zijn er genomen in de afgelopen drie jaar, en wat ontbreekt er in de verantwoording?" — en Claude leest zelf de relevante stukken.

---

## Meer bronnen toevoegen

De briefing wordt rijker naarmate je meer bronnen toevoegt. Gemeenschappelijke regelingen (GRs) en waterschappen bevatten vaak uitvoeringsinformatie die de gemeente zelf niet heeft.

### Gemeenschappelijke regelingen (GRs)

GRs zijn samenwerkingsverbanden tussen gemeenten — voor jeugdzorg, milieu, veiligheid, sociale diensten. Ze voeren beleid uit dat de gemeente heeft uitbesteed. Als je wilt weten wat er in de praktijk van dat beleid terechtkomt, moet je daar kijken.

Na `toolkit.py onderzoek` detecteert de toolkit automatisch welke GRs bij de gemeente horen en slaat die op als `regelingen.md` in de documentenmap. De detectie combineert twee bronnen: tekst uit de vergaderstukken én de officiële deelnemersregistratie van organisaties.overheid.nl. GRs die zelden bij naam in de stukken staan (bijv. veiligheidsregio's, recreatieschappen) verschijnen daardoor toch in de lijst.

Of je die GR-stukken ook kunt downloaden, hangt af van hoe de GR publiceert:

**Via de ORI API — direct scrapebaar**
Sommige GRs zijn geïndexeerd in de Open Raadsinformatie API, net als gemeenten. Die zijn direct te downloaden:

```bash
python3 toolkit.py nieuwe-regeling    # slug en ORI-indexnaam invoeren
python3 scraper_gr.py <naam>
```

Of een GR in ORI staat, zie je met `python3 scraper_gr.py --lijst-ori`.

**Via Notubiz API — direct scrapebaar**
De meeste GRs publiceren via Notubiz. De scraper kan die direct benaderen als je het Notubiz-organisatie-ID opgeeft in `bronnen/regelingen.json`:

```bash
python3 scraper_gr.py --zoek jeugdhulp   # zoek het ID op in Notubiz
# voeg notubiz_id toe aan bronnen/regelingen.json
python3 scraper_gr.py jeugdhulp-rijnmond
```

Voorbeelden: GGD Rotterdam-Rijnmond, MRDH, Jeugdzorg Rijnmond.

**Via iBabs SOAP — direct scrapebaar**
GRs die een iBabs-vergaderportaal gebruiken zijn scrapebaar via de SOAP API. Voeg `ibabs_naam` toe in `bronnen/regelingen.json` — de waarde is de Sitename in de portaal-URL (bijv. `dcmr` uit `dcmr.bestuurlijkeinformatie.nl`):

```bash
python3 scraper_gr.py <naam>   # werkt zodra ibabs_naam is ingevuld
```

Voorbeelden: DCMR Milieudienst Rijnmond, veiligheidsregio's.

**Geen portaal — WOO-verzoek**
Een kleine groep GRs publiceert nauwelijks openbaar. Ze zijn wettelijk verplicht dat wel te doen (Wgr art. 22, Woo). Je kunt een formeel verzoek opstellen met:

```
/wob-verzoek <onderwerp>
```

### Waterschappen

Alle 21 Nederlandse waterschappen die via de ORI API beschikbaar zijn staan vooraf geconfigureerd. Downloaden:

```bash
python3 toolkit.py scrape hollandse-delta
```

Relevant bij onderwerpen als waterveiligheid, klimaatadaptatie, grondwater en rioolwaterzuivering.

---

## Met Claude Code: wat het extra oplevert

Als je Claude Code installeert, krijgt de toolkit er een laag bij. Claude Code is een AI-assistent die je vanuit de terminal opent in een map en die zelf bestanden kan lezen, doorzoeken en vergelijken.

De toolkit is zo gebouwd dat Claude Code weet wat er beschikbaar is:

- De `context.md` briefing vertelt Claude welke bronnen er zijn en hoe hij moet zoeken
- De `prompts/` map bevat sjablonen voor veelvoorkomende onderzoeksvormen
- De `.claude/skills/` map bevat acties die Claude kan uitvoeren — rapport opslaan, WOO-verzoek genereren, alert instellen

Na een onderzoekssessie biedt Claude zelf aan welke vervolgstappen zinvol zijn. Dat overzicht staat ook in de briefing:

| Prompt | Wanneer |
|---|---|
| `prompts/vrije-vraag.md` | Brede onderzoeksvraag zonder vooraf bekende trefwoorden — **start hier** |
| `prompts/raadsstukken-analyse.md` | Gestructureerde analyse van een bekend dossier |
| `prompts/rode-vlaggen.md` | Na een onderzoekssessie: checklist van zeven categorieën op misstanden |
| `prompts/wederhoor.md` | Gerichte vragen per partij op basis van de stukken |
| `prompts/bronnenbrief.md` | Eerste contactbrief aan een bron of betrokkene |

---

## Automatische monitoring (optioneel)

Als je een gemeente intensief volgt en wekelijks gesignaleerd wilt worden bij nieuwe relevante stukken:

```bash
python3 toolkit.py nieuw-dossier
```

Een wizard vraagt naar trefwoorden. Daarna draait de analyse automatisch elke week via crontab. Bij treffers verschijnt een macOS-melding en staat een alertrapport klaar in `~/Documents/notulen/<orgaan>/alerts/`.

Je hebt dit niet nodig voor een eerste onderzoek — het is aanvullend op de primaire werkwijze.

---

## Alle commando's

```bash
# Documenten
python3 toolkit.py scrape <orgaan>              # download nieuwe stukken
python3 toolkit.py scrape <orgaan> --droog      # droog uitvoeren (geen downloads)
python3 toolkit.py scrape --alles               # alle geconfigureerde organen bijwerken

# Onderzoek
python3 toolkit.py onderzoek <gemeente>         # bronnencheck + zoekindex + briefing
python3 index.py <gemeente> "zoekterm"          # zoek direct in de index

# GRs ontdekken en instellen
python3 scraper_gr.py --lijst                   # toon geconfigureerde GRs
python3 scraper_gr.py --lijst-ori               # ontdek GRs in de ORI API
python3 scraper_gr.py --zoek <naam>             # zoek GR-organisatie in Notubiz

# Organen en bronnen instellen
python3 toolkit.py nieuw-orgaan                 # gemeente, waterschap of GR toevoegen

# Monitoring
python3 toolkit.py nieuw-dossier                # dossier met trefwoorden aanmaken
python3 analyse.py --dossier <naam>             # handmatig alert draaien

# Overzicht
python3 toolkit.py                              # dashboard
python3 toolkit.py status                       # uitgebreid statusoverzicht
python3 toolkit.py check                        # installatiecheck
```

---

## Eerlijke verwachtingen

**Tekstextractie is niet waterdicht.** Raadsstukken zijn als PDF notoir slecht van kwaliteit — gescand, slecht opgemaakt, soms een foto van een pagina. De toolkit doet zijn best maar mist regelmatig passages. Een lege treffer betekent niet dat iets er niet in staat.

**Dit is een startpunt, geen eindpunt.** Raadsstukken vertellen wat er formeel besloten is, niet waarom, en niet wat er buiten de vergaderzaal is afgesproken.

**Het signaleert, maar beoordeelt niet.** De redactionele afweging blijft bij jou.

---

## Mapstructuur

```
lokaalbestuur-toolkit/
├── toolkit.py              hoofdinterface
├── scraper.py              gemeentedocumenten (ORI API)
├── scraper_waterschap.py   waterschapstukken (ORI API)
├── scraper_gr.py           GR-stukken
├── analyse.py              keyword-alerts
├── index.py                zoekindex (SQLite FTS5)
├── bronnen/                catalogussen (gemeenten, waterschappen, GRs)
├── organen/                configuratie per orgaan
├── dossiers/               configuratie per monitoringsdossier
├── prompts/                sjablonen voor onderzoeksgesprekken
└── checklists/             rode-vlagchecklist lokaal bestuur

~/Documents/notulen/
├── rotterdam/
│   ├── gemeenteraad/2026-01-27/*.pdf
│   ├── index.db
│   ├── context.md              ← briefing voor Claude
│   └── alerts/alert-2026-03-26.md
├── waterschappen/hollandse-delta/
└── regelingen/jeugdhulp-rijnmond/
```
