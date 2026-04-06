"""
Tijdlijn-reconstructie van raadsstukken op basis van een zoekterm

Doorzoekt het archief van een orgaan en exporteert alle treffers
chronologisch als Markdown-tijdlijn. Handig voor het reconstrueren
van hoe een dossier zich door de tijd heeft ontwikkeld.

Gebruik:
    python3 tijdlijn.py rotterdam "woningbouw"
    python3 tijdlijn.py --dossier asielopvang "spreidingswet"
    python3 tijdlijn.py rotterdam "grond" --droog

De tijdlijn wordt opgeslagen in:
    ~/Documents/notulen/<orgaan>/tijdlijnen/tijdlijn-<term>-<datum>.md

Vereisten: pdfplumber
"""

import json
import re
import sys
from datetime import datetime
from pathlib import Path

import pdfplumber

OUTPUT_BASIS = Path.home() / "Documents" / "notulen"
CONTEXT_GROOTTE = 250
MAX_FRAGMENTEN_PER_DOC = 2


# ── Argumenten ────────────────────────────────────────────────────────────────

def parse_args():
    argv = sys.argv[1:]
    droog = "--droog" in argv
    argv = [a for a in argv if a != "--droog"]

    dossier_naam = None
    if "--dossier" in argv:
        idx = argv.index("--dossier")
        if idx + 1 < len(argv):
            dossier_naam = argv[idx + 1]
            argv = argv[:idx] + argv[idx + 2:]
        else:
            print("Gebruik: --dossier <naam>")
            sys.exit(1)

    positional = [a for a in argv if not a.startswith("--")]

    orgaan = positional[0].lower() if len(positional) >= 1 else None
    zoekterm = positional[1] if len(positional) >= 2 else None

    return orgaan, zoekterm, dossier_naam, droog


# ── Dossier laden ─────────────────────────────────────────────────────────────

def laad_orgaan_uit_dossier(dossier_naam: str) -> str:
    pad = Path(__file__).parent / "dossiers" / f"{dossier_naam}.json"
    if not pad.exists():
        print(f"Dossier niet gevonden: {pad}")
        sys.exit(1)
    config = json.loads(pad.read_text(encoding="utf-8"))
    orgaan = config.get("orgaan") or config.get("gemeente")
    if not orgaan:
        print(f"Dossier '{dossier_naam}' heeft geen 'orgaan' veld.")
        sys.exit(1)
    return orgaan


# ── Tekstextractie ────────────────────────────────────────────────────────────

def extraheer_tekst(pdf_pad: Path) -> str:
    try:
        with pdfplumber.open(str(pdf_pad)) as pdf:
            return "\n".join(p.extract_text() or "" for p in pdf.pages).strip()
    except Exception:
        return ""


# ── Datum uit pad ─────────────────────────────────────────────────────────────

def datum_uit_pad(pdf_pad: Path) -> str:
    """Extraheer datum uit mapstructuur: .../vergadertype/YYYY-MM-DD/bestand.pdf"""
    datum = pdf_pad.parent.name
    if re.match(r"\d{4}-\d{2}-\d{2}", datum):
        return datum
    return "0000-00-00"


def vergadertype_uit_pad(pdf_pad: Path, docs_map: Path) -> str:
    try:
        return pdf_pad.relative_to(docs_map).parts[0]
    except Exception:
        return "onbekend"


# ── Fragmenten ────────────────────────────────────────────────────────────────

def zoek_fragmenten(tekst: str, zoekterm: str) -> list[str]:
    tekst_lower = tekst.lower()
    term_lower = zoekterm.lower()
    fragmenten = []
    gezien = set()
    pos = 0

    while len(fragmenten) < MAX_FRAGMENTEN_PER_DOC:
        idx = tekst_lower.find(term_lower, pos)
        if idx == -1:
            break
        start = max(0, idx - CONTEXT_GROOTTE)
        eind = min(len(tekst), idx + len(zoekterm) + CONTEXT_GROOTTE)
        sleutel = start // (CONTEXT_GROOTTE * 2)
        if sleutel not in gezien:
            gezien.add(sleutel)
            fragment = tekst[start:eind].strip()
            fragment = re.sub(
                re.escape(zoekterm), f"**{zoekterm}**", fragment, flags=re.IGNORECASE
            )
            fragmenten.append(f"> …{fragment}…")
        pos = idx + 1

    return fragmenten


# ── Hoofdprogramma ────────────────────────────────────────────────────────────

def main():
    orgaan, zoekterm, dossier_naam, droog = parse_args()

    if dossier_naam and not orgaan:
        orgaan = laad_orgaan_uit_dossier(dossier_naam)

    if not orgaan or not zoekterm:
        print(__doc__)
        sys.exit(0)

    docs_map = OUTPUT_BASIS / orgaan
    if not docs_map.exists():
        print(f"Archiefmap niet gevonden: {docs_map}")
        print("Zorg dat de scraper al heeft gedraaid voor dit orgaan.")
        sys.exit(1)

    print(f"\nTijdlijn — {orgaan.capitalize()} — '{zoekterm}'")
    print("─" * 55)

    pdfs = sorted(docs_map.rglob("*.pdf"))
    print(f"{len(pdfs)} PDF's doorzoeken...\n")

    hits = []

    for pdf_pad in pdfs:
        tekst = extraheer_tekst(pdf_pad)
        if not tekst:
            continue
        if zoekterm.lower() not in tekst.lower():
            continue

        fragmenten = zoek_fragmenten(tekst, zoekterm)
        if not fragmenten:
            continue

        hits.append({
            "datum": datum_uit_pad(pdf_pad),
            "vergadertype": vergadertype_uit_pad(pdf_pad, docs_map),
            "bestand": pdf_pad.name,
            "fragmenten": fragmenten,
        })

    hits.sort(key=lambda h: h["datum"])

    print(f"{len(hits)} document(en) met treffers gevonden.\n")

    if not hits:
        print("Geen treffers — probeer een andere zoekterm.")
        return

    # ── Markdown opbouwen ─────────────────────────────────────────────────────

    datum_vandaag = datetime.now().strftime("%Y-%m-%d")
    regels = [
        f"# Tijdlijn: '{zoekterm}' — {orgaan.capitalize()}",
        f"",
        f"Gegenereerd op {datum_vandaag}. {len(hits)} document(en) met treffers, chronologisch gesorteerd.",
        f"",
    ]

    huidig_jaar = None
    for hit in hits:
        jaar = hit["datum"][:4]
        if jaar != huidig_jaar:
            huidig_jaar = jaar
            regels += [f"", f"## {jaar}", f""]

        regels += [
            f"### {hit['datum']} — {hit['vergadertype']}",
            f"",
            f"`{hit['bestand']}`",
            f"",
        ]
        for fragment in hit["fragmenten"]:
            regels += [fragment, f""]

    # ── Opslaan of droog tonen ────────────────────────────────────────────────

    if droog:
        print("\n".join(regels[:40]))
        print("\n[DROOG — niet opgeslagen]")
        return

    tijdlijn_map = docs_map / "tijdlijnen"
    tijdlijn_map.mkdir(exist_ok=True)
    veilige_term = re.sub(r"[^\w]", "-", zoekterm.lower())[:40]
    uitvoer_pad = tijdlijn_map / f"tijdlijn-{veilige_term}-{datum_vandaag}.md"
    uitvoer_pad.write_text("\n".join(regels), encoding="utf-8")

    print(f"Tijdlijn opgeslagen: {uitvoer_pad}")
    print("─" * 55)


if __name__ == "__main__":
    main()
