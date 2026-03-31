"""
Analyse-script voor openbare raadsstukken van Nederlandse gemeenten
Werkt volledig lokaal — geen API of internetverbinding nodig.

Gebruik:
    python3 analyse.py --dossier asielopvang          # orgaan uit dossier-config
    python3 analyse.py barendrecht --dossier asielopvang   # orgaan expliciet opgeven
    python3 analyse.py barendrecht --droog            # zonder dossier, droog uitvoeren
    python3 analyse.py --dossier asielopvang --docs-map ~/archief/barendrecht

Werking:
    1. Kijk welke PDF's nieuw zijn sinds de vorige analyse
    2. Extraheer tekst uit die PDF's
    3. Filter op trefwoorden (uit dossier-config of CONFIGURATIE hieronder)
    4. Extraheer tekstfragmenten rondom trefwoorden
    5. Schrijf een gestructureerd alertrapport naar <docs-map>/alerts/
    6. Stuur een macOS-melding (optioneel)

Vereisten:
    pip install pdfplumber

Standaard map voor documenten: ~/Documents/notulen/<orgaan>/
Gebruik --docs-map om een andere map op te geven.
"""

import json
import logging
import subprocess
import sys
import re
from datetime import datetime
from pathlib import Path

import pdfplumber

# ══════════════════════════════════════════════════════════════════════════════
# CONFIGURATIE — pas dit aan voor jouw dossier
# ══════════════════════════════════════════════════════════════════════════════

# Bovenliggende map voor alle gemeentearchieven
# Per gemeente wordt hier een submap verwacht, bijv. ~/Documents/notulen/arnhem/
OUTPUT_BASIS = Path.home() / "Documents" / "notulen"

# Label voor dit dossier — verschijnt in de alerttitel en bestandsnaam
DOSSIER_LABEL = "asielzoekers-opvang"

# Trefwoorden voor de voorselectie (hoofdletterongevoelig)
# Tip: gebruik meervoudsvormen en afkortingen apart
TREFWOORDEN = [
    "asielzoeker", "asielopvang", "asielzoekers",
    "azc", "asielzoekerscentrum",
    "centraal orgaan opvang",
    "spreidingswet",
    "statushouder", "statushouders",
    "uitgeprocedeerd",
    "vluchteling", "vluchtelingen",
    "opvanglocatie", "crisisopvang",
    "inburgering", "inburgeraar",
    "vluchtelingenwerk",
]

# Aantal tekens context rondom elk trefwoord
CONTEXT_GROOTTE = 400

# Maximaal aantal fragmenten per document
MAX_FRAGMENTEN = 5

# macOS-melding sturen bij treffers? True / False
MACOS_MELDING = True

# ══════════════════════════════════════════════════════════════════════════════


def parse_args():
    args = sys.argv[1:]
    gemeente = None
    docs_map_override = None
    droog = "--droog" in args
    dossier_naam = None

    positional = [a for a in args if not a.startswith("--")]
    if positional:
        gemeente = positional[0].lower()

    if "--docs-map" in args:
        idx = args.index("--docs-map")
        if idx + 1 < len(args):
            docs_map_override = Path(args[idx + 1]).expanduser()

    if "--dossier" in args:
        idx = args.index("--dossier")
        if idx + 1 < len(args):
            dossier_naam = args[idx + 1]

    return gemeente, docs_map_override, droog, dossier_naam


def laad_dossier(naam: str) -> dict:
    """Laad dossierconfig uit dossiers/<naam>.json naast dit script."""
    toolkit_map = Path(__file__).parent
    dossier_pad = toolkit_map / "dossiers" / f"{naam}.json"
    if not dossier_pad.exists():
        beschikbaar = [p.stem for p in (toolkit_map / "dossiers").glob("*.json")]
        print(f"Dossier niet gevonden: {dossier_pad}")
        if beschikbaar:
            print(f"Beschikbare dossiers: {', '.join(sorted(beschikbaar))}")
        sys.exit(1)
    return json.loads(dossier_pad.read_text(encoding="utf-8"))


