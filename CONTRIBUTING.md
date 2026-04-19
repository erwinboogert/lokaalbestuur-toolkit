# Bijdragen aan de Lokaalbestuur Toolkit

Bijdragen zijn welkom, in het bijzonder orgaan-configs voor gemeenten, waterschappen, provincies en gemeenschappelijke regelingen die nog niet in de map staan.

---

## Orgaan-config toevoegen

De snelste en meest waardevolle bijdrage is een configuratiebestand voor een orgaan dat je zelf gebruikt of dat voor anderen nuttig is.

**Stap 1 — Maak het bestand aan**

Maak een bestand aan in `organen/` met de naam van het orgaan in kleine letters en koppeltekens:

```
organen/arnhem.json
organen/hollandse-delta.json
organen/drechtsteden-gr.json
```

**Stap 2 — Gebruik dit formaat**

```json
{
  "naam": "Volledige naam",
  "type": "gemeente",
  "bron": "ori",
  "vergadertypen": [
    "gemeenteraad",
    "commissie"
  ]
}
```

| Veld | Toegestane waarden |
|---|---|
| `type` | `gemeente`, `waterschap`, `gr`, `provincie` |
| `bron` | `ori` (enige ondersteunde bron op dit moment) |
| `vergadertypen` | zie `organen/README.md` voor standaarden per type |

**Stap 3 — Test**

Controleer dat de scraper de vergadertypen correct vindt:

```bash
python3 scraper.py <orgaannaam> --droog
```

Verwacht resultaat: vergaderingen worden gevonden die overeenkomen met de opgegeven vergadertypen. Als er nul vergaderingen worden gevonden, controleer dan de spelling (hoofdletterongevoelig, gedeeltelijke match).

**Stap 4 — Open een pull request**

Eén orgaan per PR, met een korte beschrijving van wat het orgaan is en hoe je de vergadertypen hebt geverifieerd.

---

## Andere bijdragen

- **Bugmeldingen** — open een issue met reproductiestappen
- **Prompts** — nieuwe analyseprompts in `prompts/` zijn welkom; volg de structuur van de bestaande bestanden
- **Documentatie** — verbeteringen aan README of andere documentatie via een PR

---

## Wat buiten scope valt

De toolkit is bewust begrensd. Bijdragen die buiten de filosofische grenzen vallen worden niet opgenomen — zie het onderdeel *Grenzen* in `roadmap.md` voor de redenering darachter. Kortweg: geen persoonsgegevens, geen sociale media, geen webinterface, geen cloudopslag.
