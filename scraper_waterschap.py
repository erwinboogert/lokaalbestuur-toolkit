"""
Scraper voor vergaderstukken van Nederlandse waterschappen
Bronnen: Open Raadsinformatie API (openraadsinformatie.nl) en iBabs SOAP API

Waterschappen zijn democratisch gekozen bestuursorganen voor waterveiligheid,
dijkbeheer en rioolwaterzuivering. Ze vergaderen openbaar maar worden
nauwelijks journalistiek gevolgd. De ORI API ontsluit ze via de owi_-prefix;
waterschappen zonder ORI-koppeling worden via iBabs benaderd.

Gebruik:
    python3 scraper_waterschap.py hollandse-delta           # download vergaderstukken
    python3 scraper_waterschap.py hollandse-delta --droog   # toon wat er gedownload zou worden
    python3 scraper_waterschap.py --lijst                   # toon geconfigureerde waterschappen
    python3 scraper_waterschap.py --lijst-ori               # toon alle waterschappen in ORI

Configuratie: bronnen/waterschappen.json
Output: ~/Documents/notulen/waterschappen/<naam>/

Vergadertypen worden geladen uit bronnen/waterschappen.json.
Vereisten: geen externe bibliotheken (alleen standaard Python 3)
"""

import json
import re
import sys
from pathlib import Path

from api import (
    OUTPUT_BASIS, BRONNEN_MAP,
    setup_logging, log, log_samenvatting, vraag_doorzoekbaar_maken, parse_jaren_arg,
    toon_deelnemende_gemeenten,
    alle_indices,
    haal_vergaderingen_ori,
    haal_vergaderingen_ibabs,
    download_vergaderingen_ori, download_vergaderingen_ibabs,
)

# ══════════════════════════════════════════════════════════════════════════════
# CONFIGURATIE
# ══════════════════════════════════════════════════════════════════════════════

STANDAARD_VERGADERTYPEN = {
    "algemeen bestuur":                    True,
    "college van dijkgraaf en heemraden":  True,
    "dagelijks bestuur":                   True,
    "verenigde vergadering":               True,
}

MAX_VERGADERINGEN = 50

# ══════════════════════════════════════════════════════════════════════════════


def _lees_waterschap_config(naam: str) -> dict:
    """Lees de configuratie voor een waterschap uit waterschappen.json."""
    pad = BRONNEN_MAP / "waterschappen.json"
    if not pad.exists():
        return {}
    try:
        config = json.loads(pad.read_text(encoding="utf-8"))
        return config.get(naam, {})
    except Exception:
        return {}


def laad_vergadertypen(naam: str) -> dict[str, bool]:
    """Laad vergadertypen uit waterschappen.json of gebruik standaard."""
    config = _lees_waterschap_config(naam)
    if "vergadertypen" in config:
        return {vtype: True for vtype in config["vergadertypen"]}
    return dict(STANDAARD_VERGADERTYPEN)


def find_index_waterschap(naam: str) -> str | None:
    """Zoek de meest recente ORI-index (owi_-prefix) voor het waterschap."""
    indices = alle_indices()

    config = _lees_waterschap_config(naam)
    if "ori_index" in config:
        ori_naam = config["ori_index"]
        prefix = f"owi_{ori_naam}_"
        matches = sorted(i for i in indices if i.startswith(prefix))
        if matches:
            return matches[-1]

    prefix = f"owi_{naam.lower().replace(' ', '_').replace('-', '_')}_"
    matches = sorted(i for i in indices if i.startswith(prefix))
    return matches[-1] if matches else None


# ── Lijsten ───────────────────────────────────────────────────────────────────

def lijst_waterschappen():
    """Toon geconfigureerde waterschappen uit waterschappen.json."""
    pad = BRONNEN_MAP / "waterschappen.json"
    if not pad.exists():
        print("\nGeen waterschappen.json gevonden in bronnen/\n")
        return
    config = json.loads(pad.read_text(encoding="utf-8"))
    waterschappen = {k: v for k, v in config.items() if not k.startswith("_")}
    if not waterschappen:
        print("\nNog geen waterschappen geconfigureerd.")
        print("Gebruik 'python3 toolkit.py nieuw-waterschap' om er een toe te voegen.")
        print("Of gebruik '--lijst-ori' om te zien welke beschikbaar zijn in ORI.\n")
        return
    print(f"\n{len(waterschappen)} geconfigureerde waterschappen:\n")
    for slug, data in sorted(waterschappen.items()):
        naam = data.get("naam", slug)
        if "ibabs_naam" in data:
            bron = f"ibabs: {data['ibabs_naam']}.bestuurlijkeinformatie.nl"
        else:
            ori = data.get("ori_index", "?")
            bron = f"ori: owi_{ori}"
        print(f"  {slug:<30} {naam}  ({bron})")
    print()


