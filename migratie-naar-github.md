# Migratie naar publieke GitHub

Dit document beschrijft welke persoonlijke informatie uit de toolkit moet worden verwijderd of vervangen vóór publicatie op GitHub, en hoe toekomstige gebruikers de toolkit kunnen instellen voor hun eigen situatie.

---

## Wat is persoonlijk en moet worden aangepast

### 1. `analyse.py` — configuratieblok (de enige plek met persoonlijke inhoud)

Twee variabelen bevatten jouw specifieke dossier:

```python
DOSSIER_LABEL = "asielzoekers-opvang"          # ← jouw dossier
TREFWOORDEN = [
    "asielzoeker", "asielopvang", ...           # ← jouw trefwoorden
]
```

**Oplossing:** vervang door duidelijke placeholders met commentaar (zie onderstaand voorstel). De rest van `analyse.py` is volledig generiek en kan ongewijzigd op GitHub.

### 2. `CLAUDE.md` — verwijzing naar jouw archief

```
Barendrecht (bestaand archief): ~/Documents/notulen-barendrecht/
```

Dit is context voor Claude Code in jouw persoonlijke werksituatie — niet relevant voor andere gebruikers. **Verwijderen of generaliseren.**

### 3. Verder niets

`scraper.py`, alle prompts, de skill en de checklist bevatten geen persoonlijke informatie en kunnen ongewijzigd worden gepubliceerd.

---

## Voorstel: placeholders in `analyse.py`

Vervang het configuratieblok door dit — dan is het bestand zelf de instructie voor nieuwe gebruikers:

```python
# ══════════════════════════════════════════════════════════════════════════════
# CONFIGURATIE — pas dit aan voor jouw dossier
# ══════════════════════════════════════════════════════════════════════════════

# Label voor dit dossier — verschijnt in de alerttitel en bestandsnaam
DOSSIER_LABEL = "mijn-dossier"                  # ← AANPASSEN

# Trefwoorden voor de voorselectie (hoofdletterongevoelig)
# Tip: gebruik meervoudsvormen en afkortingen apart
TREFWOORDEN = [
    "trefwoord-1",                              # ← AANPASSEN
    "trefwoord-2",
    "trefwoord-3",
]
```

Het commentaar `# ← AANPASSEN` is de markering voor elke nieuwe gebruiker.

---

## Wat kan worden geautomatiseerd: een setup-script

Een klein `setup.py` kan nieuwe gebruikers interactief door de configuratie leiden:

```
python3 setup.py
```

```
Lokaalbestuur Toolkit — eerste installatie
--------------------------------------------
Naam van je dossier (bijv. woningbouw): woningbouw
Trefwoorden, gescheiden door komma: grond, bouwplan, bestemmingsplan, woningcorporatie

✓ analyse-woningbouw.py aangemaakt op basis van template.
✓ Klaar. Voer uit met: python3 analyse-woningbouw.py <gemeente>
```

Dit maakt automatisch een werkende kopie van `analyse.py` met de ingevoerde waarden. De basis-`analyse.py` blijft de generieke template.

---

## Actielijst voor publicatie

- [ ] Configuratieblok in `analyse.py` vervangen door placeholders (zie boven)
- [ ] Barendrecht-verwijzing in `CLAUDE.md` verwijderen of generaliseren
- [ ] `.gitignore` aanmaken voor eventuele persoonlijke analyse-kopieën (`analyse-*.py`)
- [ ] Optioneel: `setup.py` schrijven voor geautomatiseerde eerste installatie
- [ ] Repository aanmaken op GitHub en initiële commit pushen

---

## Aanbevolen `.gitignore`

```gitignore
# Persoonlijke dossierscripts (kopieën van analyse.py met eigen trefwoorden)
analyse-*.py

# macOS
.DS_Store
```

Zo kunnen gebruikers hun eigen `analyse-woningbouw.py` of `analyse-grond.py` lokaal bewaren zonder dat die per ongeluk op GitHub belanden.
