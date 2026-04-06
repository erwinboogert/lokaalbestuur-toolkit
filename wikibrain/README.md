# WikiBrain

WikiBrain zet jouw bronnenmap om in een doorzoekbare, groeiende kennisbank — en toont die kennisbank in **Obsidian**.

**Obsidian is geen optie, maar het hart van dit systeem.** Alle output van WikiBrain is Markdown met Obsidian-syntax: wikilinks (`[[Concept]]`), frontmatter, backlinks, Dataview-tabellen en Mermaid-diagrammen. Zonder Obsidian heb je losse tekstbestanden; mét Obsidian heb je een kennisnetwerk.

---

## Gebruik als onderdeel van de Lokaalbestuur Toolkit

WikiBrain is geïntegreerd in de [Lokaalbestuur Toolkit](../README.md). Als je die toolkit gebruikt, hoef je WikiBrain niet apart te installeren en kun je de commando's via `toolkit.py` aanroepen:

```bash
python3 toolkit.py wikibrain-ingest     # verwerk nieuwe raadsstukken
python3 toolkit.py wikibrain-compile    # update kennisbank-artikelen
python3 toolkit.py wikibrain-query "jouw vraag"
```

Het dashboard (`python3 toolkit.py`) toont automatisch de WikiBrain-status.

Wil je WikiBrain los gebruiken — buiten de toolkit, voor andere bronnen of domeinen — volg dan de installatie-instructies hieronder.

---

## Wat je nodig hebt

| Vereiste | Waarvoor |
|---|---|
| **Obsidian** | Lezen, navigeren en doorzoeken van de wiki |
| **Python 3.10+** | Draaien van WikiBrain |
| **Claude Code** | LLM-calls voor samenvatten, discovery en schrijven |
| **Een bronmap** | PDFs, Word-docs, HTML — jouw ruwe materiaal |

---

## Hoe het werkt

```
Bronmap (PDFs, Word, HTML)
       ↓
   wikibrain ingest        ← converteert naar markdown, slaat alleen nieuwe/gewijzigde op
       ↓
   wikibrain compile       ← herkent concepten, schrijft wiki-artikelen
       ↓
   wiki/                   ← Obsidian-vault met artikelen, backlinks, zoekindex
       ↓
   wikibrain query         ← stel vragen, krijg antwoord als markdown/slides/diagram
       ↓
   wikibrain lint          ← bewaakt kwaliteit, signaleert duplicaten en gaten
```

---

## Kernprincipes

- **Incremental first.** Elke run verwerkt alleen nieuwe of gewijzigde bestanden.
- **Search vóór LLM.** De zoekindex filtert; Claude leest alleen wat relevant is.
- **Één canon per concept.** Een centrale registry voorkomt losse duplicaatartikelen.
- **Obsidian doet backlinks.** WikiBrain schrijft forward links; Obsidian toont incoming links automatisch.
- **Fouten stoppen niet de hele run.** Mislukte conversies worden gelogd en overgeslagen.
- **Pre-filter vóór LLM.** Keyword-matching gaat eerst; Claude wordt alleen ingeschakeld bij twijfel.

---

## Fase 0: Omgeving opzetten

### Stap 1 — Obsidian installeren en vault aanmaken

