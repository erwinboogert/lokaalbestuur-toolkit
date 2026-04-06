"""
Partijposities tracken in raadsstukken

Doorzoekt vergaderverslagen op een zoekterm en koppelt gevonden fragmenten
aan sprekers en fracties. Handig voor het reconstrueren welke partijen
welk standpunt innamen over een onderwerp.

Gebruik:
    python3 partijen.py rotterdam "woningbouw"
    python3 partijen.py --dossier asielopvang "spreidingswet"
    python3 partijen.py rotterdam "woningbouw" --uitvoer

Let op: de sprekerdetectie is heuristisch en werkt het best bij goed
opgemaakte vergaderverslagen. Gescande PDF's of afwijkende opmaak kunnen
leiden tot weinig of geen treffers. Controleer altijd de bronnen.

Vereisten: pdfplumber
"""

import json
import re
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path

import pdfplumber

OUTPUT_BASIS = Path.home() / "Documents" / "notulen"
CONTEXT_GROOTTE = 300

# Sprekerpatronen — gangbare Nederlandse vergadernotatie
# Volgorde: meest specifiek eerst
SPREKER_PATRONEN = [
    # De heer / Mevrouw Naam (Partij):
    re.compile(
        r'(?:De heer|de heer|Mevrouw|mevrouw|Dhr\.|dhr\.|Mw\.|mw\.)\s+'
        r'[A-ZÀ-Ÿ][a-zA-Zà-ÿ\- ]{1,30?}\s*'
        r'\(([^)\n]{2,25})\)\s*[:\n]',
        re.MULTILINE,
    ),
    # NAAM (Partij): — volledig hoofdletters
    re.compile(
        r'^[A-ZÀÁÂÄÆÇÈÉÊËÌÍÎÏÒÓÔÕÖÙÚÛÜ][A-ZÀÁÂÄÆÇÈÉÊËÌÍÎÏÒÓÔÕÖÙÚÛÜ \-]{1,30}'
        r'\s*\(([^)\n]{2,25})\)\s*[:\n]',
        re.MULTILINE,
    ),
]

# Bekende partijafkortingen voor aanvullende detectie
PARTIJ_NAMEN = re.compile(
    r'\b(VVD|PvdA|D66|GroenLinks|GL|SP|CDA|ChristenUnie|CU|SGP|PVV|'
    r'BBB|Volt|JA21|FvD|50PLUS|OSF|PvdD|DENK|Lijst\s+\w+|'
    r'Lokaal\s+\w+|Fractie\s+\w+)\b'
)


# ── Argumenten ────────────────────────────────────────────────────────────────

def parse_args():
    argv = sys.argv[1:]
    uitvoer = "--uitvoer" in argv
    argv = [a for a in argv if a != "--uitvoer"]

    dossier_naam = None
    if "--dossier" in argv:
        idx = argv.index("--dossier")
        if idx + 1 < len(argv):
            dossier_naam = argv[idx + 1]
            argv = argv[:idx] + argv[idx + 2:]

    positional = [a for a in argv if not a.startswith("--")]
    orgaan = positional[0].lower() if len(positional) >= 1 else None
    zoekterm = positional[1] if len(positional) >= 2 else None

    return orgaan, zoekterm, dossier_naam, uitvoer


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


def datum_uit_pad(pdf_pad: Path) -> str:
    datum = pdf_pad.parent.name
    return datum if re.match(r"\d{4}-\d{2}-\d{2}", datum) else "0000-00-00"


def vergadertype_uit_pad(pdf_pad: Path, docs_map: Path) -> str:
    try:
        return pdf_pad.relative_to(docs_map).parts[0]
    except Exception:
        return "onbekend"


# ── Sprekerdetectie ───────────────────────────────────────────────────────────

def vind_sprekerposities(tekst: str) -> list[tuple[int, str]]:
    """
    Geeft lijst van (positie_in_tekst, partijnaam) tuples,
    gesorteerd op positie.
    """
    gevonden = []

    for patroon in SPREKER_PATRONEN:
        for m in patroon.finditer(tekst):
            partij = m.group(1).strip()
            # Filter te lange of rommelige overeenkomsten
            if len(partij) > 25 or '\n' in partij:
                continue
            gevonden.append((m.start(), partij))

    # Sorteer op positie, verwijder duplicaten op dezelfde plek
    gevonden.sort(key=lambda x: x[0])
    return gevonden


def attribueer_fragment(tekst: str, positie: int, sprekers: list[tuple[int, str]]) -> str | None:
    """Geef de partij die het dichtst vóór positie aan het woord was."""
    partij = None
    for pos, naam in sprekers:
        if pos < positie:
            partij = naam
        else:
            break
    return partij


# ── Analyse ───────────────────────────────────────────────────────────────────

