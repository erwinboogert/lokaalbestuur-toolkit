"""
Zoekindex voor raadsstukken — bouw en doorzoek een lokale full-text index

Gebruik:
    python3 index.py rotterdam                    # bouw/update de index
    python3 index.py rotterdam "woningbouw"       # zoek in de index
    python3 index.py rotterdam "grond OR woningbouw"
    python3 index.py rotterdam "woningbouw" --uitvoer   # exporteer naar Markdown
    python3 index.py rotterdam --status           # toon statistieken
    python3 index.py --dossier asielopvang "spreidingswet"

Zoeksyntaxis (SQLite FTS5):
    woord                  enkelvoudige term
    woord1 woord2          beide woorden
    woord1 OR woord2       een van beide
    "woord1 woord2"        exacte woordcombinatie
    woord1 NOT woord2      eerste maar niet tweede

De index staat in: ~/Documents/notulen/<orgaan>/index.db
Zoekresultaten in: ~/Documents/notulen/<orgaan>/zoekresultaten/

Vereisten: pdfplumber
"""

import json
import re
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

import pdfplumber

_toolkit_map = Path(__file__).parent
_config_pad = _toolkit_map / "config.local.json"
_data_map: Path | None = None
if _config_pad.exists():
    try:
        _cfg = json.loads(_config_pad.read_text(encoding="utf-8"))
        if "data_map" in _cfg:
            _data_map = Path(_cfg["data_map"]).expanduser()
    except Exception:
        pass

OUTPUT_BASIS = _data_map if _data_map else (Path.home() / "Documents" / "notulen")
_DOSSIERS_MAP = (_data_map / "dossiers") if _data_map else (_toolkit_map / "dossiers")


# ── Argumenten ────────────────────────────────────────────────────────────────

def parse_args():
    argv = sys.argv[1:]
    uitvoer = "--uitvoer" in argv
    status = "--status" in argv
    argv = [a for a in argv if a not in ("--uitvoer", "--status")]

    dossier_naam = None
    if "--dossier" in argv:
        idx = argv.index("--dossier")
        if idx + 1 < len(argv):
            dossier_naam = argv[idx + 1]
            argv = argv[:idx] + argv[idx + 2:]

    positional = [a for a in argv if not a.startswith("--")]
    orgaan = positional[0].lower() if len(positional) >= 1 else None
    zoekterm = positional[1] if len(positional) >= 2 else None

    return orgaan, zoekterm, dossier_naam, uitvoer, status


def laad_orgaan_uit_dossier(dossier_naam: str) -> str:
    pad = _DOSSIERS_MAP / f"{dossier_naam}.json"
    if not pad.exists():
        print(f"Dossier niet gevonden: {pad}")
        sys.exit(1)
    config = json.loads(pad.read_text(encoding="utf-8"))
    orgaan = config.get("orgaan") or config.get("gemeente")
    if not orgaan:
        print(f"Dossier '{dossier_naam}' heeft geen 'orgaan' veld.")
        sys.exit(1)
    return orgaan


# ── Database ──────────────────────────────────────────────────────────────────

def open_db(docs_map: Path) -> sqlite3.Connection:
    db_pad = docs_map / "index.db"
    con = sqlite3.connect(str(db_pad))
    con.execute("PRAGMA journal_mode=WAL")
    con.executescript("""
        CREATE TABLE IF NOT EXISTS geindexeerd (
            pad TEXT PRIMARY KEY,
            geindexeerd_op TEXT
        );

        CREATE VIRTUAL TABLE IF NOT EXISTS tekst_fts USING fts5(
            pad        UNINDEXED,
            datum      UNINDEXED,
            vergadertype UNINDEXED,
            bestandsnaam UNINDEXED,
            tekst,
            tokenize = 'unicode61'
        );
    """)
    con.commit()
    return con


# ── Hulpfuncties ──────────────────────────────────────────────────────────────

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


# ── Indexeren ─────────────────────────────────────────────────────────────────

def bouw_index(docs_map: Path, con: sqlite3.Connection):
    al_geindexeerd = {r[0] for r in con.execute("SELECT pad FROM geindexeerd")}
    pdfs = sorted(docs_map.rglob("*.pdf"))
    nieuw = [p for p in pdfs if str(p) not in al_geindexeerd]

    print(f"Index: {len(al_geindexeerd)} al geïndexeerd, {len(nieuw)} nieuw")

    if not nieuw:
        print("Index is actueel.")
        return

    nu = datetime.now().isoformat()
    toegevoegd = 0

    for pdf_pad in nieuw:
        tekst = extraheer_tekst(pdf_pad)
        if not tekst:
            con.execute("INSERT INTO geindexeerd VALUES (?, ?)", (str(pdf_pad), nu))
            continue

        datum = datum_uit_pad(pdf_pad)
        vergadertype = vergadertype_uit_pad(pdf_pad, docs_map)

        con.execute(
            "INSERT INTO tekst_fts (pad, datum, vergadertype, bestandsnaam, tekst) VALUES (?,?,?,?,?)",
            (str(pdf_pad), datum, vergadertype, pdf_pad.name, tekst)
        )
        con.execute("INSERT INTO geindexeerd VALUES (?, ?)", (str(pdf_pad), nu))
        toegevoegd += 1

        if toegevoegd % 25 == 0:
            con.commit()
            print(f"  {toegevoegd}/{len(nieuw)} geïndexeerd…")

    con.commit()
    print(f"Klaar — {toegevoegd} document(en) toegevoegd aan index.")


