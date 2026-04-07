# Roadmap — Lokaalbestuur Toolkit

## Voor wie is dit, en wanneer werkt het

Deze toolkit is het meest nuttig voor journalisten die één gemeente of regio intensief volgen en een specifiek dossier over langere tijd willen bijhouden. Denk aan een journalist die maandenlang een grondtransactiedossier volgt, of iemand die wil weten hoe een gemeente over de jaren heen omgaat met een onderwerp als woningbouw of jeugdzorg. In die situatie — terugkerende monitoring van bekende trefwoorden in een afgebakende bron — levert de toolkit echt tijdswinst.

De toolkit werkt minder goed als snelle verkenning van een onbekend onderwerp, als instrument voor breaking news, of als vervanging van het lezen van de stukken zelf. Het is een zeef, geen samenvatting.

**De eerlijke vergelijking:** gemeentelijke websites, Notubiz en iBabs hebben zelf al zoekfuncties. Wat deze toolkit toevoegt is de automatisering over tijd — je hoeft niet elke week zelf te zoeken — en de koppeling aan Claude voor gestructureerde analyse. Dat is waardevol, maar incrementeel.

**De installatiedrempel is reëel.** Deze toolkit is op dit moment het meest geschikt voor journalisten die vertrouwd zijn met de terminal en niet terugschrikken voor Python. Dat is een kleinere groep dan de lokale en regionale journalistiek als geheel. Wie het project doorontwikkelt, moet zich bewust zijn van die grens: ofwel de drempel verlagen, ofwel bewust kiezen voor een smallere doelgroep van technisch vaardige onderzoekers.

## De drempel verlagen: praktische tips voor onboarding

De installatiedrempel hoeft geen absolute blokkade te zijn. Een aantal praktische maatregelen kan helpen zonder dat de toolkit complexer of minder lokaal wordt.

**Laat een AI-CLI je door de installatie leiden.** Claude Code en Gemini CLI zijn AI-assistenten die je vanuit de terminal gebruikt en die daadwerkelijk bestanden kunnen lezen en commando's kunnen uitvoeren op je eigen machine. Je kunt zo'n assistent wijzen op de GitHub-repository van deze toolkit en vragen: *"Help me deze toolkit installeren en mijn eerste dossier instellen."* De assistent leest de README, controleert wat er al staat, stelt de juiste vragen en typt de benodigde commando's voor je uit. Dit maakt de drempel voor minder technisch onderlegde journalisten aanzienlijk lager. Claude Code is te installeren via `npm install -g @anthropic-ai/claude-code`, Gemini CLI via `npm install -g @google/gemini-cli`.

**✅ Een vooraf ingesteld voorbeelddossier.** `dossiers/voorbeeld-woningbouw.json` + `organen/amsterdam.json` — nieuwe gebruikers zien meteen hoe een dossier eruitziet en kunnen het als sjabloon gebruiken.

**Een installatiecheck.** Het commando `python3 toolkit.py check` controleert automatisch of alles goed staat: Python-versie, benodigde bibliotheken, verbinding met de API, aanwezige dossiers en crontab-regels. Nieuwe gebruikers zien direct wat er nog mist zonder zelf te moeten debuggen. Dit commando is beschikbaar vanaf de huidige versie van de toolkit.

**Een korte videowalthrough.** Twee minuten schermopname van terminal tot eerste alert is voor veel journalisten toegankelijker dan een geschreven README, hoe goed die ook is. Dit kost weinig maar verlaagt de drempel sterk.

---

## ✅ Fase 1 — Basistoolkit

Doel: raadsstukken van elke Nederlandse gemeente kunnen downloaden via de Open Raadsinformatie API.

- `scraper.py` — haalt vergaderingen en bijbehorende PDF's op via de ORI-API
- Automatische mappenstructuur per gemeente, vergadertype en datum
- Droog-modus (`--droog`) om te zien wat er gedownload zou worden zonder iets op te slaan
- Logging naar bestand en stdout
- Geen externe bibliotheken vereist (alleen standaard Python 3)

---

## ✅ Fase 2 — Automatische monitoring

Doel: automatisch gesignaleerd worden als nieuwe raadsstukken relevante onderwerpen bevatten.

- `analyse.py` — doorzoekt nieuwe PDF's op configureerbare trefwoorden
- State-tracking via JSON: al geanalyseerde bestanden worden overgeslagen
- Alertrapport als Markdown met tekstfragmenten rondom trefwoorden
- macOS-melding bij treffers
- Instelbaar via `DOSSIER_LABEL`, `TREFWOORDEN`, `CONTEXT_GROOTTE`
- Crontab-instructies in README voor volledig geautomatiseerde weekelijkse run

