# Organen-catalogus

Deze map bevat configuratiebestanden per orgaan. Elk bestand beschrijft één orgaan: een gemeente, waterschap of gemeenschappelijke regeling (GR).

## Structuur van een orgaan-config

```json
{
  "naam": "Barendrecht",
  "type": "gemeente",
  "bron": "ori",
  "vergadertypen": [
    "gemeenteraad",
    "commissie",
    "raadsbrede commissie"
  ]
}
```

| Veld | Waarden | Toelichting |
|---|---|---|
| `naam` | vrije tekst | Volledige naam voor weergave |
| `type` | `gemeente`, `waterschap`, `gr` | Type orgaan |
| `bron` | `ori` | Databron (nu alleen ORI; uitbreidbaar) |
| `vergadertypen` | lijst van strings | Welke vergadering-namen worden gescraped (hoofdletterongevoelig, gedeeltelijke match) |

## Naamgeving van bestanden

- Gebruik de naam zoals die voorkomt in de Open Raadsinformatie API-index
- Alleen kleine letters, cijfers en koppeltekens
- Gemeente: `barendrecht.json`, `den-haag.json`
- Waterschap: `hollandse-delta.json`, `rijnland.json`
- GR: `drechtsteden-gr.json`, `midden-holland-gr.json`

Controleer de beschikbare indices via: `python3 scraper.py` (toont alle beschikbare organen)

## Standaard vergadertypen per type

**Gemeente**
```json
["gemeenteraad", "commissie", "raadsbrede commissie"]
```

**Waterschap**
```json
["algemeen bestuur", "college van dijkgraaf en heemraden"]
```

**Gemeenschappelijke regeling**
```json
["algemeen bestuur", "dagelijks bestuur", "portefeuillehoudersoverleg"]
```

## Nieuw orgaan toevoegen

Via de wizard:
```bash
python3 toolkit.py nieuw-orgaan
```

Of handmatig: maak een `.json`-bestand aan volgens bovenstaande structuur en voeg het toe aan deze map.

## Bijdragen

Heb je een orgaan-config aangemaakt die voor anderen nuttig kan zijn? Pull requests zijn welkom.
Houd de naamgeving consistent en test dat de scraper de vergadertypen correct vindt voordat je een PR opent.
