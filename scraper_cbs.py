"""
CBS iv3-scraper — haalt gemeentefinanciën op uit CBS dataderden.cbs.nl
Bron: Onbewerkte iv3-data per gemeente (jaarrekening)

Gebruik:
    python3 scraper_cbs.py rotterdam              # laatste 3 beschikbare jaren
    python3 scraper_cbs.py rotterdam 2022         # specifiek jaar
    python3 scraper_cbs.py rotterdam 2021 2022    # meerdere jaren
    python3 scraper_cbs.py rotterdam --droog      # toon wat opgehaald zou worden
    python3 scraper_cbs.py --lijst                # toon geconfigureerde gemeenten

Werking:
    1. Zoek CBS-gemeentecode op (GM0599 voor Rotterdam) via bronnen/gemeentecodes.json
    2. Zoek dataset-ID op voor het gevraagde jaar via bronnen/iv3datasets.json
    3. Haal jaarrekening-records op via CBS OData API (dataderden.cbs.nl)
    4. Sla op als CSV in ~/Documents/notulen/<gemeente>/financien/iv3_<jaar>.csv

Eenheid: bedragen in 1.000 euro (vermenigvuldig met 1000 voor werkelijk bedrag)
Verslagsoort: jaarrekening (meest recente correctie, 2e plaatsing)

Vereisten: geen externe bibliotheken (alleen standaard Python 3)
"""

import csv
import json
import logging
import sys
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path

# ── Configuratie ──────────────────────────────────────────────────────────────

_toolkit_map = Path(__file__).parent
_config_pad = _toolkit_map / "config.local.json"
_data_map = None
if _config_pad.exists():
    try:
        _cfg = json.loads(_config_pad.read_text(encoding="utf-8"))
        if "data_map" in _cfg:
            _data_map = Path(_cfg["data_map"]).expanduser()
    except Exception:
        pass

OUTPUT_BASIS = _data_map if _data_map else (Path.home() / "Documents" / "notulen")
BRONNEN_MAP = _toolkit_map / "bronnen"
CBS_BASE = "https://dataderden.cbs.nl/ODataApi/OData"

# ── Logging ───────────────────────────────────────────────────────────────────

def setup_logging(orgaan: str) -> logging.Logger:
    log_map = OUTPUT_BASIS / orgaan / "logs"
    log_map.mkdir(parents=True, exist_ok=True)
    log_pad = log_map / "cbs.log"

    logger = logging.getLogger("scraper_cbs")
    logger.setLevel(logging.INFO)
    if logger.handlers:
        return logger

    fmt = logging.Formatter("%(asctime)s  %(levelname)-7s  %(message)s", "%Y-%m-%d %H:%M:%S")
    sh = logging.StreamHandler()
    sh.setFormatter(fmt)
    fh = logging.FileHandler(log_pad, encoding="utf-8")
    fh.setFormatter(fmt)
    logger.addHandler(sh)
    logger.addHandler(fh)
    return logger

# ── Configuratiebestanden laden ───────────────────────────────────────────────

def laad_gemeentecodes() -> dict:
    pad = BRONNEN_MAP / "gemeentecodes.json"
    if not pad.exists():
        print(f"Fout: {pad} niet gevonden")
        sys.exit(1)
    data = json.loads(pad.read_text(encoding="utf-8"))
    return {k: v for k, v in data.items() if not k.startswith("_")}


def laad_iv3datasets() -> dict:
    pad = BRONNEN_MAP / "iv3datasets.json"
    if not pad.exists():
        print(f"Fout: {pad} niet gevonden")
        sys.exit(1)
    data = json.loads(pad.read_text(encoding="utf-8"))
    return {k: v for k, v in data.items() if not k.startswith("_")}

# ── CBS API ───────────────────────────────────────────────────────────────────