---

## ✅ Fase 3 — Zoeken en verdiepen

Doel: van keyword-alerts naar echte onderzoekstool waarmee je dwars door het archief kunt graven.

### ✅ Volledige tekstextractie
`pdfplumber` vervangt `pypdf` — betere tekstkwaliteit bij gescande PDF's en complexe opmaak (tabellen, kolommen).

### ✅ Lokale full-text zoekindex
`index.py` — SQLite FTS5-index van alle gedownloade stukken. Eenmalig opbouwen, daarna milliseconden per zoekopdracht.

```bash
python3 index.py rotterdam                      # bouw/update index
python3 index.py rotterdam "grondprijs"         # zoek
python3 index.py rotterdam "grond OR woningbouw" --uitvoer  # exporteer naar Markdown
python3 index.py rotterdam --status             # statistieken
```

Resultaten bevatten: bestandsnaam, vergaderdatum, vergadertype, snippet met gemarkeerde treffers.

### ✅ Timeline-reconstructie per dossier
`tijdlijn.py` — zoekt alle treffers voor een term door het archief, sorteert chronologisch en exporteert als Markdown naar `~/Documents/notulen/<orgaan>/tijdlijnen/`.

```bash
python3 tijdlijn.py rotterdam "woningbouw"
python3 tijdlijn.py --dossier asielopvang "spreidingswet"
```

### ✅ Partijposities tracken
`partijen.py` — heuristische sprekerdetectie op basis van gangbare Nederlandse vergadernotatie. Koppelt fragmenten aan fracties, gegroepeerd per partij. Waarschuwt expliciet als geen sprekers worden herkend.

```bash
python3 partijen.py rotterdam "woningbouw"
python3 partijen.py --dossier asielopvang "spreidingswet" --uitvoer
```

Resultaten in: `~/Documents/notulen/<orgaan>/partijposities/`

---

## ✅ Fase 4 — Onderzoeksondersteuning

Doel: de ruwe data vertalen naar journalistiek bruikbare analyses en onderzoeksstructuur.

- `prompts/raadsstukken-analyse.md` — twee herbruikbare Claude-prompts: huidige stand van zaken (tijdlijn, beslissingen, partijposities) en vooruitblik (aankomende beslismomenten, politieke verwachtingen)
- `checklists/red-flag-lokale-overheid.md` — rode-vlagchecklist met 7 categorieën (bestuur, financiën, aanbesteding, subsidies, vastgoed, transparantie, toezicht) en urgentieschaal
- `.claude/skills/rapport-opslaan.md` — analyse opslaan als rapport en alert aanbieden
- `.claude/skills/alert-beoordelen.md` — binnengekomen alert beoordelen op urgentie en vervolgactie
- `.claude/skills/trefwoorden-verfijnen.md` — trefwoorden van een dossier analyseren en verbeteren
- `.claude/skills/wob-verzoek.md` — formeel WOO/WOB-verzoek genereren

---

## ✅ Fase 5 — Promptbibliotheek uitbreiden

Doel: de toolkit ook bruikbaar maken voor de schrijf- en contactfase van het onderzoek, niet alleen de analysefase.

- `prompts/wederhoor.md` — gerichte vragen per partij op basis van passages uit de stukken, met bronvermelding
- `prompts/bronnenbrief.md` — eerste contactbrief aan bron of betrokkene, toon aanpasbaar per doelgroep
- `prompts/vergelijking.md` — vergelijk meerdere gemeenten op hetzelfde onderwerp; feitelijk + verklarend
- `prompts/budget.md` — analyseer begrotingsposten, kostenoverschrijdingen en financiële keuzes

---

## ✅ Fase 5b — Orgaan-architectuur

Doel: de toolkit voorbereiden op meerdere brontypen door orgaan en dossier te scheiden.

- `organen/<naam>.json` — configuratie per orgaan: type (gemeente/waterschap/GR), bron, vergadertypen
- `dossiers/<naam>.json` gebruikt nu `"orgaan"` in plaats van `"gemeente"` als referentie
- `scraper.py` laadt vergadertypen automatisch uit `organen/<naam>.json` als dat bestand aanwezig is
- `toolkit.py nieuw-orgaan` — interactieve wizard met standaard vergadertypen per orgaantype
- Standaard vergadertypen gedefinieerd voor gemeente, waterschap en GR

