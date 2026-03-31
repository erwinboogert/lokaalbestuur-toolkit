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
python3 index.py barendrecht                      # bouw/update index
python3 index.py barendrecht "grondprijs"         # zoek
python3 index.py barendrecht "grond OR woningbouw" --uitvoer  # exporteer naar Markdown
python3 index.py barendrecht --status             # statistieken
```

Resultaten bevatten: bestandsnaam, vergaderdatum, vergadertype, snippet met gemarkeerde treffers.

### ✅ Timeline-reconstructie per dossier
`tijdlijn.py` — zoekt alle treffers voor een term door het archief, sorteert chronologisch en exporteert als Markdown naar `~/Documents/notulen/<orgaan>/tijdlijnen/`.

```bash
python3 tijdlijn.py barendrecht "woningbouw"
python3 tijdlijn.py --dossier asielopvang "spreidingswet"
```

### ✅ Partijposities tracken
`partijen.py` — heuristische sprekerdetectie op basis van gangbare Nederlandse vergadernotatie. Koppelt fragmenten aan fracties, gegroepeerd per partij. Waarschuwt expliciet als geen sprekers worden herkend.

```bash
python3 partijen.py barendrecht "woningbouw"
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
- **Dossier kan meerdere organen volgen** — `"organen": ["barendrecht", "ridderkerk"]` in dossier-config; `analyse.py` itereert over meerdere documentenmappen en bundelt resultaten in één rapport. Bewust uitgesteld: vereist substantiële refactor van `analyse.py`.

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
├── bronnen/                ← nieuw: configuratie per brontype
│   ├── regelingen.json     ← actieve gemeenschappelijke regelingen
│   ├── waterschappen.json  ← actieve waterschappen
│   └── gemeenten_cbs.json  ← gemeenten voor financiële monitoring
```

Het dashboard (`python3 toolkit.py`) toont alle actieve bronnen in één overzicht:

```
── Actieve bronnen ───────────────────────────────
  Raadsstukken    12 gemeenten   laatste run: 2 dagen geleden
  Regelingen       3 actief      laatste run: 5 dagen geleden
  Waterschappen    1 actief      laatste run: nooit
  Financiën        4 gemeenten   laatste update: jan 2026
```

### Fase 6a — Gemeenschappelijke regelingen

Gemeenten voeren steeds meer taken niet zelf uit, maar via samenwerkingsverbanden met andere gemeenten. Denk aan sociale diensten, regionale omgevingsdiensten, veiligheidsregio's en jeugdhulpregio's. Deze zogeheten gemeenschappelijke regelingen hebben eigen besturen, eigen begrotingen en eigen vergaderingen — maar vallen buiten het zicht van de individuele gemeenteraad. Er is nauwelijks democratisch toezicht en journalistieke aandacht ontbreekt vrijwel volledig. Juist hier kunnen grote bedragen worden besteed en besluiten worden genomen zonder dat iemand goed oplet. Een deel van deze regelingen is al vindbaar via de Open Raadsinformatie API, maar ze zijn ondervertegenwoordigd.

**Nieuw bestand:** `scraper_gr.py` — werkt identiek aan `scraper.py`, maar filtert specifiek op samenwerkingsorganen in de ORI-API.

```bash
python3 scraper_gr.py veiligheidsregio-rotterdam  # download vergaderstukken
python3 scraper_gr.py --lijst                     # toon beschikbare regelingen
```

Output in: `~/Documents/notulen/regelingen/<naam>/`

**Toolkit-commando's:**
```bash
python3 toolkit.py nieuwe-regeling    # voeg een GR toe aan bronnen/regelingen.json
python3 toolkit.py scrape-regelingen  # download nieuwe stukken voor alle actieve regelingen
```

### Fase 6b — Waterschappen

Waterschappen zijn democratisch gekozen bestuursorganen die verantwoordelijk zijn voor waterveiligheid, dijkbeheer, rioolwaterzuivering en grondwaterpeil. Ze beheren samen miljarden aan publiek geld en vergaderen openbaar, maar worden in de lokale en regionale journalistiek vrijwel nooit bericht. Met de toenemende druk van klimaatverandering wordt hun werk steeds relevanter. De vergaderstukken zijn openbaar maar niet via één centrale API beschikbaar — dit vraagt een eigen scraper per waterschap, geconfigureerd via `bronnen/waterschappen.json`.

**Nieuw bestand:** `scraper_waterschap.py`

```bash
python3 scraper_waterschap.py hollandse-delta  # download vergaderstukken
python3 scraper_waterschap.py --lijst          # toon geconfigureerde waterschappen
```

Output in: `~/Documents/notulen/waterschappen/<naam>/`

**Configuratie in `bronnen/waterschappen.json`:**
```json
{
  "hollandse-delta": {
    "naam": "Waterschap Hollandse Delta",
    "systeem": "notubiz",
    "base_url": "..."
  }
}
```

**Toolkit-commando's:**
```bash
python3 toolkit.py nieuw-waterschap    # voeg een waterschap toe
python3 toolkit.py scrape-waterschappen
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