def lijst_ori_waterschappen():
    """Toon beschikbare owi_-indices in de ORI API."""
    indices = alle_indices()
    owi_indices = sorted(i for i in indices if i.startswith("owi_"))

    basisnamen = sorted(set(
        i.replace("owi_", "").rsplit("_", 2)[0]
        for i in owi_indices
    ))

    print()
    print("Beschikbare waterschappen in de ORI API")
    print("─" * 50)
    print()
    print(f"  {len(basisnamen)} waterschappen gevonden (owi_-prefix):\n")
    for naam in basisnamen:
        prefix = f"owi_{naam}_"
        recente = sorted(i for i in owi_indices if i.startswith(prefix))
        print(f"  {naam}")
        if recente:
            print(f"    → {recente[-1]}")
    print()
    print("  Gebruik de basisnaam (zonder 'owi_' en tijdstempel) als ori_index")
    print("  bij 'python3 toolkit.py nieuw-waterschap'.")
    print()


# ── Hoofdprogramma ────────────────────────────────────────────────────────────

def main():
    args = sys.argv[1:]
    vlaggen = {a for a in args if a.startswith("--")}
    droog = "--droog" in vlaggen
    args = [a for a in args if not a.startswith("--")]

    if "--lijst-ori" in vlaggen:
        lijst_ori_waterschappen()
        return

    if "--lijst" in vlaggen or not args:
        lijst_waterschappen()
        if not args:
            print(__doc__)
        return

    naam = args[0].lower()
    if not re.match(r'^[a-z0-9][a-z0-9\-\ ]{0,60}$', naam):
        print(f"Ongeldige naam: '{naam}'. Gebruik alleen letters, cijfers en koppeltekens.")
        sys.exit(1)

    vergadertypen = laad_vergadertypen(naam)
    config = _lees_waterschap_config(naam)
    output_map = OUTPUT_BASIS / "waterschappen" / naam
    setup_logging(output_map)

    log("=" * 60)
    log(f"Waterschap: {naam}  {'(DROOG)' if droog else ''}")
    log("=" * 60)

    vanaf, terugkijk_dagen = parse_jaren_arg()

    ibabs_naam = config.get("ibabs_naam")
    if ibabs_naam:
        log(f"Bron: iBabs ({ibabs_naam}.bestuurlijkeinformatie.nl)")
        vergaderingen = haal_vergaderingen_ibabs(
            ibabs_naam, vergadertypen, terugkijk_dagen=terugkijk_dagen)
        log(f"{len(vergaderingen)} vergaderingen gevonden")
        if not vergaderingen:
            log("Geen vergaderingen gevonden met de geconfigureerde vergadertypen.")
            log(f"Actieve types: {', '.join(k for k, v in vergadertypen.items() if v)}")

        nieuw, overgeslagen, fouten = download_vergaderingen_ibabs(
            vergaderingen, output_map, droog)
        log_samenvatting(nieuw, overgeslagen, fouten, output_map)
        if not droog:
            vraag_doorzoekbaar_maken(nieuw, output_map)
        toon_deelnemende_gemeenten("waterschap", naam)
        return

    index = find_index_waterschap(naam)
    if not index:
        log(f"FOUT: geen ORI-index gevonden voor '{naam}'.")
        log("Gebruik --lijst-ori om beschikbare waterschappen te ontdekken.")
        log("Voeg het waterschap toe via: python3 toolkit.py nieuw-waterschap")
        sys.exit(1)
    log(f"Bron: ORI-index {index}")

    vergaderingen = haal_vergaderingen_ori(index, vergadertypen, MAX_VERGADERINGEN, vanaf)
    log(f"{len(vergaderingen)} vergaderingen gevonden")

    if not vergaderingen:
        log("Geen vergaderingen gevonden met de geconfigureerde vergadertypen.")
        log(f"Actieve types: {', '.join(k for k, v in vergadertypen.items() if v)}")

    nieuw, overgeslagen, fouten = download_vergaderingen_ori(
        vergaderingen, index, output_map, droog)
    log_samenvatting(nieuw, overgeslagen, fouten, output_map)
    if not droog:
        vraag_doorzoekbaar_maken(nieuw, output_map)
    toon_deelnemende_gemeenten("waterschap", naam)


if __name__ == "__main__":
    main()
