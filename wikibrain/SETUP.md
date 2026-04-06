---
title: WikiBrain — Installatie & Obsidian Setup
---

# WikiBrain — Installatie & Setup

## 1. Repository klonen

```bash
cd /Users/erwin/Documents/Wikibrain
git clone https://github.com/erwinboogert/Zoeken-in-de-bieb.git .
```

## 2. Python omgeving opzetten

```bash
python3 --version          # moet 3.10 of hoger zijn
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install -e .
```

Na installatie is het `wikibrain` commando beschikbaar in de terminal (zolang de venv actief is).

## 3. Bronmap vullen

Plaats je bronbestanden (PDF, Word, HTML, Markdown, afbeeldingen) in:

```
/Users/erwin/Documents/Wikibrain/sources/
```

Submappen zijn toegestaan — WikiBrain scant recursief.

## 4. Obsidian instellen

### Vault openen

1. Open Obsidian
2. Klik **Open folder as vault**
3. Kies: `/Users/erwin/Documents/Wikibrain`

Dit opent het hele project als vault. De wiki-artikelen staan in `wiki/concepts/` en `wiki/sources/`.

### Aanbevolen plugins

Ga naar **Settings → Community Plugins → Browse**:

| Plugin | Waarvoor |
|---|---|
| **Dataview** | Tabellen en lijsten op basis van frontmatter |
| **Marp Slides** | Presentaties bekijken vanuit `.marp.md` bestanden |

### Instellingen aanpassen

| Instelling | Waar | Waarde |
|---|---|---|
| Wikilinks | Settings → Files & Links → Use Wikilinks | **Aan** |
| Backlinks | Settings → Core Plugins → Backlinks | **Aan** |
| Startpagina | Community Plugin "Homepage" of handmatig | `wiki/_meta/INDEX` |

### Mappen die je kunt verbergen in Obsidian

Ga naar **Settings → Files & Links → Excluded files** en voeg toe:

```
.venv
.git
__pycache__
raw/sources
raw/attachments
raw/processed
```

Zo zie je in Obsidian alleen de relevante wiki-inhoud.

## 5. Eerste run

```bash
source .venv/bin/activate

# Bekijk wat er verwerkt zou worden (zonder iets te doen)
wikibrain ingest --dry-run

# Verwerk bronbestanden
wikibrain ingest

# Bouw wiki-artikelen
wikibrain compile
```

Open daarna Obsidian en navigeer naar `wiki/_meta/INDEX.md` om je eerste artikelen te zien.

## 6. Wekelijkse workflow

```
Nieuwe bestanden in sources/ plaatsen
       ↓
wikibrain ingest
       ↓
wikibrain compile
       ↓
Obsidian → INDEX.md → nieuwe artikelen lezen
       ↓
Optioneel: wikibrain query "Wat is er nieuw deze week?"
       ↓
Optioneel: wikibrain lint --report
```

## Mappenstructuur

```
/Users/erwin/Documents/Wikibrain/
├── sources/                ← jouw bronbestanden (PDF, Word, etc.)
├── raw/                    ← geconverteerde markdown + wachtrij
├── wiki/
│   ├── concepts/           ← wiki-artikelen per concept
│   ├── sources/            ← samenvattingen per bron
│   ├── _meta/
│   │   ├── INDEX.md        ← startpagina
│   │   ├── concepts.json   ← concept registry
│   │   └── search.db       ← zoekindex
│   └── outputs/            ← resultaten van queries
├── prompts/                ← Claude instructies (aanpasbaar)
├── wikibrain/              ← Python code
├── config.yaml             ← instellingen
└── requirements.txt
```