[Download Obsidian](https://obsidian.md) als je het nog niet hebt.

Open Obsidian → "Open folder as vault" → kies de **`wiki/`** map van dit project.

Stel daarna de volgende plugins en instellingen in:

| Instelling | Waar |
|---|---|
| Use Wikilinks aan | Settings → Files & Links |
| Backlinks aan | Settings → Core Plugins |
| Startpagina → `_meta/INDEX.md` | Settings → Core Plugins → Page Preview |
| **Dataview** installeren | Settings → Community Plugins |
| **Marp** installeren (voor slides) | Settings → Community Plugins |

> Obsidian rendert Mermaid-diagrammen native — daar is geen plugin voor nodig.

### Stap 2 — Python-omgeving opzetten

```bash
python3 --version          # moet 3.10 of hoger zijn
cd /pad/naar/wikibrain
python3 -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
pip install -e .
```

### Stap 3 — Config aanmaken

```bash
cp config.yaml.voorbeeld config.yaml
```

Open `config.yaml` en stel in:

```yaml
paths:
  sources: "/absoluut/pad/naar/jouw/bronmap"
```

De rest van de config kun je naar behoefte aanpassen.

---

## Fase 1: Ingest

**Doel:** Bronbestanden omzetten naar schone markdown. Ongewijzigde bestanden worden overgeslagen.

### Conversiestrategie

WikiBrain probeert drie converters in volgorde:

1. **MarkItDown** (primair) — snel, breed inzetbaar
2. **PyMuPDF4LLM** (fallback) — beter voor complexe PDFs
3. **Marker** (optioneel, zwaar) — zet `use_marker: true` in config als de eerste twee structureel tekortschieten

Mislukte conversies worden gelogd in `raw/errors.log` en overgeslagen.

### Commando's

```bash
wikibrain ingest                    # alleen nieuwe/gewijzigde bestanden
wikibrain ingest --dry-run          # toon wat verwerkt zou worden
wikibrain ingest --force            # alles opnieuw verwerken
```

### Na ingest

Bekijk een paar bestanden in `raw/sources/` — in Obsidian of in de terminal. Controleer `raw/errors.log` op mislukte conversies.

---

## Fase 2: Compile

**Doel:** Wiki-artikelen bouwen op basis van de geconverteerde bronnen.

### Hoe compile werkt

1. Leest de wachtrij (`raw/queue.json`)
2. Controleert aliasconflicten in de concept registry
3. Koppelt elke bron aan bestaande concepten via keyword-matching; twijfelgevallen gaan naar Claude
4. Schrijft of updatet wiki-artikelen in `wiki/concepts/`
5. Schrijft een bronpagina per bron in `wiki/sources/`
6. Werkt `wiki/_meta/INDEX.md` bij — het startpunt in Obsidian
7. Werkt de zoekindex bij (`search.db`)

De artikelen worden geschreven in Obsidian-Markdown:

```markdown
---
title: Participatieverordening
aliases: [inspraakverordening]
tags: [regelgeving, lokaal-bestuur]
sources:
  - raw/sources/participatieverordening-rotterdam.md
source_count: 3
last_updated: 2026-04-06
---

# Participatieverordening

...

## Zie ook
- [[Gemeenteraad]]
- [[Inspraak]]
```

### Waarschuwing bij grote runs

Bij 25 of meer bronnen in de wachtrij vraagt WikiBrain om bevestiging. Elke bron kost meerdere Claude-calls. Werk bij grote collecties in batches:

```bash
wikibrain compile --limit 50       # verwerk maximaal 50 bronnen
```

### Commando's

```bash
wikibrain compile                                    # verwerk wachtrij
wikibrain compile --dry-run                          # toon wat er zou veranderen
wikibrain compile --limit 50                         # maximaal 50 bronnen
wikibrain compile --force-concept "Participatieverordening"  # hercompileer één artikel
wikibrain compile --all                              # hercompileer volledige wiki
```

### Na compile — bekijken in Obsidian

Open `wiki/_meta/INDEX.md` in Obsidian. Elk nieuw artikel staat hier als wikilink. Klik door naar een artikel en gebruik het **Backlinks-paneel** (rechtsonder) om te zien welke bronnen eraan gekoppeld zijn.

---

## Fase 3: Q&A & Output

**Doel:** Vragen stellen aan de wiki. WikiBrain zoekt eerst in de index, dan leest Claude gericht.

### Commando's

```bash
wikibrain query "Welke verordeningen zijn er herzien?"
wikibrain query "Overzicht alle organisaties" --output table
wikibrain query "Tijdlijn van besluiten" --output mermaid
wikibrain query "Vergelijk twee dossiers" --output slides
```

### Outputformaten

| Formaat | Bestandstype | Bekijken in |
|---|---|---|
| `markdown` | `.md` | Obsidian |
| `slides` | `.marp.md` | Obsidian + Marp plugin |
| `table` | `.md` met Dataview-syntax | Obsidian + Dataview plugin |
| `mermaid` | `.md` met Mermaid-blok | Obsidian (native, geen plugin) |
| `image` | `.png` via matplotlib | Obsidian of Finder |

Output wordt opgeslagen in `wiki/outputs/` met timestamp — zichtbaar in Obsidian.

---

## Fase 4: Search

```bash
wikibrain search "jeugdhulp"
wikibrain search "wethouder stolk" --top 10
wikibrain search "verordening" --type concept
```

De zoekindex (`search.db`) is gebouwd tijdens compile en groeit incrementeel mee.

---

## Fase 5: Lint

**Doel:** Kwaliteit bewaken naarmate de wiki groeit. Aanbevolen wekelijks na compile.

```bash
wikibrain lint                    # alle checks
wikibrain lint --report           # schrijf rapport naar wiki/_meta/health_report.md
wikibrain lint --fix              # Claude stelt fixes voor
```

Het rapport verschijnt als `health_report.md` in Obsidian.

---

## Wekelijkse workflow

**Via de Lokaalbestuur Toolkit:**
```
python3 toolkit.py wikibrain-ingest
python3 toolkit.py wikibrain-compile
python3 toolkit.py wikibrain-query "Wat is er nieuw deze week?"
```

**Direct via WikiBrain CLI:**
```
Nieuwe bestanden in bronmap
       ↓
wikibrain ingest
       ↓
wikibrain compile --limit 50      (of meer als je bundel het toelaat)
       ↓
Obsidian → INDEX.md → nieuwe artikelen bekijken
       ↓
wikibrain query "Wat is er nieuw deze week?"
       ↓
wikibrain lint --report
```

---

## Mappenstructuur

```
project/
├── wikibrain/          ← Python package (code)
├── prompts/            ← system prompts als .txt (aanpasbaar)
├── raw/
│   ├── sources/        ← geconverteerde markdown per bronbestand
│   ├── attachments/    ← afbeeldingen uit bronnen
│   ├── processed/      ← gearchiveerde bronnen na compile
│   ├── index.json      ← manifest met hashes en status
│   ├── queue.json      ← wachtrij voor compile
│   └── errors.log      ← mislukte conversies
├── wiki/               ← Obsidian-vault
│   ├── concepts/       ← één artikel per concept
│   ├── sources/        ← één pagina per bronbestand
│   ├── outputs/        ← query-resultaten met timestamp
│   └── _meta/
│       ├── INDEX.md        ← startpagina in Obsidian
│       ├── concepts.json   ← concept registry
│       ├── search.db       ← zoekindex
│       └── health_report.md
├── config.yaml         ← jouw instellingen (niet in git)
├── config.yaml.voorbeeld
├── requirements.txt
└── setup.py
```

---

## Hoe je een sessie hervat

**Via de toolkit:**
> "We werken aan de Lokaalbestuur Toolkit. Geef me een statusoverzicht."

**Standalone:**
> "We werken aan WikiBrain in [pad]. Geef me een statusoverzicht op basis van raw/index.json en wiki/_meta/INDEX.md."