**Nieuw bestand:** `scraper_cbs.py` — haalt iv3-data op via de CBS StatLine API, slaat op als CSV per gemeente.

```bash
python3 scraper_cbs.py arnhem                              # haal iv3-data op
python3 scraper_cbs.py --vergelijk arnhem breda roosendaal # vergelijkingsrapport
```

Output in: `~/Documents/notulen/<gemeente>/financien/`
- `iv3_<jaar>.csv` — ruwe data
- `vergelijking_<datum>.md` — Markdown-rapport met opvallende afwijkingen

**Toolkit-commando's:**
```bash
python3 toolkit.py financien arnhem  # haal data op + toon samenvatting
python3 toolkit.py vergelijk arnhem  # vergelijk met vergelijkbare gemeenten
```

De financiële data is institutioneel (gemeente als geheel) en valt daarmee binnen de bestaande privacygrenzen van de toolkit.

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

---

## Fase 8 — Zoekarchitectuur (open beslissing)

*Toegevoegd maart 2026. Nog geen beslissing genomen.*

### Aanleiding

De toolkit bouwt een groeiend lokaal archief van raadsstukken — maandelijks aangevuld, mogelijk over meerdere gemeenten en jaren. De vraag is hoe dit archief het beste doorzoekbaar wordt gemaakt, gegeven dat het gebruik primair *ontdekkend* is: je weet niet altijd wat je zoekt.

### De drie opties

**FTS5 (full-text zoekindex, al gebouwd als `index.py`)**
Zoekt op exacte woorden en varianten. Snel en betrouwbaar. Werkt goed als je weet wat je zoekt — een naam, een term, een specifiek woord. Werkt slecht voor ontdekkend werken: je moet al een mentaal beeld hebben van welk woord in de tekst staat. "Grondtransactie" vindt je niet als de tekst "verkoop perceel" zegt.

**Semantic search (vector-database via Ollama)**
Zoekt op betekenis. Je kunt vragen stellen als "wat speelt er rond wonen?" en documenten vinden die het woord "woningbouw" nooit bevatten, maar wel gaan over huisvesting, starters, huurmarkt of bouwplannen. Krachtig voor ontdekkend werk, maar nog steeds query-gestuurd: je hebt een vraag nodig. Vereist meer infrastructuur (Ollama, embedding-model, vector-database).

**Periodieke digest (nog niet gebouwd)**
Claude leest automatisch alle nieuwe documenten van de week en schrijft op wat er opvalt — zonder dat de journalist een vraag stelt. Dit is de enige optie die écht toevallige ontdekkingen mogelijk maakt: je krijgt een signaal over iets waar je niet op zocht. Past het beste bij de werkwijze van een onderzoeksjournalist die "vist". Sluit aan bij het bestaande alertsysteem. Laagste complexiteit van de drie.

### Kernoverweging

Claude kan documenten niet allemaal tegelijk lezen: het contextvenster heeft een limiet. Bij een klein archief is dat geen probleem. Bij een archief van jaren en meerdere gemeenten — duizenden documenten — is *selectie* noodzakelijk. De vraag is welk mechanisme die selectie maakt, en of dat mechanisme blinde vlekken creëert.

FTS5 en semantic search selecteren op basis van een query. Wie niet weet wat er speelt, zoekt er ook niet op. De digest selecteert niet: alles nieuws wordt gelezen. Dat is het fundamentele verschil.

### Voorlopige conclusie

Voor ontdekkend journalistiek werk — vissen, patronen zien, onverwachte verbanden — is de **digest de meest waardevolle volgende stap**. Semantic search voegt waarde toe als het archief zo groot wordt dat zelfs de digest niet meer behapbaar is, of als je gericht wil zoeken met vage begrippen. Vector-database-infrastructuur is pas zinvol als de vorige twee stappen tekortschieten.

**Aanbevolen volgorde:**
1. Digest bouwen — Claude leest wekelijks alle nieuwe stukken, schrijft signalen op
2. FTS5 gebruiken voor precieze nazoekacties (al beschikbaar)
3. Semantic search overwegen als het archief substantieel groeit of multi-gemeente wordt
