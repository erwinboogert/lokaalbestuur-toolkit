"""
Scraper voor vergaderstukken van gemeenschappelijke regelingen (GRs)
Bronnen: Open Raadsinformatie API (ORI), Notubiz API direct, of iBabs SOAP API

Gemeenschappelijke regelingen zijn samenwerkingsverbanden tussen gemeenten:
veiligheidsregio's, sociale diensten, omgevingsdiensten, jeugdhulpregio's.
Ze vergaderen openbaar maar worden nauwelijks journalistiek gevolgd.

De scraper ondersteunt drie bronnen:
  - ORI API: GRs die als gemeente-index in ORI staan (ori_-prefix)
  - Notubiz API direct: elke GR met een notubiz_id in bronnen/regelingen.json
  - iBabs SOAP API: elke GR met een ibabs_naam in bronnen/regelingen.json

De Notubiz API is volledig openbaar. Elk Notubiz-portaal van een GR heeft
een organisatie-ID dat je kunt opzoeken via:
    python3 scraper_gr.py --zoek <naam>

De iBabs Sitename vind je in de URL van het vergaderportaal van de GR,
bijv. https://dcmr.bestuurlijkeinformatie.nl → ibabs_naam: "dcmr"

Gebruik:
    python3 scraper_gr.py nieuw-reijerwaard      # download vergaderstukken
    python3 scraper_gr.py nieuw-reijerwaard --droog  # droog uitvoeren
    python3 scraper_gr.py --lijst                # toon geconfigureerde GRs
    python3 scraper_gr.py --lijst-ori            # ontdek GRs in de ORI API
    python3 scraper_gr.py --zoek jeugdhulp       # zoek GR in Notubiz

Configuratie: bronnen/regelingen.json
Output: ~/Documents/notulen/regelingen/<naam>/

Vereisten: geen externe bibliotheken (alleen standaard Python 3)
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

from api import (
    OUTPUT_BASIS, BRONNEN_MAP,
    setup_logging, log, log_samenvatting, vraag_doorzoekbaar_maken, parse_jaren_arg,
    toon_deelnemende_gemeenten,
    alle_indices,
    notubiz_verzoek,
    haal_vergaderingen_notubiz,
    haal_vergaderingen_ibabs,
    download_vergaderingen_ori, download_vergaderingen_notubiz, download_vergaderingen_ibabs,
    haal_vergaderingen_ori, haal_documenten_ori,
)

# ══════════════════════════════════════════════════════════════════════════════
# CONFIGURATIE
# ══════════════════════════════════════════════════════════════════════════════

STANDAARD_VERGADERTYPEN = {
    "algemeen bestuur":           True,
    "dagelijks bestuur":          True,
    "portefeuillehoudersoverleg": True,
}

MAX_VERGADERINGEN = 50

# ══════════════════════════════════════════════════════════════════════════════


def find_index_gr(naam: str) -> str | None:
    """Zoek de meest recente ORI-index voor de opgegeven GR.

    Probeert eerst de ori_index uit regelingen.json. Valt daarna terug
    op directe naammatching.
    """
    indices = alle_indices()

    pad = BRONNEN_MAP / "regelingen.json"
    if pad.exists():
        try:
            config = json.loads(pad.read_text(encoding="utf-8"))
            if naam in config and "ori_index" in config[naam]:
                ori_naam = config[naam]["ori_index"]
                prefix = f"ori_{ori_naam.lower().replace(' ', '_').replace('-', '_')}_"
                matches = sorted(i for i in indices if i.startswith(prefix))
                if matches:
                    return matches[-1]
        except Exception:
            pass

    prefix = f"ori_{naam.lower().replace(' ', '_').replace('-', '_')}_"
    matches = sorted(i for i in indices if i.startswith(prefix))
    return matches[-1] if matches else None


def _lees_regeling_config(naam: str) -> dict:
    """Lees de configuratie voor een GR uit regelingen.json."""
    pad = BRONNEN_MAP / "regelingen.json"
    if not pad.exists():
        return {}
    try:
        config = json.loads(pad.read_text(encoding="utf-8"))
        return config.get(naam, {})
    except Exception:
        return {}


def laad_vergadertypen(naam: str) -> dict[str, bool]:
    """Laad vergadertypen uit regelingen.json of gebruik standaard."""
    config = _lees_regeling_config(naam)
    if "vergadertypen" in config:
        return {vtype: True for vtype in config["vergadertypen"]}
    return dict(STANDAARD_VERGADERTYPEN)


# ── Lijsten ───────────────────────────────────────────────────────────────────

def lijst_regelingen():
    """Toon geconfigureerde GRs uit regelingen.json."""
    pad = BRONNEN_MAP / "regelingen.json"
    if not pad.exists():
        print("\nGeen regelingen.json gevonden in bronnen/\n")
        return
    config = json.loads(pad.read_text(encoding="utf-8"))
    regelingen = {k: v for k, v in config.items() if not k.startswith("_")}
    if not regelingen:
        print("\nNog geen regelingen geconfigureerd.")
        print("Gebruik 'python3 toolkit.py nieuwe-regeling' om er een toe te voegen.")
        print("Of gebruik '--lijst-ori' om te zien welke GRs beschikbaar zijn in ORI.\n")
        return
    print(f"\n{len(regelingen)} geconfigureerde regelingen:\n")
    for slug, data in sorted(regelingen.items()):
        naam = data.get("naam", slug)
        if data.get("notubiz_id"):
            bron = f"notubiz:{data['notubiz_id']}"
        elif data.get("ibabs_naam"):
            bron = f"ibabs:{data['ibabs_naam']}"
        elif data.get("ori_index"):
            bron = f"ori:{data['ori_index']}"
        else:
            bron = "?"
        print(f"  {slug:<32} {naam:<45} ({bron})")
    print()


def lijst_ori_gr():
    """Toon beschikbare ORI-indices."""
    indices = alle_indices()

    ori = sorted(set(
        i.replace("ori_", "").rsplit("_", 2)[0].replace("_", "-")
        for i in indices if i.startswith("ori_")
    ))
    owi = sorted(set(
        i.replace("owi_", "").rsplit("_", 2)[0].replace("_", "-")
        for i in indices if i.startswith("owi_")
    ))
    osi = sorted(set(
        i.replace("osi_", "").rsplit("_", 2)[0].replace("_", "-")
        for i in indices if i.startswith("osi_")
    ))

    print()
    print("Beschikbare indices in de ORI API")
    print("─" * 50)
    print()
    print(f"  ori_  {len(ori)} gemeenten (raadsstukken via Notubiz/iBabs)")
    print(f"  owi_  {len(owi)} waterschappen")
    print(f"  osi_  {len(osi)} provincies")
    print()
    print("  Gemeenschappelijke regelingen zijn momenteel NIET")
    print("  opgenomen in de ORI API. Zoek de stukken van jouw GR")
    print("  op de eigen website of via Notubiz (notubiz.nl).")
    print()
    print("  Als jouw GR wél in ORI staat (bijv. als gemeente geregistreerd),")
    print("  zoek de naam dan in onderstaande lijst en gebruik die als ori_index")
    print("  bij 'python3 toolkit.py nieuwe-regeling'.")
    print()
    print(f"  Alle {len(ori)} gemeenten in ORI:\n")
    for naam in ori:
        print(f"    {naam}")
    print()


def zoek_notubiz_organisaties(zoekterm: str) -> list[dict]:
    """Zoek GR-organisaties in de Notubiz-catalogus op naam."""
    data = notubiz_verzoek("organisations")
    orgs = data.get("organisations", {}).get("organisation", [])
    term = zoekterm.lower()
    return [
        {
            "id": int(o.get("@attributes", {}).get("id", 0) or o.get("id", 0)),
            "naam": o.get("name", "").strip(),
        }
        for o in orgs
        if term in o.get("name", "").lower()
    ]


# ── Hoofdprogramma ────────────────────────────────────────────────────────────

def main():
    args = sys.argv[1:]
    vlaggen = {a for a in args if a.startswith("--")}
    droog = "--droog" in vlaggen
    args = [a for a in args if not a.startswith("--")]

    if "--lijst-ori" in vlaggen:
        lijst_ori_gr()
        return

    if "--lijst" in vlaggen or not args:
        lijst_regelingen()
        if not args:
            print(__doc__)
        return

    if "--zoek" in vlaggen:
        if not args:
            print("\nGebruik: python3 scraper_gr.py --zoek <zoekterm>\n")
            sys.exit(1)
        zoekterm = " ".join(args)
        resultaten = zoek_notubiz_organisaties(zoekterm)
        if not resultaten:
            print(f"\nGeen Notubiz-organisaties gevonden voor '{zoekterm}'.\n")
        else:
            print(f"\n{len(resultaten)} organisaties gevonden voor '{zoekterm}':\n")
            for r in resultaten:
                print(f"  {r['id']:<8} {r['naam']}")
            print()
            print("Voeg toe aan bronnen/regelingen.json met notubiz_id, of gebruik:")
            print("  python3 toolkit.py nieuwe-regeling\n")
        return

    naam = args[0].lower()
    if not re.match(r'^[a-z0-9][a-z0-9\-\ ]{0,60}$', naam):
        print(f"Ongeldige naam: '{naam}'. Gebruik alleen letters, cijfers en koppeltekens.")
        sys.exit(1)

    vergadertypen = laad_vergadertypen(naam)
    config = _lees_regeling_config(naam)
    output_map = OUTPUT_BASIS / "regelingen" / naam
    setup_logging(output_map)

    log("=" * 60)
    log(f"GR: {naam}  {'(DROOG)' if droog else ''}")
    log("=" * 60)

    vanaf, terugkijk_dagen = parse_jaren_arg()

    notubiz_id = config.get("notubiz_id")
    ibabs_naam = config.get("ibabs_naam")

    if notubiz_id:
        log(f"Bron: Notubiz API (org_id={notubiz_id})")
        vergaderingen = haal_vergaderingen_notubiz(
            notubiz_id, vergadertypen, terugkijk_dagen=terugkijk_dagen)
        log(f"{len(vergaderingen)} vergaderingen gevonden")
        nieuw, overgeslagen, fouten = download_vergaderingen_notubiz(
            vergaderingen, output_map, droog)

    elif ibabs_naam:
        log(f"Bron: iBabs API (sitename={ibabs_naam})")
        vergaderingen = haal_vergaderingen_ibabs(
            ibabs_naam, vergadertypen, terugkijk_dagen=terugkijk_dagen)
        log(f"{len(vergaderingen)} vergaderingen gevonden")
        nieuw, overgeslagen, fouten = download_vergaderingen_ibabs(
            vergaderingen, output_map, droog)

    else:
        index = find_index_gr(naam)
        if not index:
            log(f"FOUT: geen ORI-index, notubiz_id of ibabs_naam gevonden voor '{naam}'.")
            log("Gebruik --lijst-ori om beschikbare GRs in ORI te ontdekken.")
            log("Gebruik --zoek <naam> om een Notubiz-organisatie op te zoeken.")
            log("Voeg de GR toe via: python3 toolkit.py nieuwe-regeling")
            sys.exit(1)
        log(f"Bron: ORI API (index={index})")

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
    toon_deelnemende_gemeenten("gr", naam)


if __name__ == "__main__":
    main()
