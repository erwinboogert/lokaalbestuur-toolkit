"""
Scraper voor openbare raadsdocumenten van Nederlandse gemeenten
Bron: Open Raadsinformatie API (openraadsinformatie.nl)

Gebruik:
    python3 scraper.py arnhem                        # download documenten van Arnhem
    python3 scraper.py arnhem --jaren 1              # alleen het afgelopen jaar
    python3 scraper.py arnhem --jaren 2              # de afgelopen 2 jaar
    python3 scraper.py arnhem --vanaf 2023-01-01     # vanaf een specifieke datum
    python3 scraper.py arnhem --droog                # laat zien wat er nieuw is, download niets
    python3 scraper.py                               # toon lijst van beschikbare gemeenten

Vergadertypen worden automatisch geladen uit organen/<naam>.json als dat bestand aanwezig is.
Zonder orgaan-config worden de standaard vergadertypen gebruikt (zie CONFIGURATIE hieronder).

Vereisten: geen externe bibliotheken (alleen standaard Python 3)
"""

import json
import re
import sys
from datetime import datetime, timedelta
from pathlib import Path

from api import (
    OUTPUT_BASIS, DATA_MAP, TOOLKIT_MAP, BRONNEN_MAP,
    setup_logging, log, log_samenvatting, vraag_doorzoekbaar_maken,
    veilige_naam, download,
    alle_indices, find_index,
    haal_vergaderingen_ori, haal_documenten_ori,
    haal_vergaderingen_notubiz, haal_documenten_notubiz,
)

# ══════════════════════════════════════════════════════════════════════════════
# CONFIGURATIE
# ══════════════════════════════════════════════════════════════════════════════

_ORGANEN_MAP = (DATA_MAP / "organen") if DATA_MAP else (TOOLKIT_MAP / "organen")

STANDAARD_VERGADERTYPEN = {
    "gemeenteraad":         True,
    "commissie":            True,
    "raadsbrede commissie": True,
}

MAX_VERGADERINGEN = 500

# ══════════════════════════════════════════════════════════════════════════════


def lijst_gemeenten():
    """Print alle beschikbare gemeenten."""
    indices = alle_indices()
    gemeenten = sorted(set(
        i.replace("ori_", "").rsplit("_", 2)[0].replace("_", "-")
        for i in indices if i.startswith("ori_")
    ))
    print(f"\n{len(gemeenten)} beschikbare gemeenten:\n")
    for g in gemeenten:
        print(f"  {g}")
    print()


# ── Gemeente-specifieke mappenstructuur ──────────────────────────────────────

def vergadering_map(output_map: Path, vergadering: dict) -> Path:
    """Gemeenten hebben een specifieke mappenstructuur per vergadertype."""
    naam = vergadering["naam"].lower()
    if "gemeenteraad" in naam:
        vtype = "gemeenteraad"
    elif "raadsbrede" in naam:
        vtype = "raadsbrede-commissie"
    else:
        vtype = veilige_naam(vergadering["naam"])
    return output_map / vtype / vergadering["datum"]


# ── Orgaan-config ────────────────────────────────────────────────────────────

def laad_orgaan_config(orgaan_naam: str) -> tuple[dict[str, bool], int | None]:
    """Laad vergadertypen uit orgaan-config. Geeft (vergadertypen, notubiz_id)."""
    pad = _ORGANEN_MAP / f"{orgaan_naam}.json"
    if not pad.exists():
        return dict(STANDAARD_VERGADERTYPEN), None
    config = json.loads(pad.read_text(encoding="utf-8"))
    if "vergadertypen" in config:
        vergadertypen = {vtype: True for vtype in config["vergadertypen"]}
    else:
        vergadertypen = dict(STANDAARD_VERGADERTYPEN)
    return vergadertypen, config.get("notubiz_id")


# ── Argumenten ───────────────────────────────────────────────────────────────

def _parse_vanaf() -> str | None:
    """Lees --vanaf DATUM of --jaren N uit sys.argv en geef een ISO-datumstring terug."""
    argv = sys.argv[1:]
    if "--vanaf" in argv:
        idx = argv.index("--vanaf")
        if idx + 1 < len(argv):
            waarde = argv[idx + 1]
            if re.match(r"^\d{4}-\d{2}-\d{2}$", waarde):
                return waarde
            print(f"Ongeldige datum bij --vanaf: '{waarde}'. Verwacht formaat: YYYY-MM-DD")
            sys.exit(1)
    if "--jaren" in argv:
        idx = argv.index("--jaren")
        if idx + 1 < len(argv):
            try:
                jaren = float(argv[idx + 1])
                return (datetime.now() - timedelta(days=int(jaren * 365))).strftime("%Y-%m-%d")
            except ValueError:
                print(f"Ongeldige waarde bij --jaren: '{argv[idx + 1]}'. Verwacht een getal.")
                sys.exit(1)
    return None


# ── Hoofdprogramma ────────────────────────────────────────────────────────────