def setup_logging(log_bestand: Path):
    log_bestand.parent.mkdir(parents=True, exist_ok=True)
    handlers = [
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(log_bestand, encoding="utf-8"),
    ]
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s  %(message)s",
        datefmt="%Y-%m-%d %H:%M",
        handlers=handlers,
    )


def log(bericht: str):
    logging.info(bericht)


def laad_staat(staat_bestand: Path) -> set:
    if staat_bestand.exists():
        data = json.loads(staat_bestand.read_text(encoding="utf-8"))
        return set(data.get("geanalyseerd", []))
    return set()


def sla_staat_op(staat_bestand: Path, geanalyseerd: set):
    staat_bestand.parent.mkdir(parents=True, exist_ok=True)
    staat_bestand.write_text(
        json.dumps(
            {"geanalyseerd": sorted(geanalyseerd),
             "laatste_run": datetime.now().isoformat()},
            indent=2, ensure_ascii=False
        ),
        encoding="utf-8"
    )


def vind_nieuwe_pdfs(docs_map: Path, geanalyseerd: set) -> list[Path]:
    alle_pdfs = list(docs_map.rglob("*.pdf"))
    return [p for p in alle_pdfs if str(p) not in geanalyseerd]


def extraheer_tekst(pdf_pad: Path) -> str:
    try:
        with pdfplumber.open(str(pdf_pad)) as pdf:
            return "\n".join(p.extract_text() or "" for p in pdf.pages).strip()
    except Exception as e:
        log(f"  ! Tekstextractie mislukt: {pdf_pad.name} — {e}")
        return ""


def bevat_trefwoorden(tekst: str) -> list[str]:
    tekst_lower = tekst.lower()
    return [t for t in TREFWOORDEN if t in tekst_lower]


def extraheer_fragmenten(tekst: str, trefwoorden: list[str]) -> str:
    """Haal tekstfragmenten rondom gevonden trefwoorden op."""
    tekst_lower = tekst.lower()
    fragmenten = []
    gezien = set()

    for woord in trefwoorden:
        pos = 0
        while len(fragmenten) < MAX_FRAGMENTEN:
            idx = tekst_lower.find(woord, pos)
            if idx == -1:
                break
            start = max(0, idx - CONTEXT_GROOTTE)
            eind = min(len(tekst), idx + len(woord) + CONTEXT_GROOTTE)
            sleutel = start // (CONTEXT_GROOTTE * 2)
            if sleutel not in gezien:
                gezien.add(sleutel)
                fragment = tekst[start:eind].strip()
                # Markeer het trefwoord in het fragment
                fragment_gemarkeerd = re.sub(
                    re.escape(woord), f"**{woord}**", fragment, flags=re.IGNORECASE
                )
                fragmenten.append(f"> …{fragment_gemarkeerd}…")
            pos = idx + 1

        if len(fragmenten) >= MAX_FRAGMENTEN:
            break

    return "\n\n".join(fragmenten) if fragmenten else "(geen fragment gevonden)"


def stuur_macos_melding(titel: str, bericht: str):
    script = f'display notification "{bericht}" with title "{titel}" sound name "Glass"'
    subprocess.run(["osascript", "-e", script], check=False)


def schrijf_rapport(alerts_map: Path, gemeente: str, hits: list[dict], droog: bool) -> Path:
    datum = datetime.now().strftime("%Y-%m-%d")
    rapport_pad = alerts_map / f"alert-{datum}.md"

    regels = [
        f"# Alert raadsstukken {gemeente.capitalize()} — {datum}",
        f"",
        f"**Dossier:** {DOSSIER_LABEL}",
        f"**{len(hits)} document(en)** gevonden met relevante inhoud.",
        f"",
    ]

    for hit in hits:
        regels += [
            f"---",
            f"",
            f"## `{hit['bestand']}`",
            f"",
            f"**Trefwoorden:** {', '.join(f'`{t}`' for t in hit['trefwoorden'])}",
            f"",
            f"### Fragmenten uit document",
            f"",
            hit["fragmenten"],
            f"",
        ]

    if not droog:
        alerts_map.mkdir(parents=True, exist_ok=True)
        rapport_pad.write_text("\n".join(regels), encoding="utf-8")
        log(f"Rapport geschreven: {rapport_pad}")
    else:
        log("[DROOG] Rapport zou worden geschreven naar: {rapport_pad}")

    return rapport_pad