---

## Losse taken

Kleine verbeteringen en acties die buiten de fases vallen.

- **GitHub-repository aanmaken** — repository publiek zetten op GitHub onder naam van Erwin Boogert; vereist `gh auth login` en `gh repo create`
- **Dossier kan meerdere organen volgen** — `"organen": ["rotterdam", "utrecht", "groningen"]` in dossier-config; `analyse.py` itereert over meerdere documentenmappen en bundelt resultaten in één rapport. Bewust uitgesteld: vereist substantiële refactor van `analyse.py`.

---

## Fase 6 — Gemeenschappelijke regelingen en waterschappen

Doel: het onderzoeksdomein uitbreiden naar twee democratische lagen die structureel worden genegeerd door lokale journalisten, maar over aanzienlijk publiek geld en publieke belangen gaan.

### Architectuurkeuze: modulair intern, unified extern

Fase 6 en 7 worden gebouwd als losse scripts naast de bestaande `scraper.py` en `analyse.py` — dezelfde aanpak als de huidige toolkit. Elke bron heeft zijn eigen scraper; de journalist spreekt altijd via `toolkit.py`. Zo blijft de code overzichtelijk en kan elke bron onafhankelijk worden onderhouden, terwijl de journalist maar één interface hoeft te kennen.

**Nieuwe bestandsstructuur:**

```
lokaalbestuur-toolkit/
├── scraper.py              ← bestaand (ORI-API, gemeenten)
├── scraper_gr.py           ← nieuw: gemeenschappelijke regelingen
├── scraper_waterschap.py   ← nieuw: waterschappen
├── scraper_cbs.py          ← nieuw (fase 7): iv3/CBS financiën
├── bronnen/                ← configuratie per brontype
│   ├── regelingen.json     ← actieve gemeenschappelijke regelingen
│   ├── waterschappen.json  ← actieve waterschappen (fase 6b)
│   ├── gemeentecodes.json  ← CBS-gemeentecodes (fase 7)
│   └── iv3datasets.json    ← CBS dataset-IDs per jaar (fase 7)
```

Het dashboard (`python3 toolkit.py`) toont alle actieve bronnen in één overzicht:

```
── Actieve bronnen ───────────────────────────────
  Raadsstukken    12 gemeenten   laatste run: 2 dagen geleden
  Regelingen       3 actief      laatste run: 5 dagen geleden
  Waterschappen    1 actief      laatste run: nooit
  Financiën        4 gemeenten   laatste update: jan 2026
```

### ✅ Fase 6a — Gemeenschappelijke regelingen (infrastructuur)

Gemeenten voeren steeds meer taken niet zelf uit, maar via samenwerkingsverbanden met andere gemeenten. Denk aan sociale diensten, regionale omgevingsdiensten, veiligheidsregio's en jeugdhulpregio's. Deze zogeheten gemeenschappelijke regelingen hebben eigen besturen, eigen begrotingen en eigen vergaderingen — maar vallen buiten het zicht van de individuele gemeenteraad. Er is nauwelijks democratisch toezicht en journalistieke aandacht ontbreekt vrijwel volledig.

`scraper_gr.py` biedt de infrastructuur: catalogus, scraper, toolkit-integratie.

```bash
python3 scraper_gr.py drechtsteden           # download vergaderstukken
python3 scraper_gr.py drechtsteden --droog   # droog uitvoeren
python3 scraper_gr.py --lijst                # toon geconfigureerde GRs
python3 scraper_gr.py --lijst-ori            # toon wat beschikbaar is in ORI
```

Output in: `~/Documents/notulen/regelingen/<naam>/`
Catalogus: `bronnen/regelingen.json`

**Toolkit-commando's:**
```bash
python3 toolkit.py nieuwe-regeling    # voeg een GR toe aan bronnen/regelingen.json
python3 toolkit.py scrape-regelingen  # download nieuwe stukken voor alle actieve regelingen
```

**Beperking:** GRs staan momenteel niet in de ORI API — de API bevat uitsluitend gemeenten (ori_), waterschappen (owi_) en provincies (osi_). De infrastructuur werkt zodra een GR via ORI ontsloten wordt, of wanneer de bron wordt uitgebreid naar Notubiz.

### Juridisch kader: GRs zijn verplicht openbaar

GRs zijn bestuursorganen en vallen onder twee wetten:

- **Wet gemeenschappelijke regelingen (Wgr), artikel 22** — vergaderingen van het Algemeen Bestuur (AB) zijn openbaar. Sluiting achter gesloten deuren vereist een verzoek van een vijfde van de leden of de voorzitter.
- **Wet open overheid (Woo)** — GRs vallen als bestuursorgaan onder de actieve openbaarmakingsplicht. In theorie moeten ze vergaderstukken, agenda's en notulen proactief publiceren. In de praktijk is naleving wisselend: de Woo-implementatie bij GRs is nog volop in uitrol.

**Praktijkprobleem:** er is geen centraal publicatiekanaal voor GR-documenten zoals ORI voor gemeenten. Veel GRs publiceren via Notubiz (vaak achter login), sommige hebben een eigen website, een deel publiceert nauwelijks iets.

### Open punt: Notubiz als bron voor GR-documenten

GR-documenten zijn doorgaans vindbaar via Notubiz (notubiz.nl). De Notubiz API is verkend en deels publiek toegankelijk:

- `api.notubiz.nl/organisations?format=json` — werkt zonder authenticatie; geeft **526 organisaties** terug als JSON/XML, inclusief GRs (o.a. Nieuw Reijerwaard id 1659, Hoeksche Waard id 937, Meerinzicht id 1982, GGD Zeeland id 3816, Jeugdzorg Rijnmond id 4073, Regio Foodvalley id 3973). Velden: naam, id, logo, coördinaten, `last_change`.
- `api.notubiz.nl/events` — geeft HTTP 400, met of zonder `organisation_id`. Vereist vrijwel zeker een API-sleutel als verplichte parameter.
- Subdomein-pages (`organisatie.notubiz.nl`) — HTTP 403, achter authenticatie.
- De API-documentatiepagina zelf zegt: "Er is nog geen documentatie beschikbaar voor publiek gebruik."
- HTML-scraping is niet haalbaar: documenten zitten niet op publieke webpagina's maar achter login.

**Drie mogelijke paden:**

1. **API-sleutel aanvragen bij Notubiz** — laagste technische drempel als ze die verstrekken. Aanvraag gedaan (april 2025); uitkomst onbekend.
2. **Wachten op ORI-uitbreiding** — ORI indexeert al Notubiz-content van gemeenten; mogelijk worden GRs in de toekomst ook opgenomen.
3. **Per GR handmatig een bron hardcoderen** — sommige GRs hebben een eigen website buiten Notubiz. Niet schaalbaar voor generieke scraper, maar bruikbaar als aanvulling in de catalogus.

### Nieuwe richting: GR-navigator in plaats van GR-scraper

Omdat een generieke scraper voor GRs voorlopig niet haalbaar is, kiest de toolkit voor een andere benadering: **de journalist zo ver mogelijk begeleiden naar de informatie**, ook als die niet automatisch opgehaald kan worden.

De kern van dit idee: de toolkit weet per GR wat de status is (wel/niet publiek, via welk kanaal, contactadres) en geeft de journalist concrete vervolgstappen — inclusief een WOO-verzoek, het juiste loket, of de juiste vragen.

**Wat de GR-navigator doet:**

- Catalogus per GR met: brontype (`ori`, `notubiz`, `website`, `geen`), URL indien bekend, contactadres AB-secretariaat, status actieve openbaarmaking
- **Als bron beschikbaar:** automatisch scrapen (zodra API-sleutel of ORI-ontsluiting beschikbaar)
- **Als bron niet beschikbaar:**
  - Pre-ingevuld WOO-verzoek voor die specifieke GR (`/wob-verzoek` skill)
  - Directe verwijzing naar het AB-secretariaat met de juiste vragen ("Waar publiceert u vergaderstukken van het Algemeen Bestuur?")
  - Toelichting op de wettelijke plicht (Wgr art. 22, Woo) die de journalist kan aanhalen
  - Eventuele eigen website van de GR als handmatige bron

**Concreet toolkit-commando (te bouwen):**
```bash
python3 toolkit.py gr-info drechtsteden     # wat weten we van deze GR, en wat kan de journalist doen?
```

Output: een Markdown-rapport met bronstatus, contactgegevens, en — indien nodig — een ingevuld WOO-verzoek of mailsjabloon naar het secretariaat.

**Waarom dit beter is dan alleen wachten op de API:**
GRs zijn wettelijk verplicht openbaar te vergaderen. Een journalist die actief vraagt om de stukken — gewapend met de juiste wettelijke grondslag en een concreet verzoek — heeft een stevige positie. De toolkit kan die positie ondersteunen, ook zonder technische toegang tot de documenten.

