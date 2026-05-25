"""
bouw_gr_index.py — Bouwt bronnen/regelingen_overheid.json

Haalt alle gemeenschappelijke regelingen op van organisaties.overheid.nl
en slaat naam, overheid_id en url_slug op per regeling.

Gebruik:
    python3 bouw_gr_index.py
    python3 bouw_gr_index.py --update-catalogus

Opties:
    --update-catalogus   Vul overheid_id automatisch in voor catalogusentries
                         in bronnen/regelingen.json die dat veld nog missen.

Output:
    bronnen/regelingen_overheid.json   complete index (~400 GRs)
"""

import json
import re
import sys
import urllib.request
from datetime import date
from pathlib import Path

# ── Paden ─────────────────────────────────────────────────────────────────────

TOOLKIT_MAP   = Path(__file__).parent
BRONNEN_MAP   = TOOLKIT_MAP / "bronnen"
INDEX_PAD     = BRONNEN_MAP / "regelingen_overheid.json"
CATALOGUS_PAD = BRONNEN_MAP / "regelingen.json"

GR_LIJST_URL  = (
    "https://organisaties.overheid.nl"
    "/samenwerkingen/naam/Gemeenschappelijke_regelingen/"
)
USER_AGENT = "lokaalbestuur-toolkit/1.0"


# ── Ophalen ───────────────────────────────────────────────────────────────────

def _haal_pagina(url):
    req = urllib.request.Request(
        url,
        headers={"User-Agent": USER_AGENT, "Accept": "text/html"},
    )
    with urllib.request.urlopen(req, timeout=20) as resp:
        return resp.read().decode("utf-8")


def bouw_index():
    """Haalt alle GRs op. Geeft dict: overheid_id (str) → {naam, naam_volledig, url_slug}."""
    print(f"  Ophalen: {GR_LIJST_URL}")
    html = _haal_pagina(GR_LIJST_URL)

    index = {}
    for m in re.finditer(
        r'href="/samenwerkingen/(\d+)/([^"/?]+)[^"]*"\s*[^>]*>\s*([^<]+?)\s*</a>',
        html,
    ):
        overheid_id   = m.group(1)
        url_slug      = m.group(2)
        naam_volledig = m.group(3).strip()

        # Verwijder het generieke GR-prefix zodat de naam informatief is
        naam = re.sub(
            r"^Gemeenschappelijk[e]?\s+[Rr]egeling\s+",
            "",
            naam_volledig,
        ).strip()
        naam = (naam[0].upper() + naam[1:]) if naam else naam_volledig

        if overheid_id not in index:
            index[overheid_id] = {
                "naam":          naam,
                "naam_volledig": naam_volledig,
                "url_slug":      url_slug,
            }

    return index


# ── Catalogus bijwerken ───────────────────────────────────────────────────────

def _norm(s):
    """Normaliseer naam: lowercase, strip GR-prefix, alleen alfanumerieke woorden."""
    s = s.lower()
    s = re.sub(r"gemeenschappelijk[e]?\s+regeling\s*", "", s)
    s = re.sub(r"[^a-z0-9]", " ", s)
    return " ".join(s.split())


