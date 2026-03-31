"""
Scraper voor openbare raadsdocumenten van Nederlandse gemeenten
Bron: Open Raadsinformatie API (openraadsinformatie.nl)

Gebruik:
    python3 scraper.py arnhem                # download documenten van Arnhem
    python3 scraper.py amsterdam             # download documenten van Amsterdam
    python3 scraper.py arnhem --droog        # laat zien wat er nieuw is, download niets
    python3 scraper.py                       # toon lijst van beschikbare gemeenten

Vergadertypen worden automatisch geladen uit organen/<naam>.json als dat bestand aanwezig is.
Zonder orgaan-config worden de standaard vergadertypen gebruikt (zie CONFIGURATIE hieronder).

Vereisten: geen externe bibliotheken (alleen standaard Python 3)
"""

import sys
import json
import urllib.request
import re
import logging
from pathlib import Path

# ══════════════════════════════════════════════════════════════════════════════
# CONFIGURATIE — pas dit aan naar eigen wens
# ══════════════════════════════════════════════════════════════════════════════

# Bovenliggende map voor alle downloads
# Per gemeente wordt hier een submap aangemaakt, bijv. ~/Documents/notulen/arnhem/
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
_ORGANEN_MAP = (_data_map / "organen") if _data_map else (_toolkit_map / "organen")

# Welke vergadertypen wil je downloaden? True = ja, False = nee
VERGADERTYPEN = {
    "gemeenteraad":         True,
    "commissie":            True,
    "raadsbrede commissie": True,
}

# Vergaderingen met 'VERVALLEN' in de naam overslaan?
SKIP_VERVALLEN = True

# Hoeveel vergaderingen terugkijken per run?
MAX_VERGADERINGEN = 50

# ══════════════════════════════════════════════════════════════════════════════

API_BASE = "https://api.openraadsinformatie.nl/v1/elastic"
DROOG = "--droog" in sys.argv


def setup(gemeente: str):
    output_map = OUTPUT_BASIS / gemeente
    log_map = output_map / "logs"
    log_map.mkdir(parents=True, exist_ok=True)
    logbestand = log_map / "scraper.log"

    handlers = [logging.StreamHandler(sys.stdout),
                logging.FileHandler(logbestand, encoding="utf-8")]
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s  %(message)s",
        datefmt="%Y-%m-%d %H:%M",
        handlers=handlers,
    )
    return output_map


def log(msg):
    logging.info(msg)


# ── API ───────────────────────────────────────────────────────────────────────

def api_search(index: str, query: dict) -> list:
    url = f"{API_BASE}/{index}/_search"
    data = json.dumps(query).encode()
    req = urllib.request.Request(
        url, data=data,
        headers={"Content-Type": "application/json", "Accept": "application/json"}
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read()).get("hits", {}).get("hits", [])


def alle_indices() -> list[str]:
    req = urllib.request.Request(
        f"{API_BASE}/_cat/indices?h=index&format=json",
        headers={"Accept": "application/json"}
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        return [row["index"] for row in json.loads(r.read())]


def find_index(gemeente: str) -> str:
    """Zoek de meest recente index voor de opgegeven gemeente."""
    prefix = f"ori_{gemeente.lower().replace(' ', '_').replace('-', '_')}_"
    matches = sorted([i for i in alle_indices() if i.startswith(prefix)])
    if not matches:
        return None
    return matches[-1]


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


# ── Vergaderingen ─────────────────────────────────────────────────────────────

def wil_vergadering(naam: str) -> bool:
    naam_lower = naam.lower()
    if SKIP_VERVALLEN and "vervallen" in naam_lower:
        return False
    for sleutel, actief in VERGADERTYPEN.items():
        if actief and sleutel in naam_lower:
            return True
    return False


def haal_vergaderingen(index: str) -> list[dict]:
    hits = api_search(index, {
        "query": {"term": {"@type": "Meeting"}},
        "sort": [{"start_date": {"order": "desc"}}],
        "size": MAX_VERGADERINGEN,
        "_source": ["name", "start_date"],
    })
    return [
        {"id": h["_id"], "naam": h["_source"].get("name", ""), "datum": h["_source"].get("start_date", "")[:10]}
        for h in hits if wil_vergadering(h["_source"].get("name", ""))
    ]


# ── Documenten ────────────────────────────────────────────────────────────────

def haal_documenten(index: str, vergadering_id: str) -> list[dict]:
    agenda_hits = api_search(index, {
        "query": {"term": {"parent": vergadering_id}},
        "size": 100,
        "_source": ["attachment"],
    })
    attachment_ids = []
    for hit in agenda_hits:
        attachment_ids.extend(hit["_source"].get("attachment", []))
    if not attachment_ids:
        return []

    media_hits = api_search(index, {
        "query": {"ids": {"values": attachment_ids}},
        "size": 200,
        "_source": ["name", "url", "@type"],
    })
    return [
        {"naam": h["_source"].get("name", "").strip(), "url": h["_source"].get("url", "")}
        for h in media_hits
        if h["_source"].get("@type") == "MediaObject"
        and h["_source"].get("url")
        and h["_source"].get("name", "").strip()
    ]


# ── Bestandsnaam en mappenstructuur ───────────────────────────────────────────

def veilige_naam(tekst: str) -> str:
    tekst = tekst.lower()
    tekst = re.sub(r"[^\w\s-]", "", tekst)
    tekst = re.sub(r"\s+", "-", tekst.strip())
    tekst = re.sub(r"-+", "-", tekst)
    return tekst[:80]


def vergadering_map(output_map: Path, vergadering: dict) -> Path:
    naam = vergadering["naam"].lower()
    if "gemeenteraad" in naam:
        vtype = "gemeenteraad"
    elif "raadsbrede" in naam:
        vtype = "raadsbrede-commissie"
    elif "commissie" in naam:
        vtype = veilige_naam(vergadering["naam"])
    else:
        vtype = veilige_naam(vergadering["naam"])
    return output_map / vtype / vergadering["datum"]


# ── Download ──────────────────────────────────────────────────────────────────

def download(url: str, bestemming: Path) -> int:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=60) as r:
        data = r.read()
    bestemming.write_bytes(data)
    return len(data)


