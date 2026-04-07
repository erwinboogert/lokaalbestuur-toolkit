# Lokaalbestuur Toolkit

Een onderzoekstool voor journalisten die openbare bestuursdocumenten van Nederlandse gemeenten, waterschappen en samenwerkingsverbanden willen doorzoeken met behulp van AI. Werkt volledig lokaal — geen API-sleutel, geen account, geen data naar buiten.

---

## Waar het om gaat

Je downloadt vergaderstukken van een gemeente (of waterschap, of samenwerkingsverband), en kunt daar vervolgens open onderzoeksvragen over stellen aan Claude Code. Niet "zoek het woord woningbouw" maar "de gemeente investeert al jaren niet meer in sportaccommodaties — is er een verband met stijgende obesitas onder jongeren?"

Claude doorzoekt het archief, leest relevante stukken, en geeft je een beeld. Jij recherche verder.

---

## Primaire werkwijze — in drie stappen

### Stap 1 — Documenten downloaden

```bash
python3 scraper.py rotterdam
```

Documenten komen in `~/Documents/notulen/rotterdam/`. Eerste keer kan even duren — daarna haalt de scraper alleen nieuwe stukken op.

Wil je eerst zien wat er gedownload wordt zonder iets op te slaan:

```bash
python3 scraper.py rotterdam --droog
```

### Stap 2 — Onderzoeksomgeving klaarzetten

```bash
python3 toolkit.py onderzoek rotterdam
```

Dit commando:
- Controleert welke bronnen beschikbaar zijn (gemeente, plus GRs en waterschappen die je hebt toegevoegd)
- Bouwt een zoekindex zodat Claude niet elk PDF-bestand hoeft te openen
- Toont welke bronnen er zijn en welke nog gedownload kunnen worden
- Genereert een **contextbriefing** die je straks aan Claude geeft

Voorbeeld output:

```
Onderzoeksomgeving — Rotterdam
──────────────────────────────────────────────────

  Index bijwerken voor rotterdam…

  Beschikbare bronnen:

  ✓  Gemeente Rotterdam                        847 doc  index ✓
  ✓  GR Jeugdhulp Rijnmond                      23 doc
  ○  GR DCMR Milieudienst Rijnmond              → python3 scraper_gr.py dcmr-milieudienst-rijnmond-2015

  Open Claude Code in de documentenmap:

    claude ~/Documents/notulen/rotterdam

  Plak dit als context vóór je vraag aan Claude:
  ┌────────────────────────────────────────────────
  │ ## Onderzoekscontext — lokaalbestuur-toolkit
  │ ...
```

### Stap 3 — Vraag stellen aan Claude Code

```bash
claude ~/Documents/notulen/rotterdam
```

Plak de briefing die stap 2 heeft gegenereerd, en stel daarna je vraag. De briefing vertelt Claude:
- Welke bronnen beschikbaar zijn en hoe die doorzoekbaar zijn
- Welk type organisatie relevant is voor welk onderwerp (GGD → gezondheid, jeugdhulp → jongeren, waterschap → klimaat)
- Hoe hij de zoekindex gebruikt voor efficiency

Zie `prompts/vrije-vraag.md` voor uitleg over hoe je je vraag het best opbouwt.

---

## Meer bronnen toevoegen

De `onderzoek`-briefing wordt automatisch rijker als je meer bronnen hebt geconfigureerd. Gemeenschappelijke regelingen (GRs) en waterschappen bevatten vaak uitvoeringsinformatie die de gemeente zelf niet heeft.

### Een gemeente toevoegen (eenmalig)

```bash
python3 toolkit.py nieuw-orgaan
```

De wizard vraagt naar naam en type. Voor gemeenten zoekt de toolkit daarna automatisch welke GRs bij die gemeente horen en stelt die voor:

```
  12 gemeenschappelijke regelingen gevonden voor rotterdam:

    1.  Beschermd wonen regio Rotterdam
    2.  DCMR Milieudienst Rijnmond 2015
    3.  Jeugdhulp Rijnmond
    ...

  Welke wil je toevoegen aan de catalogus?
```

### Waterschappen downloaden

Alle 13 Nederlandse waterschappen die via de ORI API beschikbaar zijn staan vooraf geconfigureerd:

