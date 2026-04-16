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

import sys
import json
import urllib.request
import xml.etree.ElementTree as ET
import re
import logging
from datetime import datetime, timedelta
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

# Standaard vergadertypen voor waterschappen.
# Waterschappen gebruiken uiteenlopende namen; deze trefwoorden dekken de meest
# voorkomende varianten (substring-match, hoofdletterongevoelig).
VERGADERTYPEN = {
    "algemeen bestuur":                    True,   # Aa en Maas, Zuiderzeeland (AB)
    "college van dijkgraaf en heemraden":  True,   # Zuiderzeeland, Aa en Maas
    "dagelijks bestuur":                   True,   # meerdere waterschappen
    "verenigde vergadering":               True,   # Delfland (VV), sommige hoogheemraadschappen
}

SKIP_VERVALLEN = True
MAX_VERGADERINGEN = 50

# ══════════════════════════════════════════════════════════════════════════════

API_BASE = "https://api.openraadsinformatie.nl/v1/elastic"
IBABS_ENDPOINT = "https://wcf.ibabs.eu/api/Public.svc"
IBABS_NS = "http://tempuri.org/"
IBABS_TERUGKIJK_DAGEN = 730  # ~2 jaar
DROOG = "--droog" in sys.argv


def setup(naam: str):
    output_map = OUTPUT_BASIS / "waterschappen" / naam
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
    """Zoek de meest recente ORI-index voor het opgegeven waterschap.

    Leest de ori_index uit waterschappen.json en zoekt de laatste
    tijdgestempelde index met de owi_-prefix.
    """
    indices = alle_indices()

    pad = BRONNEN_MAP / "waterschappen.json"
    if pad.exists():
        try:
            config = json.loads(pad.read_text(encoding="utf-8"))
            if naam in config and "ori_index" in config[naam]:
                ori_naam = config[naam]["ori_index"]
                prefix = f"owi_{ori_naam}_"
                matches = sorted(i for i in indices if i.startswith(prefix))
                if matches:
                    return matches[-1]
        except Exception:
            pass

    # Fallback: probeer de naam direct als owi_-prefix
    prefix = f"owi_{naam.lower().replace(' ', '_').replace('-', '_')}_"
    matches = sorted(i for i in indices if i.startswith(prefix))
    return matches[-1] if matches else None


def laad_waterschap_config(naam: str) -> None:
    """Laad vergadertypen uit waterschappen.json voor het opgegeven waterschap."""
    global VERGADERTYPEN
    pad = BRONNEN_MAP / "waterschappen.json"
    if not pad.exists():
        return
    try:
        config = json.loads(pad.read_text(encoding="utf-8"))
        if naam in config and "vergadertypen" in config[naam]:
            VERGADERTYPEN = {vtype: True for vtype in config[naam]["vergadertypen"]}
    except Exception:
        pass


def ibabs_naam_voor(naam: str) -> str | None:
    """Lees ibabs_naam uit waterschappen.json voor het opgegeven waterschap."""
    pad = BRONNEN_MAP / "waterschappen.json"
    if not pad.exists():
        return None
    try:
        config = json.loads(pad.read_text(encoding="utf-8"))
        return config.get(naam, {}).get("ibabs_naam")
    except Exception:
        return None