# ── Hoofdprogramma ────────────────────────────────────────────────────────────

def laad_orgaan_config(orgaan_naam: str) -> None:
    """Laad vergadertypen uit de geconfigureerde organen-map."""
    global VERGADERTYPEN
    pad = _ORGANEN_MAP / f"{orgaan_naam}.json"
    if not pad.exists():
        return
    config = json.loads(pad.read_text(encoding="utf-8"))
    if "vergadertypen" in config:
        VERGADERTYPEN = {vtype: True for vtype in config["vergadertypen"]}


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]

    if not args:
        print(__doc__)
        lijst_gemeenten()
        sys.exit(0)

    gemeente = args[0].lower()
    if not re.match(r'^[a-z0-9][a-z0-9\-\ ]{0,60}$', gemeente):
        print(f"Ongeldige gemeentenaam: '{gemeente}'. Gebruik alleen letters, cijfers en koppeltekens.")
        sys.exit(1)

    laad_orgaan_config(gemeente)

    output_map = setup(gemeente)

    log("=" * 60)
    log(f"Gemeente: {gemeente.capitalize()}  {'(DROOG)' if DROOG else ''}")
    log("=" * 60)

    index = find_index(gemeente)
    if not index:
        log(f"FOUT: geen index gevonden voor '{gemeente}'.")
        log("Voer het script uit zonder argument voor een lijst van beschikbare gemeenten.")
        sys.exit(1)
    log(f"Index: {index}")

    vergaderingen = haal_vergaderingen(index)
    log(f"{len(vergaderingen)} vergaderingen gevonden")

    totaal_nieuw = totaal_overgeslagen = totaal_fout = 0

    for verg in vergaderingen:
        docs = haal_documenten(index, verg["id"])
        if not docs:
            continue

        doelmap = vergadering_map(output_map, verg)
        nieuwe_docs = [d for d in docs
                       if not (doelmap / (veilige_naam(d["naam"]) + ".pdf")).exists()]

        if not nieuwe_docs:
            totaal_overgeslagen += len(docs)
            continue

        log(f"\n  {verg['naam']} ({verg['datum']}) — {len(nieuwe_docs)} nieuw van {len(docs)}")

        if not DROOG:
            doelmap.mkdir(parents=True, exist_ok=True)

        for doc in docs:
            bestandsnaam = veilige_naam(doc["naam"]) + ".pdf"
            bestemming = doelmap / bestandsnaam

            if bestemming.exists():
                totaal_overgeslagen += 1
                continue

            if DROOG:
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

    log("")
    log("─" * 60)
    log(f"Nieuw gedownload : {totaal_nieuw}")
    log(f"Al aanwezig      : {totaal_overgeslagen}")
    log(f"Fouten           : {totaal_fout}")
    log(f"Opgeslagen in    : {output_map}")
    log("─" * 60)


if __name__ == "__main__":
    main()