def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    droog = "--droog" in sys.argv

    if not args or args[0] in ("-h", "--help", "-?", "help"):
        print(__doc__)
        if not args:
            lijst_gemeenten()
        sys.exit(0)

    gemeente = args[0].lower()
    if not re.match(r'^[a-z0-9][a-z0-9\-\ ]{0,60}$', gemeente):
        print(f"Ongeldige gemeentenaam: '{gemeente}'. Gebruik alleen letters, cijfers en koppeltekens.")
        sys.exit(1)

    vanaf = _parse_vanaf()
    vergadertypen, notubiz_id = laad_orgaan_config(gemeente)

    output_map = OUTPUT_BASIS / gemeente
    setup_logging(output_map)

    log("=" * 60)
    log(f"Gemeente: {gemeente.capitalize()}  {'(DROOG)' if droog else ''}")
    if vanaf:
        log(f"Periode:  vanaf {vanaf}")
    log("=" * 60)

    index = find_index(gemeente)
    gebruik_notubiz = False

    if not index:
        if notubiz_id:
            log(f"Geen ORI-index gevonden. Gebruik Notubiz (organisatie-ID {notubiz_id}).")
            gebruik_notubiz = True
        else:
            log(f"FOUT: geen index gevonden voor '{gemeente}'.")
            log("Voer het script uit zonder argument voor een lijst van beschikbare gemeenten.")
            log("Of voeg een notubiz_id toe aan de orgaan-config als de gemeente via Notubiz publiceert.")
            sys.exit(1)
    else:
        log(f"Index: {index}")

    if gebruik_notubiz:
        vergaderingen = haal_vergaderingen_notubiz(notubiz_id, vergadertypen)
        if vanaf:
            vergaderingen = [v for v in vergaderingen if v["datum"] >= vanaf]
        vergaderingen = vergaderingen[:MAX_VERGADERINGEN]
    else:
        vergaderingen = haal_vergaderingen_ori(index, vergadertypen, MAX_VERGADERINGEN, vanaf)
    log(f"{len(vergaderingen)} vergaderingen gevonden")

    totaal_nieuw = totaal_overgeslagen = totaal_fout = 0

    for verg in vergaderingen:
        if gebruik_notubiz:
            docs = haal_documenten_notubiz(verg["id"])
        else:
            docs = haal_documenten_ori(index, verg["id"])
        if not docs:
            continue

        doelmap = vergadering_map(output_map, verg)
        nieuwe_docs = [d for d in docs
                       if not (doelmap / (veilige_naam(d["naam"]) + ".pdf")).exists()]

        if not nieuwe_docs:
            totaal_overgeslagen += len(docs)
            continue

        log(f"\n  {verg['naam']} ({verg['datum']}) — {len(nieuwe_docs)} nieuw van {len(docs)}")

        if not droog:
            doelmap.mkdir(parents=True, exist_ok=True)

        for doc in docs:
            bestandsnaam = veilige_naam(doc["naam"]) + ".pdf"
            bestemming = doelmap / bestandsnaam

            if bestemming.exists():
                totaal_overgeslagen += 1
                continue

            if droog:
                log(f"    [DROOG] {bestandsnaam}")
                totaal_nieuw += 1
                continue

            try:
                grootte = download(doc["url"], bestemming)
                log(f"    + {bestandsnaam} ({grootte / 1024:.0f} KB)")
                totaal_nieuw += 1
            except Exception as e:
                log(f"    ! FOUT: {bestandsnaam} — {e}")
                totaal_fout += 1

    log_samenvatting(totaal_nieuw, totaal_overgeslagen, totaal_fout, output_map)
    if not droog:
        vraag_doorzoekbaar_maken(totaal_nieuw, output_map)
    toon_gerelateerde_organen(gemeente)


# ── Gerelateerde organen ─────────────────────────────────────────────────────

def _zoek_in_bronbestand(bestandsnaam: str, gemeente: str) -> list[tuple[str, str]]:
    """Zoek een gemeente in een bronnen-JSON. Geeft [(slug, naam), ...]."""
    pad = BRONNEN_MAP / bestandsnaam
    if not pad.exists():
        return []
    data = json.loads(pad.read_text(encoding="utf-8"))
    return [
        (slug, info["naam"])
        for slug, info in data.items()
        if not slug.startswith("_") and gemeente in info.get("gemeenten", [])
    ]


def toon_gerelateerde_organen(gemeente: str):
    """Toon VR, waterschappen en GR's die bij deze gemeente horen."""
    vrs = _zoek_in_bronbestand("veiligheidsregios.json", gemeente)
    waterschappen = _zoek_in_bronbestand("waterschappen.json", gemeente)
    regelingen = _zoek_in_bronbestand("regelingen.json", gemeente)

    if not vrs and not waterschappen and not regelingen:
        return

    log("")
    log("  Gerelateerde organen")
    log("  " + "─" * 56)

    if vrs:
        log("  Veiligheidsregio:")
        for slug, naam in vrs:
            log(f"    → {naam:<45s} python3 scraper_vr.py {slug}")

    if waterschappen:
        log("  Waterschappen:")
        for slug, naam in waterschappen:
            log(f"    → {naam:<45s} python3 scraper_waterschap.py {slug}")

    if regelingen:
        log("  Gemeenschappelijke regelingen:")
        for slug, naam in regelingen:
            log(f"    → {naam:<45s} python3 scraper_gr.py {slug}")

    log("  " + "─" * 56)


if __name__ == "__main__":
    main()