### ✅ Fase 6b — Waterschappen

Waterschappen zijn democratisch gekozen bestuursorganen die verantwoordelijk zijn voor waterveiligheid, dijkbeheer, rioolwaterzuivering en grondwaterpeil. Ze beheren samen miljarden aan publiek geld en vergaderen openbaar, maar worden in de lokale en regionale journalistiek vrijwel nooit bericht. Met de toenemende druk van klimaatverandering wordt hun werk steeds relevanter.

Waterschappen zijn — in tegenstelling tot gemeenschappelijke regelingen — wél ontsloten via de ORI API (prefix `owi_`). Daarmee was de implementatie technisch vergelijkbaar met de bestaande gemeente-scraper.

**13 waterschappen beschikbaar in ORI**, alle vooraf geconfigureerd in `bronnen/waterschappen.json`:
Aa en Maas, Brabantse Delta, De Dommel, Hollandse Delta, Hollands Noorderkwartier, Delfland, Hunze en Aa's, Limburg, Scheldestromen, Vechtstromen, Amstel Gooi en Vecht, Wetterskip Fryslân, Zuiderzeeland.

**Nieuw bestand:** `scraper_waterschap.py`

```bash
python3 scraper_waterschap.py hollandse-delta           # download vergaderstukken
python3 scraper_waterschap.py hollandse-delta --droog   # droog uitvoeren
python3 scraper_waterschap.py --lijst                   # toon geconfigureerde waterschappen
python3 scraper_waterschap.py --lijst-ori               # toon alle owi_-indices in ORI
```

Output in: `~/Documents/notulen/waterschappen/<naam>/`

**Toolkit-commando's:**
```bash
python3 toolkit.py nieuw-waterschap     # voeg een waterschap toe aan de catalogus
python3 toolkit.py scrape-waterschappen # download stukken voor alle waterschappen
```

### Bouwvolgorde fase 6

| Stap | Wat | Reden |
|---|---|---|
| 1 | `bronnen/` mapstructuur + configuratieformat | Fundament voor beide scrapers |
| 2 | `scraper_gr.py` | Makkelijkst: zit al deels in ORI-API |
| 3 | Dashboard uitbreiding | Journalist ziet meteen wat er actief is |
| 4 | `scraper_waterschap.py` | Complexst: per waterschap maatwerk |

---

## Fase 7 — Financiële vergelijkingsdata (iv3 / CBS)

Doel: lokale journalisten in staat stellen om gemeentelijke financiën niet alleen te lezen uit de stukken, maar ook te vergelijken met andere gemeenten op basis van gestandaardiseerde overheidscijfers.

Alle Nederlandse gemeenten zijn wettelijk verplicht hun financiële verantwoording te rapporteren aan het Rijk via een vaste systematiek die iv3 heet. Het Centraal Bureau voor de Statistiek (CBS) verzamelt deze data en maakt die openbaar. De cijfers zijn gestandaardiseerd en vergelijkbaar: je kunt exact zien hoeveel een gemeente uitgeeft aan jeugdzorg, hoe hoog de schulden zijn, hoe reserves zich ontwikkelen — en dat afzetten tegen vergelijkbare gemeenten.

Deze data wordt door lokale journalisten nauwelijks gebruikt, terwijl het precies het type materiaal is dat signalen oplevert: gemeente A geeft structureel 40% meer uit aan externe inhuur dan vergelijkbare gemeenten, gemeente B heeft de afvalstoffenheffing verhoogd terwijl de reserve groeit. Gecombineerd met raadsstukken uit de bestaande toolkit ontstaat een krachtige combinatie: je ziet wat er besloten is én of het geld er ook daadwerkelijk naartoe gegaan is.

De financiële data is institutioneel (gemeente als geheel) en valt daarmee binnen de bestaande privacygrenzen van de toolkit.

### ✅ Data ophalen en opslaan

`scraper_cbs.py` — haalt de jaarrekening op uit de onbewerkte iv3-data van CBS (dataderden.cbs.nl), slaat op als CSV per gemeente per jaar.

```bash
python3 scraper_cbs.py rotterdam              # laatste 3 beschikbare jaren
python3 scraper_cbs.py rotterdam 2022         # specifiek jaar
python3 scraper_cbs.py rotterdam --droog      # toon wat opgehaald zou worden
python3 scraper_cbs.py --lijst                # toon geconfigureerde gemeenten
```