```bash
python3 scraper_waterschap.py hollandse-delta
python3 scraper_waterschap.py --lijst           # welke zijn er?
```

### GRs downloaden

GRs hebben geen centraal publicatiekanaal zoals gemeenten. Veel publiceren via Notubiz, soms achter login. De toolkit vraagt momenteel een API-sleutel aan bij Notubiz; zodra die beschikbaar is werkt de scraper. Tussentijds:

```bash
python3 toolkit.py nieuwe-regeling   # GR handmatig toevoegen aan de catalogus
```

GRs zijn wettelijk verplicht hun stukken openbaar te maken (Wgr art. 22, Woo). Als een GR niets publiceert, kun je een WOO-verzoek genereren via de `/wob-verzoek` skill in Claude Code.

---

## Optioneel: automatische monitoring

Als je een gemeente intensief volgt en wekelijks gesignaleerd wilt worden bij nieuwe relevante stukken, kun je een dossier aanmaken met trefwoorden:

```bash
python3 toolkit.py nieuw-dossier
```

Daarna draait de analyse automatisch elke week via crontab. Bij treffers verschijnt een macOS-melding en staat een alertrapport klaar in `~/Documents/notulen/<orgaan>/alerts/`.

Dit is aanvullend op de primaire werkwijze — je hebt het niet nodig voor een eerste onderzoek.

---


## Vereisten en installatie

**Vereisten:**
- Python 3.10 of hoger
- `pdfplumber` voor tekstextractie uit PDFs

```bash
pip install pdfplumber
```

**Installatiecheck:**

```bash
python3 toolkit.py check
```

Controleert Python-versie, bibliotheken, API-verbinding, dossiers en crontab.

---

## Alle commando's

```bash
# Primaire werkwijze
python3 scraper.py <gemeente>                   # download raadsstukken
python3 toolkit.py onderzoek <gemeente>         # bronnencheck + Claude-briefing genereren

# Organen en bronnen instellen
python3 toolkit.py nieuw-orgaan                 # gemeente, waterschap of GR toevoegen
python3 scraper_waterschap.py <waterschap>      # waterschapstukken downloaden
python3 scraper_gr.py <gr>                      # GR-stukken downloaden (vereist API-toegang)

# Monitoring
python3 toolkit.py nieuw-dossier                # nieuw dossier met trefwoorden
python3 analyse.py --dossier <naam>             # handmatig alert draaien

# Zoeken (direct, zonder Claude)
python3 index.py <gemeente> "zoekterm"          # zoek in de index

# Overzicht
python3 toolkit.py                              # dashboard
python3 toolkit.py status                       # uitgebreid statusoverzicht
python3 toolkit.py check                        # installatiecheck
```

---

## Analyseprompts

De map `prompts/` bevat sjablonen voor gebruik in Claude Code:

| Prompt | Wanneer |
|---|---|
| `vrije-vraag.md` | Brede onderzoeksvraag zonder vooraf bekende trefwoorden — **start hier** |
| `raadsstukken-analyse.md` | Gestructureerde analyse van een bekend dossier |
| `wederhoor.md` | Gerichte vragen per partij op basis van de stukken |
| `bronnenbrief.md` | Eerste contactbrief aan een bron of betrokkene |

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
├── scraper_gr.py           GR-stukken (vereist Notubiz API-sleutel)
├── analyse.py              keyword-alerts
├── index.py                zoekindex (SQLite FTS5)
├── bronnen/                catalogussen (gemeenten, waterschappen, GRs)
├── organen/                configuratie per orgaan
├── dossiers/               configuratie per monitoringsdossier
├── prompts/                Claude-prompts
└── checklists/             rode-vlagchecklist lokaal bestuur

~/Documents/notulen/
├── rotterdam/
│   ├── gemeenteraad/2026-01-27/*.pdf
│   ├── index.db
│   └── alerts/alert-2026-03-26.md
├── waterschappen/hollandse-delta/
└── regelingen/jeugdhulp-rijnmond/
```

---

## Databron

Raadsstukken komen van de [Open Raadsinformatie API](https://openraadsinformatie.nl), een initiatief van de Open State Foundation. Gebruik `python3 scraper.py` zonder argument voor de actuele lijst van beschikbare gemeenten.