def cbs_get(url: str) -> dict:
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def haal_records(dataset_id: str, gm_code: str, jaar: int, logger: logging.Logger) -> list:
    """Haal alle jaarrekening-records op voor één gemeente en één jaar."""
    filter_str = (
        f"startswith(Gemeenten,'{gm_code}') and "
        f"startswith(Verslagsoort,'{jaar}X005')"
    )
    basis_url = (
        f"{CBS_BASE}/{dataset_id}/TypedDataSet"
        f"?$filter={urllib.parse.quote(filter_str)}"
        f"&$top=10000&$format=json"
    )

    records = []
    url = basis_url
    pagina = 1

    while url:
        logger.info(f"  Pagina {pagina} ophalen…")
        data = cbs_get(url)
        batch = data.get("value", [])
        records.extend(batch)

        next_link = data.get("odata.nextLink") or data.get("@odata.nextLink")
        url = next_link if next_link else None
        pagina += 1

    return records

# ── CSV opslaan ───────────────────────────────────────────────────────────────

def sla_op(records: list, orgaan: str, jaar: int, droog: bool, logger: logging.Logger):
    financien_map = OUTPUT_BASIS / orgaan / "financien"
    pad = financien_map / f"iv3_{jaar}.csv"

    if droog:
        logger.info(f"[droog] {len(records)} records — zou opslaan als: {pad}")
        return

    financien_map.mkdir(parents=True, exist_ok=True)

    with pad.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "gemeente",
            "jaar",
            "taakveld_balanspost",
            "categorie",
            "verslagsoort",
            "eerste_plaatsing_1000_euro",
            "tweede_plaatsing_1000_euro",
        ])
        for r in records:
            writer.writerow([
                orgaan,
                jaar,
                r.get("TaakveldBalanspost", "").strip(),
                r.get("Categorie", "").strip(),
                r.get("Verslagsoort", "").strip(),
                r.get("k_1ePlaatsing_1"),
                r.get("k_2ePlaatsing_2"),
            ])

    logger.info(f"✓ Opgeslagen: {pad}  ({len(records)} regels)")

# ── Hoofdprogramma ────────────────────────────────────────────────────────────

def main():
    args = sys.argv[1:]
    droog = "--droog" in args
    args = [a for a in args if a != "--droog"]

    gemeentecodes = laad_gemeentecodes()
    iv3datasets = laad_iv3datasets()

    if "--lijst" in args or args == []:
        if "--lijst" in args or not args:
            print("\nGeconfigureerde gemeenten (bronnen/gemeentecodes.json):\n")
            for slug, code in sorted(gemeentecodes.items()):
                print(f"  {slug:<22} {code}")
            print()
            if not args:
                print(__doc__)
            return

    orgaan = args[0].lower()
    jaren_arg = args[1:]

    if orgaan not in gemeentecodes:
        print(f"\nOnbekende gemeente: '{orgaan}'")
        print("Beschikbare gemeenten: python3 scraper_cbs.py --lijst")
        print("Ontbreekt? Voeg toe aan bronnen/gemeentecodes.json")
        sys.exit(1)

    gm_code = gemeentecodes[orgaan]
    logger = setup_logging(orgaan)

    # Bepaal jaren: opgegeven, of standaard laatste 3 jaar
    if jaren_arg:
        try:
            jaren = [int(j) for j in jaren_arg]
        except ValueError:
            print(f"Ongeldige jaren: {jaren_arg}")
            sys.exit(1)
    else:
        huidig = datetime.now().year
        jaren = [huidig - 1, huidig - 2, huidig - 3]

    logger.info(f"{'[droog] ' if droog else ''}Start: {orgaan} ({gm_code}) / jaren: {jaren}")

    for jaar in jaren:
        dataset_id = iv3datasets.get(str(jaar))
        if not dataset_id:
            logger.warning(f"Geen dataset bekend voor {jaar} — sla over (voeg toe aan bronnen/iv3datasets.json)")
            continue

        logger.info(f"Jaar {jaar} — dataset {dataset_id}")

        try:
            records = haal_records(dataset_id, gm_code, jaar, logger)
        except Exception as e:
            logger.error(f"Fout bij ophalen {jaar}: {e}")
            continue

        if not records:
            logger.warning(f"Geen jaarrekening-records voor {orgaan} / {jaar}")
            logger.warning(f"  Tip: controleer of de jaarrekening al is ingediend bij CBS")
            continue

        sla_op(records, orgaan, jaar, droog, logger)

    logger.info("Klaar.")


if __name__ == "__main__":
    main()