def main():
    gemeente, docs_map_override, droog, dossier_naam = parse_args()

    if not gemeente and not dossier_naam:
        print(__doc__)
        sys.exit(0)

    # Laad dossierconfig als --dossier is opgegeven; overschrijf dan de globale config
    if dossier_naam:
        global DOSSIER_LABEL, TREFWOORDEN
        config = laad_dossier(dossier_naam)
        DOSSIER_LABEL = config["label"]
        TREFWOORDEN = config["trefwoorden"]
        # Leid orgaan af uit dossier als geen positional argument gegeven
        if not gemeente:
            gemeente = config.get("orgaan") or config.get("gemeente")
            if not gemeente:
                print(f"Fout: dossier '{dossier_naam}' heeft geen 'orgaan' veld.")
                sys.exit(1)

    docs_map = docs_map_override or (OUTPUT_BASIS / gemeente)
    alerts_map = docs_map / "alerts"

    # Per-dossier staatbestand zodat meerdere dossiers dezelfde PDF-map kunnen analyseren
    if dossier_naam:
        staat_bestand = docs_map / "logs" / f"analyse-staat-{dossier_naam}.json"
        # Migreer legacy staatbestand als het per-dossier bestand nog niet bestaat
        legacy = docs_map / "logs" / "analyse-staat.json"
        if not staat_bestand.exists() and legacy.exists():
            import shutil
            shutil.copy(legacy, staat_bestand)
    else:
        staat_bestand = docs_map / "logs" / "analyse-staat.json"

    log_bestand = docs_map / "logs" / "analyse.log"

    setup_logging(log_bestand)

    log("=" * 55)
    log(f"Start analyse — {gemeente.capitalize()}  {'(DROOG)' if droog else ''}")
    log(f"Dossier: {DOSSIER_LABEL}")
    log(f"Documenten: {docs_map}")
    log("=" * 55)

    if not docs_map.exists():
        log(f"FOUT: map niet gevonden: {docs_map}")
        log("Zorg dat de scraper al heeft gedraaid voor deze gemeente.")
        sys.exit(1)

    geanalyseerd = laad_staat(staat_bestand)
    nieuwe_pdfs = vind_nieuwe_pdfs(docs_map, geanalyseerd)
    log(f"Nieuwe PDF's te analyseren: {len(nieuwe_pdfs)}")

    hits = []

    for pdf_pad in nieuwe_pdfs:
        log(f"  Verwerk: {pdf_pad.relative_to(docs_map)}")
        tekst = extraheer_tekst(pdf_pad)

        geanalyseerd.add(str(pdf_pad))

        if not tekst:
            continue

        gevonden = bevat_trefwoorden(tekst)
        if not gevonden:
            log(f"    Geen trefwoorden — overgeslagen")
            continue

        log(f"    Trefwoorden: {gevonden} — fragmenten extraheren")
        fragmenten = extraheer_fragmenten(tekst, gevonden)

        hits.append({
            "bestand": str(pdf_pad.relative_to(docs_map)),
            "trefwoorden": gevonden,
            "fragmenten": fragmenten,
        })
        log(f"    HIT — toegevoegd aan rapport")

    if not droog:
        sla_staat_op(staat_bestand, geanalyseerd)

    if hits:
        schrijf_rapport(alerts_map, gemeente, hits, droog)
        if MACOS_MELDING and not droog:
            stuur_macos_melding(
                f"Alert {gemeente.capitalize()} — {DOSSIER_LABEL}",
                f"{len(hits)} document(en) gevonden — zie alerts/"
            )
        log(f"\n✓ {len(hits)} hit(s) gevonden.")
    else:
        log("Geen relevante nieuwe documenten gevonden.")

    log("─" * 55)


if __name__ == "__main__":
    main()