def analyseer_document(pdf_pad: Path, zoekterm: str, docs_map: Path) -> dict | None:
    """
    Analyseer één PDF: vind sprekers en koppel fragmenten met zoekterm aan partijen.
    Geeft None als het document geen treffers bevat.
    """
    tekst = extraheer_tekst(pdf_pad)
    if not tekst or zoekterm.lower() not in tekst.lower():
        return None

    sprekers = vind_sprekerposities(tekst)
    tekst_lower = tekst.lower()
    term_lower = zoekterm.lower()

    fragmenten_per_partij = defaultdict(list)
    n_treffers = 0
    pos = 0

    while True:
        idx = tekst_lower.find(term_lower, pos)
        if idx == -1:
            break

        n_treffers += 1
        start = max(0, idx - CONTEXT_GROOTTE)
        eind = min(len(tekst), idx + len(zoekterm) + CONTEXT_GROOTTE)
        fragment = tekst[start:eind].strip()
        fragment = re.sub(
            re.escape(zoekterm), f"**{zoekterm}**", fragment, flags=re.IGNORECASE
        )

        partij = attribueer_fragment(tekst, idx, sprekers)
        if partij:
            if len(fragmenten_per_partij[partij]) < 2:
                fragmenten_per_partij[partij].append(fragment)
        else:
            if len(fragmenten_per_partij["(geen spreker herkend)"]) < 1:
                fragmenten_per_partij["(geen spreker herkend)"].append(fragment)

        pos = idx + 1

    return {
        "datum": datum_uit_pad(pdf_pad),
        "vergadertype": vergadertype_uit_pad(pdf_pad, docs_map),
        "bestandsnaam": pdf_pad.name,
        "n_sprekers": len(sprekers),
        "n_treffers": n_treffers,
        "fragmenten": dict(fragmenten_per_partij),
    }


# ── Uitvoer ───────────────────────────────────────────────────────────────────

def bouw_rapport(resultaten: list[dict], zoekterm: str, orgaan: str) -> list[str]:
    """Bouw Markdown-rapport op, gegroepeerd per partij."""

    # Aggregeer per partij
    per_partij: dict[str, list[dict]] = defaultdict(list)
    totaal_sprekers = 0
    totaal_treffers = 0

    for doc in resultaten:
        totaal_sprekers += doc["n_sprekers"]
        totaal_treffers += doc["n_treffers"]
        for partij, fragmenten in doc["fragmenten"].items():
            for fragment in fragmenten:
                per_partij[partij].append({
                    "datum": doc["datum"],
                    "vergadertype": doc["vergadertype"],
                    "bestandsnaam": doc["bestandsnaam"],
                    "fragment": fragment,
                })

    datum_vandaag = datetime.now().strftime("%Y-%m-%d")
    regels = [
        f"# Partijposities: '{zoekterm}' — {orgaan.capitalize()}",
        f"",
        f"Gegenereerd op {datum_vandaag}.",
        f"{len(resultaten)} document(en) met treffers, "
        f"{totaal_treffers} treffer(s) totaal, "
        f"{totaal_sprekers} sprekerattributies herkend.",
        f"",
    ]

    if totaal_sprekers == 0:
        regels += [
            f"> **Waarschuwing:** geen sprekers herkend in deze documenten.",
            f"> De PDF-opmaak wijkt waarschijnlijk af van gangbare vergadernotatie.",
            f"> Controleer de bronbestanden handmatig.",
            f"",
        ]

    # Sorteer: echte partijen eerst, 'geen spreker herkend' laatst
    partijen_gesorteerd = sorted(
        per_partij.keys(),
        key=lambda p: (p.startswith("("), p.lower())
    )

    for partij in partijen_gesorteerd:
        items = sorted(per_partij[partij], key=lambda x: x["datum"])
        regels += [f"", f"## {partij}  ({len(items)} fragment(en))", f""]
        for item in items:
            regels += [
                f"**{item['datum']} — {item['vergadertype']}**  ",
                f"`{item['bestandsnaam']}`",
                f"",
                f"> …{item['fragment']}…",
                f"",
            ]

    return regels


# ── Hoofdprogramma ────────────────────────────────────────────────────────────

def main():
    orgaan, zoekterm, dossier_naam, uitvoer = parse_args()

    if dossier_naam and not orgaan:
        orgaan = laad_orgaan_uit_dossier(dossier_naam)

    if not orgaan or not zoekterm:
        print(__doc__)
        sys.exit(0)

    docs_map = OUTPUT_BASIS / orgaan
    if not docs_map.exists():
        print(f"Archiefmap niet gevonden: {docs_map}")
        sys.exit(1)

    print(f"\nPartijposities — {orgaan.capitalize()} — '{zoekterm}'")
    print("─" * 55)

    pdfs = sorted(docs_map.rglob("*.pdf"))
    print(f"{len(pdfs)} PDF's doorzoeken…\n")

    resultaten = []
    for pdf_pad in pdfs:
        doc = analyseer_document(pdf_pad, zoekterm, docs_map)
        if doc:
            resultaten.append(doc)

    print(f"{len(resultaten)} document(en) met treffers.")

    if not resultaten:
        print("Geen treffers gevonden.")
        return

    regels = bouw_rapport(resultaten, zoekterm, orgaan)

    # Toon samenvatting op scherm
    print()
    for regel in regels[:50]:
        print(regel)
    if len(regels) > 50:
        print(f"\n… ({len(regels) - 50} regels meer)")

    if uitvoer:
        uitvoer_map = docs_map / "partijposities"
        uitvoer_map.mkdir(exist_ok=True)
        datum_vandaag = datetime.now().strftime("%Y-%m-%d")
        veilige_term = re.sub(r"[^\w]", "-", zoekterm.lower())[:40]
        pad = uitvoer_map / f"partijen-{veilige_term}-{datum_vandaag}.md"
        pad.write_text("\n".join(regels), encoding="utf-8")
        print(f"\nOpgeslagen: {pad}")

    print("─" * 55)


if __name__ == "__main__":
    main()