def _best_match(zoekterm, op_naam, op_volledig, index):
    """
    Drietraps matching:
      1. Exacte normalisatie-match
      2. Index-norm is substring van de catalogus-norm (bv. "meerinzicht" in
         "samenwerkingsverband meerinzicht")
      3. Significante-woordoverlap (≥ 2 woorden van 5+ tekens)
    Geeft (overheid_id, zekerheid) of (None, None).
    """
    # Stap 1: exact
    hit = op_naam.get(zoekterm) or op_volledig.get(zoekterm)
    if hit:
        return hit, "exact"

    # Stap 2: substring
    for oid, entry in index.items():
        idx_norm = _norm(entry["naam"])
        if len(idx_norm) > 4 and idx_norm in zoekterm:
            return oid, "substring"
        idx_vol  = _norm(entry["naam_volledig"])
        if len(idx_vol) > 4 and idx_vol in zoekterm:
            return oid, "substring"

    # Stap 3: woordoverlap (min. 2 significante woorden)
    cat_woorden = {w for w in zoekterm.split() if len(w) >= 5}
    if len(cat_woorden) < 2:
        return None, None
    beste_score, beste_id = 0, None
    for oid, entry in index.items():
        idx_woorden = {w for w in _norm(entry["naam"]).split() if len(w) >= 5}
        overlap = cat_woorden & idx_woorden
        score   = len(overlap) / max(len(cat_woorden), len(idx_woorden))
        if score > beste_score and score >= 0.5:
            beste_score, beste_id = score, oid
    if beste_id:
        return beste_id, f"overlap {beste_score:.0%}"

    return None, None


def update_catalogus(index):
    """Zoek en schrijf overheid_id voor catalogusentries die het nog missen."""
    if not CATALOGUS_PAD.exists():
        print("  Catalogus niet gevonden, overgeslagen.")
        return

    catalogus = json.loads(CATALOGUS_PAD.read_text(encoding="utf-8"))

    # Opzoektabellen op genormaliseerde naam (verkorte naam én volledige naam)
    op_naam     = {_norm(v["naam"]):          k for k, v in index.items()}
    op_volledig = {_norm(v["naam_volledig"]): k for k, v in index.items()}

    bijgewerkt = 0
    for slug, info in catalogus.items():
        if slug.startswith("_") or not isinstance(info, dict):
            continue
        if "overheid_id" in info:
            print(f"  — {slug}: al aanwezig ({info['overheid_id']})")
            continue

        cat_naam  = info.get("naam", "")
        zoekterm  = _norm(cat_naam)
        gevonden_id, zekerheid = _best_match(zoekterm, op_naam, op_volledig, index)

        if gevonden_id:
            info["overheid_id"] = int(gevonden_id)
            print(f"  ✓ {slug}: {gevonden_id}  (\"{index[gevonden_id]['naam']}\")  [{zekerheid}]")
            bijgewerkt += 1
        else:
            print(f"  ? {slug}: geen match voor '{cat_naam}' — handmatig controleren")

    if bijgewerkt:
        CATALOGUS_PAD.write_text(
            json.dumps(catalogus, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        print(f"\n  {bijgewerkt} entr{'y' if bijgewerkt == 1 else 'ies'} bijgewerkt in regelingen.json")
    else:
        print("\n  Niets te updaten in regelingen.json.")


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    update_cat = "--update-catalogus" in sys.argv

    print()
    print("  GR-index bouwen — organisaties.overheid.nl")
    print("  ────────────────────────────────────────────")

    try:
        index = bouw_index()
    except Exception as e:
        print(f"  ! Fout bij ophalen: {e}", file=sys.stderr)
        sys.exit(1)

    print(f"  {len(index)} gemeenschappelijke regelingen gevonden")

    # ── Opslaan ───────────────────────────────────────────────────────────────
    uitvoer = {
        "_opmerking": (
            "Volledige index van alle gemeenschappelijke regelingen op "
            "organisaties.overheid.nl. Sleutel = overheid_id (string). "
            "Gebruik dit voor betrouwbare koppeling tussen live "
            "verkennen-resultaten en de scrapeable regelingen in regelingen.json."
        ),
        "_gegenereerd": str(date.today()),
        "_bron": GR_LIJST_URL,
    }
    uitvoer.update(index)

    INDEX_PAD.write_text(
        json.dumps(uitvoer, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(f"  Opgeslagen: bronnen/regelingen_overheid.json")

    # ── Catalogus bijwerken ───────────────────────────────────────────────────
    if update_cat:
        print()
        print("  Catalogus bijwerken (regelingen.json)")
        print("  ─────────────────────────────────────")
        update_catalogus(index)

    print()


if __name__ == "__main__":
    main()