def ibabs_soap(methode: str, body_xml: str) -> ET.Element:
    """Doe een SOAP-verzoek naar de iBabs API en geef het root-element terug."""
    envelope = (
        '<?xml version="1.0" encoding="utf-8"?>'
        '<soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/"'
        ' xmlns:tns="http://tempuri.org/">'
        "<soap:Body>"
        f"<tns:{methode}>"
        f"{body_xml}"
        f"</tns:{methode}>"
        "</soap:Body>"
        "</soap:Envelope>"
    )
    req = urllib.request.Request(
        IBABS_ENDPOINT,
        data=envelope.encode("utf-8"),
        headers={
            "Content-Type": "text/xml; charset=utf-8",
            "SOAPAction": f'"http://tempuri.org/IPublic/{methode}"',
            "User-Agent": "Mozilla/5.0",
        },
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        return ET.fromstring(r.read())


def _ibabs_tekst(el: ET.Element, tag: str) -> str:
    """Haal tekst op van een direct child-element in de iBabs-namespace."""
    child = el.find(f"{{{IBABS_NS}}}{tag}")
    return (child.text or "").strip() if child is not None else ""


def haal_vergadertypen_ibabs(sitename: str) -> dict[str, str]:
    """Geeft {id: naam} voor alle vergadertypen van een iBabs-organisatie."""
    body = f"<tns:Sitename>{sitename}</tns:Sitename>"
    try:
        root = ibabs_soap("GetMeetingtypes", body)
        result = {}
        for mt in root.iter(f"{{{IBABS_NS}}}iBabsMeetingtype"):
            mt_id = _ibabs_tekst(mt, "Id")
            mt_naam = _ibabs_tekst(mt, "Name")
            if mt_id:
                result[mt_id] = mt_naam
        return result
    except Exception as e:
        log(f"  ! GetMeetingtypes mislukt: {e}")
        return {}


def haal_vergaderingen_ibabs(sitename: str) -> list[dict]:
    """Haal vergaderingen + documenten op via de iBabs SOAP API.

    Geeft [{id, naam, datum, documenten: [{naam, url}]}].
    """
    date_from = (datetime.now() - timedelta(days=IBABS_TERUGKIJK_DAGEN)).strftime("%Y-%m-%dT00:00:00")
    date_to = datetime.now().strftime("%Y-%m-%dT23:59:59")

    vergadertypen_map = haal_vergadertypen_ibabs(sitename)

    body = (
        f"<tns:Sitename>{sitename}</tns:Sitename>"
        f"<tns:StartDate>{date_from}</tns:StartDate>"
        f"<tns:EndDate>{date_to}</tns:EndDate>"
        "<tns:MetaDataOnly>false</tns:MetaDataOnly>"
    )
    root = ibabs_soap("GetMeetingsByDateRange", body)

    vergaderingen = []
    for meeting in root.iter(f"{{{IBABS_NS}}}iBabsMeeting"):
        mt_id = _ibabs_tekst(meeting, "MeetingtypeId")
        mt_naam = vergadertypen_map.get(mt_id, mt_id)

        if not wil_vergadering(mt_naam):
            continue

        meeting_id = _ibabs_tekst(meeting, "Id")
        datum_raw = _ibabs_tekst(meeting, "MeetingDate")
        datum = datum_raw[:10] if datum_raw else ""

        documenten = []
        for doc in meeting.iter(f"{{{IBABS_NS}}}iBabsDocument"):
            confidential = _ibabs_tekst(doc, "Confidential")
            if confidential == "true":
                continue
            url = _ibabs_tekst(doc, "PublicDownloadURL")
            if not url:
                continue
            bestandsnaam = _ibabs_tekst(doc, "FileName") or _ibabs_tekst(doc, "DisplayName")
            if not bestandsnaam:
                bestandsnaam = f"document-{_ibabs_tekst(doc, 'Id')}.pdf"
            if not bestandsnaam.lower().endswith(".pdf"):
                bestandsnaam += ".pdf"
            documenten.append({"naam": bestandsnaam, "url": url})

        vergaderingen.append({
            "id": meeting_id,
            "naam": mt_naam,
            "datum": datum,
            "documenten": documenten,
        })

    return vergaderingen


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

    # Dedupleer naar basisnamen
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
        # Toon de meest recente volledige indexnaam
        prefix = f"owi_{naam}_"
        recente = sorted(i for i in owi_indices if i.startswith(prefix))
        print(f"  {naam}")
        if recente:
            print(f"    → {recente[-1]}")
    print()
    print("  Gebruik de basisnaam (zonder 'owi_' en tijdstempel) als ori_index")
    print("  bij 'python3 toolkit.py nieuw-waterschap'.")
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

    laad_waterschap_config(naam)
    output_map = setup(naam)

    log("=" * 60)
    log(f"Waterschap: {naam}  {'(DROOG)' if DROOG else ''}")
    log("=" * 60)

    ibabs_naam = ibabs_naam_voor(naam)
    if ibabs_naam:
        log(f"Bron: iBabs ({ibabs_naam}.bestuurlijkeinformatie.nl)")
        vergaderingen = haal_vergaderingen_ibabs(ibabs_naam)
        log(f"{len(vergaderingen)} vergaderingen gevonden")
        if not vergaderingen:
            log("Geen vergaderingen gevonden met de geconfigureerde vergadertypen.")
            log(f"Actieve types: {', '.join(k for k, v in VERGADERTYPEN.items() if v)}")

        totaal_nieuw = totaal_overgeslagen = totaal_fout = 0

        for verg in vergaderingen:
            docs = verg["documenten"]
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
        return

    index = find_index(naam)
    if not index:
        log(f"FOUT: geen ORI-index gevonden voor '{naam}'.")
        log("Gebruik --lijst-ori om beschikbare waterschappen te ontdekken.")
        log("Voeg het waterschap toe via: python3 toolkit.py nieuw-waterschap")
        sys.exit(1)
    log(f"Bron: ORI-index {index}")

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
