# Design Brief — Lokaalbestuur Toolkit Webinterface

## 1. Wat dit is

Een lokale webapplicatie voor een journalist die structureel vergaderstukken
van Nederlandse gemeenten, waterschappen, veiligheidsregio's,
gemeenschappelijke regelingen en provincies monitort. De toolkit bestaat
vandaag als een verzameling Python-scripts. Dit is de GUI-laag die alle
functies ontsluit zonder dat de gebruiker een terminal hoeft te openen.

**Stack:** Python backend (Flask of FastAPI) + moderne HTML/CSS/JS frontend.
Draait lokaal via `python3 toolkit.py serve`, opent op `http://localhost:8080`.
Geen cloud, geen login, geen externe afhankelijkheden.

**AI is geen vereiste.** De GUI is een volledig zelfstandige tool. Scrapen,
zoeken, alerts en rapporten werken zonder Claude, Gemini of een andere
AI-dienst. AI is een optionele losse stap ná de toolkit, voor wie dieper
onderzoek wil doen.

---

## 2. Gebruikerspersona

**Erwin, onderzoeksjournalist**

- Werkt aan één of meerdere verhalen tegelijk, elk over een ander thema
  (woningbouw, zorg, grondschandalen, milieu)
- Volgt tientallen bestuursorganen: gemeenten, hun GRs, waterschappen,
  veiligheidsregio's, provincies
- Zijn workflow: *gemeente kiezen → scrapen → zoeken → alert → rapport*
- Werkt in sessies: opent de tool, start een onderzoek, sluit de tool
- Heeft geen terminalervaring nodig — maar is niet bang voor details
- Wil weten wat er nieuw is zodra hij opstart

**Wat hij van de tool vraagt:**
1. Laat me snel zien wat er nieuw is (alerts, nieuwe documenten)
2. Laat me een gemeente of orgaan kiezen en alle bijbehorende stukken ophalen
3. Laat me zoeken, gericht en breed
4. Stuur me een melding als er iets relevants binnenkomt

---

## 3. Kernworkflow (chronologisch)

```
[Opstarten]
  → Dashboard toont: alerts, recente scraper-runs, actieve dossiers

[Nieuw verhaal starten]
  → Verkennen: gemeente invullen
  → Systeem toont: provincie, veiligheidsregio, waterschap(pen), GRs
  → Journalist kiest welke bronnen hij wil downloaden
  → Kies terugkijkperiode (6 / 12 / 18 / 24 maanden)
  → Scraper draait, voortgang zichtbaar in UI
  → Na afloop: vraag of nieuwe documenten doorzoekbaar gemaakt worden

[Onderzoeken]
  → Zoekinterface: gemeente kiezen, zoekterm invullen
  → Resultaten: per vergadering, per document, snippet met markering
  → Document openen vanuit zoekresultaten

[Monitoren]
  → Dossier aanmaken: naam + trefwoorden + orgaan
  → Systeem scrapet automatisch (cron) en analyseert nieuwe PDF's
  → Alert binnenkomt → journalist klikt → rapport opent

[Rapport]
  → Alert-rapport in Markdown weergeven
  → Kopieer-knop voor gebruik in Claude Code-sessie
```

---

## 4. Schermkaart

```
┌─────────────────────────────────────────────────────────────┐
│  NAVIGATIE (sidebar of topbar)                              │
│  Dashboard · Verkennen · Scrapen · Zoeken · Dossiers · Alerts │
└─────────────────────────────────────────────────────────────┘

[1] DASHBOARD          — startpagina; alerts + status
[2] VERKENNEN          — gemeente opzoeken, ecosysteem in kaart
[3] SCRAPEN            — bronnen downloaden, voortgang zien
    [3a] Gemeente
    [3b] Gemeenschappelijke regelingen
    [3c] Waterschappen
    [3d] Veiligheidsregio's
    [3e] Provincies
[4] ZOEKEN             — full-text zoek in gedownloade documenten
[5] DOSSIERS           — monitoringsdossiers beheren
    [5a] Overzicht
    [5b] Nieuw dossier
    [5c] Dossier bewerken
[6] ALERTS             — inkomende alertrapporten bekijken
[7] INSTELLINGEN       — data-map, cron-configuratie, installatie-check
```

---

## 5. Schermspecificaties

