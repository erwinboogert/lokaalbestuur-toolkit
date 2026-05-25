# Lokaalbestuur Toolkit

Nederlandse gemeenten, provincies, waterschappen en samenwerkingsverbanden publiceren duizenden vergaderstukken per jaar. Ze zijn openbaar, maar in de praktijk onvindbaar: verspreid over honderden websites, als slecht doorzoekbare PDF's, zonder centrale index.

Deze toolkit downloadt die stukken automatisch en maakt ze doorzoekbaar — lokaal op je eigen machine, zonder account of API-sleutel. Je kunt er vervolgens open onderzoeksvragen over stellen: niet "zoek het woord woningbouw", maar "is er een verband tussen de bezuinigingen op sport en de stijgende obesitascijfers onder jongeren?"

---

## Wat de toolkit doet

De toolkit bestaat uit drie lagen die je los of samen kunt gebruiken:

**1. Downloaden** — De scraper haalt vergaderstukken op via de [Open Raadsinformatie API](https://openraadsinformatie.nl) (een initiatief van de Open State Foundation). Eerste keer duurt even; daarna haalt hij alleen nieuwe stukken op.

**2. Doorzoekbaar maken** — Uit de gedownloade PDF's bouwt de toolkit een lokale zoekindex (SQLite FTS5). Je kunt die direct bevragen via de terminal, of als startpunt gebruiken in een AI-gesprek.

**3. Onderzoeken** — De toolkit genereert een contextbriefing die beschrijft welke bronnen beschikbaar zijn, hoe ze doorzoekbaar zijn, en welk type organisatie relevant is voor welk onderwerp. Die briefing geef je mee aan een AI — het werkt met elke AI-assistent die tekst kan lezen, maar profiteert het meest van een AI die zelf bestanden kan openen en doorzoeken, zoals [Claude Code](https://claude.ai/code).

---

## Twee manieren om te beginnen

Er zijn twee ingangen — kies wat bij je past:

- **Bronnenboek (browser)** — een lokale webinterface. Dubbelklik `Bronnenboek.command` en ga aan de slag in je browser. Beste keuze voor de meeste journalisten: geen terminal nodig, één plek voor verkennen, scrapen, zoeken en monitoren.
- **Terminal** — `python3 toolkit.py ...`. Beste keuze als je wilt scripten, in cron wilt draaien, of Claude Code wilt gebruiken voor open onderzoeksvragen.

Beide ingangen werken op dezelfde lokale data — je kunt zonder problemen wisselen.

---

## Installatie

```bash
git clone https://github.com/erwinboogert/lokaalbestuur-toolkit.git
cd lokaalbestuur-toolkit
python3 toolkit.py setup
```

Dat is alles. Het setup-commando controleert je Python-versie, installeert de benodigde bibliotheken, test de API-verbinding en stelt de documentenmap in. Je hebt **Python 3.10 of hoger** nodig (de scrapers gebruiken nieuwe type-syntax).

**Voor Bronnenboek (browser)** — eenmalig `pip install flask` (of `pip install -r requirements.txt`).

**Optioneel maar aanbevolen:** [Claude Code](https://claude.ai/code) — een AI-assistent die je installeert als CLI en die zelf bestanden en mappen kan doorzoeken. Daarmee kun je de toolkit zijn volledige potentieel benutten (zie verderop).

---

## Bronnenboek — via de browser

Bronnenboek is een lokale webinterface die alle stappen visueel maakt: verkennen, scrapen, zoeken, dossiers en alerts. Hij draait op je eigen machine, zonder cloud of account.

### Starten

Dubbelklik op **`Bronnenboek.command`** in Finder. Een Terminal-venster opent met de servertitel "Bronnenboek", en je standaardbrowser opent automatisch op:

```
http://localhost:5001
```

Sluit het venster om de server te stoppen. Tip: sleep `Bronnenboek.command` naar je Dock voor één-klik-opstarten.

*Eerste keer:* macOS Gatekeeper kan vragen om bevestiging. Rechtsklik op het bestand → **Open** → bij de waarschuwing op "Openen" klikken. Daarna werkt dubbelklikken gewoon.

### Wat je erin kunt doen

- **Dashboard** — actieve dossiers, recente alerts, status per gemeente in één oogopslag.
- **Verkennen** — typ een gemeente, zie meteen welke provincie, veiligheidsregio, waterschap en GRs erbij horen. Klik door om elk orgaan met één klik te scrapen.
- **Scrapen** — periode kiezen (6/12/18/24 maanden), eerst simuleren of direct downloaden. Standaard worden nieuwe documenten **automatisch doorzoekbaar gemaakt** na de download (toggle uitschakelbaar).
- **Zoeken** — full-text door alle gedownloade stukken, per orgaan.
- **Dossiers & Alerts** — monitoringsdossiers met trefwoorden; alertrapporten verschijnen hier als er nieuwe treffers zijn.

Alles wat de terminal-versie kan, kan ook hier — alleen wie open onderzoeksvragen via Claude Code wil stellen, gebruikt nog de terminal.

---

## Aan de slag via de terminal — in vier stappen

### Stap 1 — Verkennen

Voordat je iets downloadt, laat de toolkit zien welke bronnen beschikbaar zijn voor een gemeente: de bijbehorende provincie, veiligheidsregio, relevante gemeenschappelijke regelingen en het waterschap.

```bash
python3 toolkit.py verkennen rotterdam
```

Je hoeft nu geen keuze te maken. Alles wat hier verschijnt kun je later alsnog downloaden als het relevant wordt voor je onderzoek.

### Stap 2 — Documenten downloaden

```bash
python3 scraper.py rotterdam
```

Documenten komen in `~/Documents/notulen/rotterdam/`. Je kunt de periode beperken:

```bash
python3 scraper.py rotterdam --jaren 1        # alleen het afgelopen jaar
python3 scraper.py rotterdam --vanaf 2024-01-01   # vanaf een specifieke datum
python3 scraper.py rotterdam --droog          # eerst zien wat er gedownload wordt
```

Wil je ook de provincie, veiligheidsregio, een GR of een waterschap downloaden:

```bash
python3 scraper_provincie.py zuid-holland
python3 scraper_vr.py rotterdam-rijnmond
python3 scraper_gr.py jeugdhulp-rijnmond
python3 scraper_waterschap.py hollandse-delta
```

### Stap 3 — Onderzoeksomgeving voorbereiden

```bash
python3 toolkit.py onderzoek rotterdam
```

Dit commando:
- Controleert welke bronnen beschikbaar zijn (gemeente, plus eventuele provincie, GRs en waterschappen)
- Bouwt de zoekindex bij
- Schrijft een **contextbriefing** naar `~/Documents/notulen/rotterdam/context.md`

De briefing beschrijft voor een AI welke bronnen er zijn, hoe ze doorzoekbaar zijn, en welk type organisatie relevant is voor welk onderwerp. Aan het einde staat ook een overzicht van beschikbare prompts en skills.

### Stap 4 — Onderzoeken

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
/woo-verzoek <onderwerp>
```

### Waterschappen

Alle 21 Nederlandse waterschappen staan vooraf geconfigureerd (13 via ORI API, 8 via iBabs SOAP). De toolkit weet welk waterschap bij welke gemeente hoort en toont dat automatisch bij `verkennen`. Downloaden:

```bash
python3 scraper_waterschap.py hollandse-delta
```

Relevant bij onderwerpen als waterveiligheid, klimaatadaptatie, grondwater en rioolwaterzuivering.

### Veiligheidsregio's

Alle 25 Nederlandse veiligheidsregio's zijn opgenomen in de toolkit. De bijbehorende regio wordt automatisch getoond bij `verkennen`. Downloaden:

```bash
python3 scraper_vr.py rotterdam-rijnmond
python3 scraper_vr.py --lijst              # toon alle 25 regio's
python3 scraper_vr.py --welke rotterdam    # welke VR hoort bij een gemeente?
```

De scraper ondersteunt alle publicatievormen: eigen websites (22 regio's), iBabs (Brabant-Noord), en Notubiz (Zeeland). Relevant bij onderwerpen als brandweer, crisisbeheersing en rampenbestrijding.

### Provincies

Alle 12 Nederlandse provincies staan in de catalogus. 10 zijn automatisch scrapebaar: 8 via de ORI API, 2 via Notubiz (Gelderland, Noord-Brabant). Drenthe en Zeeland hebben geen geautomatiseerde bron. De toolkit weet welke provincie bij welke gemeente hoort en toont dat automatisch bij `verkennen`. Downloaden:

```bash
python3 scraper_provincie.py zuid-holland
python3 scraper_provincie.py --lijst           # toon alle provincies en hun bron
python3 scraper_provincie.py --lijst-ori       # toon provincies in ORI API
```

Relevant bij onderwerpen als ruimtelijke ordening, natuur en stikstof, woningbouwafspraken, regionale infrastructuur, energietransitie en interbestuurlijk toezicht op gemeenten.

---

## Met Claude Code: wat het extra oplevert

Als je Claude Code installeert, krijgt de toolkit er een laag bij. Claude Code is een AI-assistent die je vanuit de terminal opent in een map en die zelf bestanden kan lezen, doorzoeken en vergelijken.

De toolkit is zo gebouwd dat Claude Code weet wat er beschikbaar is:

- De `context.md` briefing vertelt Claude welke bronnen er zijn en hoe hij moet zoeken
- De `prompts/` map bevat sjablonen voor veelvoorkomende onderzoeksvormen
- De `.claude/commands/` map bevat acties die Claude kan uitvoeren — rapport opslaan, WOO-verzoek genereren, alert instellen, trefwoorden verfijnen

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
# Verkennen (altijd als eerste stap bij een nieuwe gemeente)
python3 toolkit.py verkennen <gemeente>         # toon VR, GRs en waterschap

# Documenten downloaden
python3 scraper.py <gemeente>                   # raadsdocumenten gemeente
python3 scraper.py <gemeente> --jaren 1         # alleen het afgelopen jaar
python3 scraper.py <gemeente> --vanaf 2024-01-01  # vanaf een specifieke datum
python3 scraper.py <gemeente> --droog           # droog uitvoeren (geen downloads)
python3 scraper_vr.py <slug>                    # veiligheidsregio
python3 scraper_vr.py --lijst                   # toon alle 25 veiligheidsregio's
python3 scraper_vr.py --welke <gemeente>        # welke VR hoort bij gemeente?
python3 scraper_waterschap.py <slug>            # waterschap
python3 scraper_gr.py <slug>                    # gemeenschappelijke regeling
python3 scraper_provincie.py <slug>             # provincie
python3 scraper_provincie.py --lijst            # toon alle provincies en hun bron
python3 toolkit.py scrape --alles               # alle geconfigureerde organen bijwerken
python3 toolkit.py scrape-waterschappen         # alle geconfigureerde waterschappen
python3 toolkit.py scrape-regelingen            # alle geconfigureerde GRs
python3 toolkit.py scrape-provincies            # alle geconfigureerde provincies

# Onderzoek
python3 toolkit.py onderzoek <gemeente>         # zoekindex + Claude-briefing
python3 index.py <gemeente> "zoekterm"          # zoek direct in de index

# GRs ontdekken en instellen
python3 scraper_gr.py --lijst                   # toon geconfigureerde GRs
python3 scraper_gr.py --lijst-ori               # ontdek GRs in de ORI API
python3 scraper_gr.py --zoek <naam>             # zoek GR-organisatie in Notubiz

# Organen en bronnen instellen
python3 toolkit.py nieuw-orgaan                 # gemeente toevoegen (interactief)
python3 toolkit.py nieuwe-regeling              # GR toevoegen (interactief)
python3 toolkit.py nieuw-waterschap             # waterschap toevoegen (interactief)
python3 toolkit.py nieuwe-provincie             # provincie toevoegen (interactief)
python3 toolkit.py brondata-bijwerken           # GR-index uit overheid.nl verversen

# Monitoring
python3 toolkit.py nieuw-dossier                # dossier met trefwoorden aanmaken
python3 analyse.py --dossier <naam>             # analyse handmatig draaien

# Bronnenboek (webinterface)
python3 server.py                               # start zonder Bronnenboek.command

# Overzicht en onderhoud
python3 toolkit.py                              # dashboard
python3 toolkit.py status                       # uitgebreid statusoverzicht
python3 toolkit.py setup                        # installatie (afhankelijkheden + configuratie)
python3 toolkit.py check                        # installatiecheck
python3 toolkit.py fix-cron                     # crontab-regels controleren/herstellen
python3 toolkit.py --help                       # alle commando's met korte uitleg
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
├── Bronnenboek.command     dubbelklik-opstartscript voor de webinterface (macOS)
├── toolkit.py              hoofdinterface
├── api.py                  gedeelde scraper-functies (ORI / Notubiz / iBabs)
├── scraper.py              gemeentedocumenten (ORI API)
├── scraper_waterschap.py   waterschapstukken (ORI API + iBabs)
├── scraper_gr.py           GR-stukken (ORI / Notubiz / iBabs)
├── scraper_vr.py           veiligheidsregio's (website / Notubiz / iBabs)
├── scraper_provincie.py    provincies (ORI API / Notubiz)
├── analyse.py              keyword-alerts
├── index.py                zoekindex (SQLite FTS5)
├── server.py               Bronnenboek-webserver (Flask, poort 5001)
├── web/                    Bronnenboek-frontend (HTML + React/JSX)
├── bronnen/                catalogussen (gemeenten, waterschappen, GRs, VRs, provincies)
├── organen/                configuratie per orgaan
├── dossiers/               configuratie per monitoringsdossier
├── prompts/                sjablonen voor onderzoeksgesprekken
├── .claude/commands/       slash-commando's binnen dit project (rapport-opslaan, woo-verzoek, …)
├── skills/                 systeembrede skills (te kopiëren naar ~/.claude/commands/)
└── checklists/             rode-vlagchecklist lokaal bestuur

~/Documents/notulen/
├── rotterdam/
│   ├── gemeenteraad/2026-01-27/*.pdf
│   ├── index.db
│   ├── context.md              ← briefing voor Claude
│   └── alerts/alert-2026-03-26.md
├── waterschappen/hollandse-delta/
├── regelingen/jeugdhulp-rijnmond/
├── veiligheidsregios/rotterdam-rijnmond/
└── provincies/zuid-holland/
```