Output in: `~/Documents/notulen/<gemeente>/financien/iv3_<jaar>.csv`

Eenheid: 1.000 euro. Velden: taakveld/balanspost-code, categorie, eerste en tweede plaatsing.
Gemeentecodes: `bronnen/gemeentecodes.json` (37 gemeenten, uitbreidbaar).
Dataset-IDs per jaar: `bronnen/iv3datasets.json` (2010–2025).

**Toolkit-commando:**
```bash
python3 toolkit.py financien rotterdam        # haal data op via toolkit
python3 toolkit.py financien rotterdam 2022   # specifiek jaar
```

### Nog open

- **iv3-codes vertalen naar leesbare labels** — de taakveld/balanspost-codes (bijv. `6.1`, `L1.1`) zijn CBS-codes uit het Besluit begroting en verantwoording. Zonder vertaaltabel zijn de CSV-bestanden niet direct leesbaar voor een journalist. Vereist een handmatig samengestelde of extern verkregen codetabel.

- **Vergelijkbare gemeenten bepalen** — voor een betekenisvolle vergelijking moet je weten welke gemeenten vergelijkbaar zijn (inwonertal, stedelijkheidsgraad, centrumfunctie). CBS heeft een gemeentetypologie; die moet worden geïntegreerd.

- **Afwijkingen signaleren** — automatisch detecteren wanneer een gemeente significant afwijkt van vergelijkbare gemeenten. Vereist statistische keuzes (mediaan, drempelwaarden) en domeinkennis over wat een relevante afwijking is.

- **Vergelijkingsrapport** — Markdown-rapport met opvallende afwijkingen per gemeente, bruikbaar als startpunt voor een verhaal. Dit bouwt voort op de drie punten hierboven.

---

## Grenzen — wat deze toolkit niet moet worden

Dit gedeelte dient als kompas: het beschrijft de richting die bewust niet wordt ingeslagen, en waarom. Deze grenzen zijn onderdeel van de filosofie van het project, niet een tijdelijke beperking.

### Geen persoonsgegevens tracken

De toolkit richt zich op instituties en besluiten, niet op individuen. Zodra je begint met het systematisch volgen van wat een specifieke wethouder, ambtenaar of raadslid zegt of doet, verander je van onderzoeksinstrument in surveillancetool. Dat is een principieel andere activiteit, met andere ethische en juridische implicaties. De grens ligt bij: wat besluit de organisatie, niet wie zei wat.

### Geen sociale media

Raadsleden twitteren, wethouders geven persconferenties en doen uitspraken buiten vergaderingen om. Die uitspraken kunnen journalistiek relevant zijn, maar sociale media-monitoring is een volledig ander domein — met andere dynamieken, andere bronkwaliteit en andere juridische grenzen. De kracht van deze toolkit zit juist in het werken met officiële, openbare institutionele documenten. Sociale media toevoegen leidt af van dat kernidee.

### Geen nationale politiek

De waarde van deze toolkit zit in het lokale en regionale: de dingen die te klein zijn voor nationale redacties maar te technisch voor de lokale krant met drie redacteuren. Zodra de focus verschuift naar Tweede Kamer, ministeries of landelijke partijpolitiek, is er geen gebrek aan tools, mensen en budget meer. Daar voegt deze toolkit niets toe. Houd het bij de bestuurlijke lagen die structureel onderbediend worden: gemeenten, waterschappen, provincies, gemeenschappelijke regelingen.

### Geen webinterface of cloudopslag

De toolkit draait bewust lokaal, op de eigen machine van de journalist. Dat is geen technische beperking maar een principiële keuze: documenten blijven privé, er gaat geen data naar externe servers, er zijn geen accounts of wachtwoorden, en de journalist heeft volledige controle. Zodra je een webserver, hosting of gebruikersaccounts nodig hebt, bouw je een softwareproduct met bijbehorende verantwoordelijkheden — dat is een ander project.

### Automatiseer de signalering, niet de conclusie

De toolkit mag een journalist sneller bij de juiste vraag brengen. Wat het niet mag doen, is de vraag zelf beantwoorden. Alerts, fragmenten, tijdlijnen en checklists zijn hulpmiddelen voor de journalist — die beoordeelt zelf wat een signaal waard is, welke bronnen hij raadpleegt en of er een verhaal is. De redactionele verantwoordelijkheid blijft altijd bij de mens.