### [1] Dashboard

**Doel:** Direct zien wat er nieuw is en waar je gebleven bent.

**Primaire zone — Alerts (bovenaan)**
- Lijst van recente alert-rapporten, gesorteerd op datum
- Per alert: dossier-label, orgaan, datum, aantal hits ("3 documenten gevonden")
- Klikbaar → opent Alert-scherm
- Badge (rode cirkel) op het tabblad Alerts als er ongelezen alerts zijn

**Secundaire zone — Actieve dossiers**
- Per dossier: naam, orgaan, trefwoorden (max 3 zichtbaar), laatste run
- Knop "Nu draaien" per dossier → start analyse direct

**Tertiaire zone — Bronnen-status**
- Compacte tegel per brontype:
  - Gemeenten: n geconfigureerd, n gedownload
  - GRs: n actief
  - Waterschappen: n geconfigureerd, n gedownload
  - Veiligheidsregio's: n gedownload
  - Provincies: n gedownload
- Klik op tegel → gaat naar Scrapen-scherm voor dat type

**Lege staat:**
- Eerste gebruik: grote "Start hier" call-to-action met stap 1 (Verkennen)

---

### [2] Verkennen

**Doel:** Journalist voert een gemeente in en krijgt direct het bestuursecosysteem terug.

**Input:** Groot zoekveld bovenaan — "Zoek een gemeente…"
- Autocomplete op basis van gemeenten_overheid.json (355 gemeenten)
- Enter of klik op "Verkennen"

**Resultaat-kaart (na zoeken):**
```
┌──────────────────────────────────────────────────┐
│  ARNHEM — Vooronderzoek                          │
│                                                  │
│  Provincie         Gelderland                    │
│  Veiligheidsregio  Gelderland-Midden             │
│  Waterschap        Waterschap Rivierenland        │
│                                                  │
│  Gemeenschappelijke regelingen (12)              │
│  ☐ Dar NV                                        │
│  ☐ GGD Gelderland-Midden                         │
│  ☐ Omgevingsdienst Regio Arnhem                  │
│  ☐ Presikhaaf bedrijven                          │
│  ☐ …                                             │
│                                                  │
│  [✓ Alles selecteren]                            │
│                                                  │
│  [ Raadsstukken downloaden (altijd) ]            │
│  [ + Geselecteerde bronnen toevoegen ]           │
└──────────────────────────────────────────────────┘
```

**Gedrag:**
- Veiligheidsregio, waterschap en provincie zijn direct klikbaar naar hun Scrapen-pagina
- GRs zijn aanvinkvakjes — journalist kiest welke hij wil downloaden
- Knop "Raadsstukken downloaden" navigeert naar Scrapen [3a] en start de download
- Knop "+ Geselecteerde bronnen toevoegen" start GR-scrapers voor de aangevinkte GRs
- Na klikken: navigeer naar Scrapen-scherm met live voortgang

**Edge cases:**
- Gemeente niet gevonden in mapping → foutmelding + handmatig invoerpad
- API niet bereikbaar → "Kan GRs niet ophalen — check je verbinding"

---

### [3] Scrapen

**Doel:** Vergaderstukken downloaden van een orgaan.

**Tabstructuur boven het scherm:**
`Gemeenten · GRs · Waterschappen · Veiligheidsregio's · Provincies`

**Per tab:**

**[3a] Gemeenten**
- Dropdown: kies gemeente uit geconfigureerde organen
- Terugkijkperiode (zie §5.1 hieronder)
- Droog-modus toggle: "Eerst simuleren (droog uitvoeren)"
- Knop "Start download"

