# Organen-catalogus

Deze map bevat configuratiebestanden per orgaan. Elk bestand beschrijft één orgaan: een gemeente, waterschap, provincie of gemeenschappelijke regeling (GR).

## Structuur van een orgaan-config

```json
{
  "naam": "Rotterdam",
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
| `type` | `gemeente`, `waterschap`, `gr`, `provincie` | Type orgaan |
| `bron` | `ori`, `ibabs`, `notubiz` | Databron — wordt automatisch bepaald op basis van de configuratie in `bronnen/` |
| `vergadertypen` | lijst van strings | Welke vergadering-namen worden gescraped (hoofdletterongevoelig, gedeeltelijke match) |

## Naamgeving van bestanden

- Alleen kleine letters, cijfers en koppeltekens
- Gemeente: `rotterdam.json`, `den-haag.json`
- Waterschap: `hollandse-delta.json`, `rijnland.json`
- GR: `drechtsteden-gr.json`, `midden-holland-gr.json`
- Provincie: `zuid-holland.json`, `gelderland.json`

Beschikbare indices: `python3 scraper.py --lijst` (gemeenten), `python3 scraper_waterschap.py --lijst` (waterschappen), `python3 scraper_gr.py --lijst` (GRs), `python3 scraper_provincie.py --lijst` (provincies)

## Standaard vergadertypen per type

**Gemeente**
```json
["gemeenteraad", "commissie", "raadsbrede commissie"]
```

**Waterschap**
```json
["algemeen bestuur", "college van dijkgraaf en heemraden", "dagelijks bestuur", "verenigde vergadering"]
```

**Gemeenschappelijke regeling**
```json
["algemeen bestuur", "dagelijks bestuur", "portefeuillehoudersoverleg"]
```

**Provincie**
```json
["provinciale staten", "gedeputeerde staten", "statencommissie", "commissie"]
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
