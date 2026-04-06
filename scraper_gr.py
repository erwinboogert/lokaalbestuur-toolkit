"""
Scraper voor vergaderstukken van gemeenschappelijke regelingen (GRs)
Bron: Open Raadsinformatie API (openraadsinformatie.nl)

Gemeenschappelijke regelingen zijn samenwerkingsverbanden tussen gemeenten:
veiligheidsregio's, sociale diensten, omgevingsdiensten, jeugdhulpregio's.
Ze vergaderen openbaar maar worden nauwelijks journalistiek gevolgd.

GRs die via Notubiz of iBabs publiceren zijn vindbaar in de ORI API
(ori_-prefix), met hetzelfde datamodel als gemeentelijke raadsstukken.

Gebruik:
    python3 scraper_gr.py drechtsteden           # download vergaderstukken
    python3 scraper_gr.py drechtsteden --droog   # toon wat er gedownload zou worden
    python3 scraper_gr.py --lijst                # toon geconfigureerde GRs
    python3 scraper_gr.py --lijst-ori            # ontdek GR-achtige indices in ORI

Configuratie: bronnen/regelingen.json
Output: ~/Documents/notulen/regelingen/<naam>/

Vergadertypen worden geladen uit bronnen/regelingen.json.
Vereisten: geen externe bibliotheken (alleen standaard Python 3)
"""

import sys
import json
import urllib.request
import re
import logging
from pathlib import Path

# ══════════════════════════════════════════════════════════════════════════════
# CONFIGURATIE
# ══════════════════════════════════════════════════════════════════════════════

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
BRONNEN_MAP = _toolkit_map / "bronnen"

# Standaard vergadertypen voor GRs
VERGADERTYPEN = {
    "algemeen bestuur":           True,
    "dagelijks bestuur":          True,
    "portefeuillehoudersoverleg": True,
}

SKIP_VERVALLEN = True
MAX_VERGADERINGEN = 50

# Trefwoorden om GR-achtige ORI-indices te herkennen (voor --lijst-ori)
GR_TREFWOORDEN = [
    "regio", "veiligheid", "omgevingsdienst", "jeugd",
    "dienst", "samenwerking", "werkvoorzieningschap",
    "gemeenschappelijk", "gr_", "ggd", "milieu",
]

# ══════════════════════════════════════════════════════════════════════════════

API_BASE = "https://api.openraadsinformatie.nl/v1/elastic"
DROOG = "--droog" in sys.argv


def setup(naam: str):
    output_map = OUTPUT_BASIS / "regelingen" / naam
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


def find_index(naam: str) -> str | None:
    """Zoek de meest recente ORI-index voor de opgegeven GR.

    Probeert eerst de ori_index uit regelingen.json. Valt daarna terug
    op directe naammatching (voor GRs die nog niet in regelingen.json staan).
    """
    indices = alle_indices()

    # Stap 1: opzoeken via regelingen.json
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

    # Stap 2: directe naammatching als fallback
    prefix = f"ori_{naam.lower().replace(' ', '_').replace('-', '_')}_"
    matches = sorted(i for i in indices if i.startswith(prefix))
    return matches[-1] if matches else None


def laad_regeling_config(naam: str) -> None:
    """Laad vergadertypen uit regelingen.json voor de opgegeven GR."""
    global VERGADERTYPEN
    pad = BRONNEN_MAP / "regelingen.json"
    if not pad.exists():
        return
    try:
        config = json.loads(pad.read_text(encoding="utf-8"))
        if naam in config and "vergadertypen" in config[naam]:
            VERGADERTYPEN = {vtype: True for vtype in config[naam]["vergadertypen"]}
    except Exception:
        pass


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
        ori = data.get("ori_index", "?")
        print(f"  {slug:<28} {naam}  (ori: {ori})")
    print()


def lijst_ori_gr():
    """Toon beschikbare ORI-indices zodat de gebruiker kan controleren of zijn GR erin staat."""
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
    return output_map / veilige_naam(vergadering["naam"]) / vergadering["datum"]


# ── Download ──────────────────────────────────────────────────────────────────

def download(url: str, bestemming: Path) -> int:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=60) as r:
        data = r.read()
    bestemming.write_bytes(data)
    return len(data)


# ── Hoofdprogramma ────────────────────────────────────────────────────────────

def main():
    args = sys.argv[1:]
    vlaggen = {a for a in args if a.startswith("--")}
    args = [a for a in args if not a.startswith("--")]

    if "--lijst-ori" in vlaggen:
        lijst_ori_gr()
        return

    if "--lijst" in vlaggen or not args:
        lijst_regelingen()
        if not args:
            print(__doc__)
        return

    naam = args[0].lower()
    if not re.match(r'^[a-z0-9][a-z0-9\-\ ]{0,60}$', naam):
        print(f"Ongeldige naam: '{naam}'. Gebruik alleen letters, cijfers en koppeltekens.")
        sys.exit(1)

    laad_regeling_config(naam)
    output_map = setup(naam)

    log("=" * 60)
    log(f"GR: {naam}  {'(DROOG)' if DROOG else ''}")
    log("=" * 60)

    index = find_index(naam)
    if not index:
        log(f"FOUT: geen ORI-index gevonden voor '{naam}'.")
        log("Gebruik --lijst-ori om beschikbare GRs te ontdekken.")
        log("Voeg de GR toe via: python3 toolkit.py nieuwe-regeling")
        sys.exit(1)
    log(f"Index: {index}")

    vergaderingen = haal_vergaderingen(index)
    log(f"{len(vergaderingen)} vergaderingen gevonden")

    if not vergaderingen:
        log("Geen vergaderingen gevonden met de geconfigureerde vergadertypen.")
        log(f"Actieve types: {', '.join(k for k, v in VERGADERTYPEN.items() if v)}")

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