**[3b–3e] Andere organen**
- Lijst van geconfigureerde organen (uit bronnen/*.json)
- Per orgaan: naam, aantal gedownloade documenten, datum laatste run, knop "Downloaden"
- "Alles downloaden"-knop bovenaan voor batch

---

#### §5.1 Terugkijkperiode-selector

Van toepassing bij: eerste download van een gemeente, GR of waterschap,
én bij handmatige scraper-runs.

```
Hoe ver wil je terugkijken?

  ○  6 maanden
  ○  12 maanden
  ○  18 maanden
  ●  24 maanden  (aanbevolen)
  ○  Vanaf datum: [____-__-__]
```

- Standaard geselecteerd: 24 maanden
- Opties komen overeen met `--jaren` vlag in de scrapers (6 mnd = 0.5j, etc.)
- Bij vervolgdownloads (orgaan al eerder gescraped): periode-selector tonen
  maar met een toelichting "Alleen nieuwe documenten worden gedownload"

---

#### §5.2 Voortgangs-UI (tijdens download)

```
┌─────────────────────────────────────────────────────┐
│  Arnhem downloaden                     [Annuleren]  │
│                                                     │
│  ████████████░░░░░░░░░  67%  (340 / 507 docs)       │
│                                                     │
│  ✓ Gemeenteraad 2024-11-14 — 12 docs                │
│  ✓ Commissie Wonen 2024-11-07 — 8 docs              │
│  ⟳ Gemeenteraad 2024-10-31 — bezig…                │
│                                                     │
│  Fouten: 0                                          │
└─────────────────────────────────────────────────────┘
```

- Streamt via Server-Sent Events (SSE) op `/api/scraper/status`
- Na voltooiing: samenvatting + doorzoekbaar-maken-dialoog (zie §5.3)

---

#### §5.3 Doorzoekbaar-maken-dialoog (na voltooiing)

Verschijnt alleen als er >0 nieuwe documenten zijn gedownload.
Wordt niet getoond bij een droge run.

```
✓ Download voltooid — 312 nieuwe documenten

┌─────────────────────────────────────────────────────┐
│  Wil je de nieuwe documenten doorzoekbaar maken?    │
│                                                     │
│  Geschatte tijd: ~15 minuten                        │
│                                                     │
│  [ Ja, maak doorzoekbaar ]      [ Later ]           │
└─────────────────────────────────────────────────────┘
```

- "Ja" → start index.py, toont een tweede voortgangsindicator
- "Later" → sluit dialoog; een "Maak doorzoekbaar"-knop verschijnt op het
  Dashboard zolang er niet-geïndexeerde documenten zijn
- Tijdschatting: ~3 seconden per document (afgerond op minuten)

---

### [4] Zoeken

**Doel:** Full-text zoeken in alle gedownloade documenten.

**Layout:**
```
┌────────────────────────────────────────────────────────┐
│  Orgaan: [Arnhem ▾]   Zoek: [woningbouw grond    ] [↵]│
└────────────────────────────────────────────────────────┘

  47 resultaten voor "woningbouw grond"

  ─────────────────────────────────────────────────────
  2024
    2024-11-14 · Gemeenteraad
    raadsvoorstel-vaststelling-bestemmingsplan.pdf
    > …de **woningbouw** op de voormalige **grond**…

    2024-10-31 · Commissie Wonen
    nota-grondbeleid-actualisatie.pdf
    > …**grondprijs** voor sociale **woningbouw** …
```

**Zoeksyntaxis-hulp (klein tooltip-icoon):**
- `woord1 woord2` — beide woorden
- `woord1 OR woord2` — een van beide
- `"exacte zin"` — woordcombinatie
- `woord1 NOT woord2`

**Per resultaat:**
- Datum, vergadertype, bestandsnaam
- Snippet met gemarkeerde trefwoorden
- Klik op resultaat → document opent in systeem-PDF-viewer

**Orgaan-selector:**
- Alle geconfigureerde gemeenten + regelingen + waterschappen +
  veiligheidsregio's + **provincies** (na bugfix index.py)
- Groepering per type in de dropdown

**Edge cases:**
- Geen index.db aanwezig → "Index nog niet gebouwd — eerst scrapen en doorzoekbaar maken"
- Ongeldige FTS5-syntaxis → vriendelijke foutmelding
- Geen resultaten → suggestie om synoniemen of bredere term te proberen

---

### [5] Dossiers

**[5a] Overzicht**

| Naam | Orgaan | Trefwoorden | Laatste run | Status | Acties |
|------|--------|-------------|-------------|--------|--------|
| woningbouw | arnhem | woningbouw, grond… | 21 mei, 09:30 | ✓ Actief | Bewerken · Nu draaien |
| asielopvang | rotterdam | asielzoeker, azc… | Nooit | ○ Wacht | Bewerken · Nu draaien |

- "Nieuw dossier"-knop rechtsboven

**[5b] Nieuw dossier (formulier)**
```
Naam             [woningbouw            ]
Label            [Woningbouw & grond    ]
Orgaan           [Arnhem           ▾    ]
Trefwoorden      [woningbouw            ] [+ toevoegen]
                 [grondbeleid           ] [×]
                 [bestemmingsplan       ] [×]
                 [bouwvergunning        ] [×]

Automatisch draaien:  ☑ Wekelijks (woensdag 09:30)
macOS-melding:        ☑ Aan

[ Opslaan ]  [ Annuleren ]
```

**[5c] Dossier bewerken**
- Zelfde formulier, ingevuld
- "Nu draaien"-knop bovenaan
- "Verwijder dossier"-knop (bevestigingsdialoog)

---

### [6] Alerts

**Doel:** Inkomende alertrapporten bekijken en beoordelen.

**Lijst-view:**
```
┌──────────────────────────────────────────────────────────┐
│  ● NIEUW  woningbouw · Arnhem · 21 mei 2026             │
│  3 documenten gevonden                                   │
│                                                          │
│  ○ asielopvang · Rotterdam · 14 mei 2026                 │
│  1 document gevonden                                     │
└──────────────────────────────────────────────────────────┘
```

**Detail-view (na klikken):**
- Markdown-rapport gerenderd in de UI
- Trefwoorden gemarkeerd
- Per document: bestandsnaam, klikbaar pad, snippet
- Knop "Kopieer briefing voor Claude Code" → kopieert rapport als platte tekst
- Knop "Maak Woo-verzoek" → opent woo-verzoek prompt (pre-filled met dossierinfo)

---

### [7] Instellingen

**Secties:**

**Data-map**
- Huidige locatie tonen (`~/Documents/notulen/`)
- Knop "Wijzigen" → tekstinvoer met bestandskiezer

**Installatie-check**
- Python-versie ✓
- pdfplumber geïnstalleerd ✓
- Schrijfrechten data-map ✓
- ORI API bereikbaar ✓
- Notubiz API bereikbaar ✓

**Cron-taken**
- Overzicht van actieve crontabregels
- Per taak: beschrijving, schema, laatste run

**Notubiz-catalogus**
- Datum laatste update
- Knop "Ververs nu"

---

## 6. Technische architectuur

### Backend (Python)

**Framework:** Flask (voorkeur) of FastAPI
**Entrypoint:** `python3 toolkit.py serve` of apart `server.py`

**REST API-endpoints:**

```
GET  /api/status                → dashboard-data: alerts, dossiers, bronnen-status
GET  /api/gemeenten             → lijst van beschikbare gemeenten (ORI-indices)
GET  /api/organen               → geconfigureerde organen uit organen/*.json
GET  /api/dossiers              → alle dossiers
POST /api/dossiers              → nieuw dossier aanmaken
PUT  /api/dossiers/:naam        → dossier bijwerken
DEL  /api/dossiers/:naam        → dossier verwijderen

GET  /api/verkennen/:gemeente   → provincie, VR, waterschap, GRs
POST /api/scrapen/gemeente      → start gemeente-scraper
POST /api/scrapen/gr            → start GR-scraper
POST /api/scrapen/waterschap    → start waterschap-scraper
POST /api/scrapen/vr            → start VR-scraper
POST /api/scrapen/provincie     → start provincie-scraper
GET  /api/scrapen/status        → SSE-stream van scraper-output

POST /api/index/bijwerken       → bouw/update zoekindex voor een orgaan
GET  /api/zoeken                → ?orgaan=&q= → zoekresultaten

GET  /api/alerts                → alle alertrapporten (meta)
GET  /api/alerts/:id            → alert-rapport (Markdown-inhoud)
POST /api/analyse/draaien       → start analyse.py voor een dossier
```

### Datamodel (wat de backend leest/schrijft)

```
~/Documents/notulen/
├── organen/                    ← orgaan-configs (JSON)
│   └── arnhem.json             {naam, type, bron, vergadertypen}
├── dossiers/                   ← dossier-configs (JSON)
│   └── woningbouw.json         {label, orgaan, trefwoorden}
├── arnhem/                     ← gemeente-archief
│   ├── gemeenteraad/
│   │   └── 2024-11-14/
│   │       └── raadsvoorstel-xxx.pdf
│   ├── index.db                ← SQLite FTS5-index
│   ├── regelingen.md           ← gedetecteerde GRs
│   ├── alerts/
│   │   └── alert-2026-05-21.md
│   └── logs/
│       ├── scraper.log
│       └── analyse-staat-woningbouw.json
├── regelingen/<slug>/          ← GR-archieven
├── waterschappen/<slug>/       ← waterschap-archieven
├── veiligheidsregios/<slug>/   ← VR-archieven
└── provincies/<slug>/          ← provincie-archieven

bronnen/ (in toolkit-map)
├── regelingen.json             {slug: {naam, notubiz_id?, ibabs_naam?, deelnemers}}
├── waterschappen.json          {slug: {naam, ori_index, vergadertypen}}
├── veiligheidsregios.json      {slug: {naam, bron, org_id?}}
└── provincies.json             {slug: {naam, ori_index?, notubiz_id?}}
```

### Frontend

**Aanpak:** Jinja2 templates + HTMX of lichte vanilla JS.
Geen build-stap nodig, werkt offline, past bij de Python-stack.

**Real-time scraper-voortgang:** Server-Sent Events (SSE) op
`/api/scrapen/status` — streamt log-regels van de lopende scraper.

---

## 7. Visuele richting

**Toon:** Journalistiek, zakelijk, informatiedicht. Geen speelse kleuren of
decoratieve illustraties. Denk FT, NRC digitaal, Bellingcat-tools.

**Kleurenschema:**
- Basis: donker (near-black achtergrond), lichte tekst
- Accent: één warme kleur (amber of blauw-grijs) voor calls-to-action
- Alerts: rood/oranje voor ongelezen, grijs voor gelezen
- Voortgang: groene progress bar

**Typografie:**
- Brood: Inter of System UI
- Code/bestandsnamen: JetBrains Mono of Fira Code
- Kopgrootte: compact — dit is een werktool, geen homepage

**Componenten die terugkomen:**
- Status-badge (nieuw / actief / fout / wacht)
- Voortgangsbalk voor scraper-runs
- Doorzoekbaar-maken-dialoog (na elke geslaagde download)
- Inline terminal-output (monospace, scrollbaar) tijdens scraper-runs
- Toast-notificaties voor voltooide acties

**Schermformaat:** desktop-only (min. 1280px breed).

---

## 8. Kritieke gedragsregels

1. **Scraper-output streamt** — gebruiker ziet live wat er gedownload wordt.

2. **Doorzoekbaar-maken is een expliciete stap** — na elke succesvolle
   download verschijnt de dialoog (§5.3). Nooit stilzwijgend indexeren.
   Nooit de vraag tonen bij een droge run of bij 0 nieuwe documenten.

3. **Terugkijkperiode altijd zichtbaar** — de gebruiker weet altijd hoe ver
   terug hij kijkt. Standaard 24 maanden, altijd aanpasbaar.

4. **Geen data-verlies** — "Verwijder dossier" heeft altijd een bevestiging.
   Scraper overschrijft nooit bestaande bestanden.

5. **Foutmeldingen zijn concreet** — niet "Er is een fout opgetreden" maar
   "Gemeente 'veere' niet gevonden in de ORI API."

6. **Orgaan-configs in de juiste map** — de backend schrijft altijd naar
   `~/Documents/notulen/organen/`, nooit naar de projectmap.

7. **Provincies doorzoekbaar** — na bugfix index.py zijn provincies ook
   opvraagbaar via de zoekindex. De orgaan-selector in het Zoekscherm
   toont ze altijd.

---

## 9. Buiten scope

- Gebruikersbeheer / login
- Cloud-sync of remote API
- Mobile responsiveness
- In-browser PDF-viewer (nice to have, niet vereist)
- AI-analyse direct in de UI
- Versiegeschiedenis van dossiers

---

## 10. Bouwvolgorde (aanbevolen)

```
Sprint 1: Flask-backend + Dashboard (status-endpoints)
Sprint 2: Verkennen (gemeente-lookup + GR-kaart)
Sprint 3: Scrapen + SSE-voortgang + doorzoekbaar-maken-dialoog
Sprint 4: Zoeken (index.py koppelen)
Sprint 5: Dossiers CRUD
Sprint 6: Alerts-overzicht + detail
Sprint 7: Instellingen + installatie-check
```