# ── Zoeken ────────────────────────────────────────────────────────────────────

def zoek(zoekterm: str, con: sqlite3.Connection) -> list[dict]:
    try:
        rijen = con.execute("""
            SELECT
                pad, datum, vergadertype, bestandsnaam,
                snippet(tekst_fts, 4, '**', '**', '…', 30)
            FROM tekst_fts
            WHERE tekst MATCH ?
            ORDER BY rank
        """, (zoekterm,)).fetchall()
    except sqlite3.OperationalError as e:
        print(f"Zoekfout: {e}")
        print("Controleer je zoeksyntaxis. Gebruik aanhalingstekens voor zinsdelen.")
        sys.exit(1)

    return [
        {"pad": r[0], "datum": r[1], "vergadertype": r[2],
         "bestandsnaam": r[3], "snippet": r[4]}
        for r in rijen
    ]


def druk_resultaten(hits: list[dict], zoekterm: str):
    print(f"\n{len(hits)} resultaat/resultaten voor '{zoekterm}'\n")
    print("─" * 55)

    huidig_jaar = None
    for hit in hits:
        jaar = hit["datum"][:4]
        if jaar != huidig_jaar:
            huidig_jaar = jaar
            print(f"\n  {jaar}")

        print(f"\n  {hit['datum']}  {hit['vergadertype']}")
        print(f"  {hit['bestandsnaam']}")
        print(f"\n  {hit['snippet']}\n")

    print("─" * 55)


def exporteer_markdown(hits: list[dict], zoekterm: str, docs_map: Path):
    datum_vandaag = datetime.now().strftime("%Y-%m-%d")
    regels = [
        f"# Zoekresultaten: '{zoekterm}'",
        f"",
        f"Gegenereerd op {datum_vandaag}. {len(hits)} resultaat/resultaten.",
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
            f"`{hit['bestandsnaam']}`",
            f"",
            f"> {hit['snippet']}",
            f"",
        ]

    uitvoer_map = docs_map / "zoekresultaten"
    uitvoer_map.mkdir(exist_ok=True)
    veilige_term = re.sub(r"[^\w]", "-", zoekterm.lower())[:40]
    pad = uitvoer_map / f"zoek-{veilige_term}-{datum_vandaag}.md"
    pad.write_text("\n".join(regels), encoding="utf-8")
    print(f"Opgeslagen: {pad}")


# ── Status ────────────────────────────────────────────────────────────────────

def toon_status(docs_map: Path, con: sqlite3.Connection):
    n_geindexeerd = con.execute("SELECT COUNT(*) FROM geindexeerd").fetchone()[0]
    n_tekst = con.execute("SELECT COUNT(*) FROM tekst_fts").fetchone()[0]
    laatste = con.execute(
        "SELECT MAX(geindexeerd_op) FROM geindexeerd"
    ).fetchone()[0] or "—"

    db_grootte = (docs_map / "index.db").stat().st_size / 1024 / 1024

    print(f"\nIndex — {docs_map.name}")
    print("─" * 40)
    print(f"  Bestanden verwerkt : {n_geindexeerd}")
    print(f"  Geïndexeerd (tekst): {n_tekst}")
    print(f"  Laatste update     : {laatste[:16]}")
    print(f"  Databasegrootte    : {db_grootte:.1f} MB")
    print("─" * 40)


# ── Hoofdprogramma ────────────────────────────────────────────────────────────

def main():
    orgaan, zoekterm, dossier_naam, uitvoer, status = parse_args()

    if dossier_naam and not orgaan:
        orgaan = laad_orgaan_uit_dossier(dossier_naam)

    if not orgaan:
        print(__doc__)
        sys.exit(0)

    docs_map = OUTPUT_BASIS / orgaan
    if not docs_map.exists():
        # Probeer ook submappen voor regelingen, waterschappen en veiligheidsregio's
        for submap in ("regelingen", "waterschappen", "veiligheidsregios"):
            kandidaat = OUTPUT_BASIS / submap / orgaan
            if kandidaat.exists():
                docs_map = kandidaat
                break
        else:
            print(f"Archiefmap niet gevonden: {docs_map}")
            print("Zorg dat de scraper al heeft gedraaid voor dit orgaan.")
            sys.exit(1)

    con = open_db(docs_map)

    if status:
        toon_status(docs_map, con)
        return

    if not zoekterm:
        # Geen zoekterm: index bijwerken
        bouw_index(docs_map, con)
        return

    # Zoekterm opgegeven: eerst index bijwerken, dan zoeken
    bouw_index(docs_map, con)
    hits = zoek(zoekterm, con)

    if not hits:
        print(f"\nGeen resultaten voor '{zoekterm}'.")
        return

    druk_resultaten(hits, zoekterm)

    if uitvoer:
        exporteer_markdown(hits, zoekterm, docs_map)


if __name__ == "__main__":
    main()

