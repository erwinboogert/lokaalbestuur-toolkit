"""
Gedeelde API-functies voor de lokaalbestuur-toolkit scrapers.

Bevat alle herbruikbare logica voor:
  - Open Raadsinformatie (ORI) API
  - Notubiz API
  - iBabs SOAP API
  - Bestandsnamen, downloads en logging
  - Configuratie (config.local.json)
"""

from __future__ import annotations

import json
import logging
import re
import subprocess
import sys
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from html import unescape as html_unescape
from pathlib import Path


# ── Configuratie ─────────────────────────────────────────────────────────────

TOOLKIT_MAP = Path(__file__).parent

_config_pad = TOOLKIT_MAP / "config.local.json"
_data_map: Path | None = None
if _config_pad.exists():
    try:
        _cfg = json.loads(_config_pad.read_text(encoding="utf-8"))
        if "data_map" in _cfg:
            _data_map = Path(_cfg["data_map"]).expanduser()
    except Exception:
        pass

DATA_MAP = _data_map  # None als geen config.local.json; anders het geconfigureerde pad
OUTPUT_BASIS = _data_map if _data_map else (Path.home() / "Documents" / "notulen")
BRONNEN_MAP = TOOLKIT_MAP / "bronnen"


# ── Logging ──────────────────────────────────────────────────────────────────

def setup_logging(output_map: Path):
    """Configureer logging naar stdout en een logbestand in output_map/logs/."""
    log_map = output_map / "logs"
    log_map.mkdir(parents=True, exist_ok=True)
    logbestand = log_map / "scraper.log"

    handlers = [
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(logbestand, encoding="utf-8"),
    ]
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s  %(message)s",
        datefmt="%Y-%m-%d %H:%M",
        handlers=handlers,
    )


def log(msg):
    logging.info(msg)


# ── Vergaderfilter ───────────────────────────────────────────────────────────

def wil_vergadering(naam: str, vergadertypen: dict[str, bool],
                    skip_vervallen: bool = True) -> bool:
    """Controleer of een vergadering gedownload moet worden op basis van type."""
    naam_lower = naam.lower()
    if skip_vervallen and "vervallen" in naam_lower:
        return False
    for sleutel, actief in vergadertypen.items():
        if actief and sleutel in naam_lower:
            return True
    return False


# ── Bestandsnaam en download ─────────────────────────────────────────────────

def veilige_naam(tekst: str) -> str:
    """Maak een veilige bestandsnaam van een willekeurige tekst."""
    tekst = tekst.lower()
    tekst = re.sub(r"[^\w\s-]", "", tekst)
    tekst = re.sub(r"\s+", "-", tekst.strip())
    tekst = re.sub(r"-+", "-", tekst)
    return tekst[:80]


def download(url: str, bestemming: Path) -> int:
    """Download een bestand en geef de grootte in bytes terug."""
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=60) as r:
        data = r.read()
    bestemming.write_bytes(data)
    return len(data)


# ── ORI API (Open Raadsinformatie) ───────────────────────────────────────────

API_BASE = "https://api.openraadsinformatie.nl/v1/elastic"


def api_search(index: str, query: dict) -> list:
    """Voer een Elasticsearch-zoekopdracht uit op een ORI-index."""
    url = f"{API_BASE}/{index}/_search"
    data = json.dumps(query).encode()
    req = urllib.request.Request(
        url, data=data,
        headers={"Content-Type": "application/json", "Accept": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read()).get("hits", {}).get("hits", [])


def alle_indices() -> list[str]:
    """Haal alle beschikbare ORI-indices op."""
    req = urllib.request.Request(
        f"{API_BASE}/_cat/indices?h=index&format=json",
        headers={"Accept": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        return [row["index"] for row in json.loads(r.read())]


def find_index(naam: str, prefix: str = "ori") -> str | None:
    """Zoek de meest recente ORI-index met het opgegeven prefix en naam."""
    indices = alle_indices()
    zoek = f"{prefix}_{naam.lower().replace(' ', '_').replace('-', '_')}_"
    matches = sorted(i for i in indices if i.startswith(zoek))
    return matches[-1] if matches else None


def haal_vergaderingen_ori(index: str, vergadertypen: dict[str, bool],
                           max_vergaderingen: int = 50,
                           vanaf: str | None = None) -> list[dict]:
    """Haal vergaderingen op uit een ORI-index. Geeft [{id, naam, datum}]."""
    if vanaf:
        query = {
            "bool": {
                "must": [
                    {"term": {"@type": "Meeting"}},
                    {"range": {"start_date": {"gte": vanaf + "T00:00:00Z"}}},
                ]
            }
        }
        size = 200
    else:
        query = {"term": {"@type": "Meeting"}}
        size = max_vergaderingen

    hits = api_search(index, {
        "query": query,
        "sort": [{"start_date": {"order": "desc"}}],
        "size": size,
        "_source": ["name", "start_date"],
    })
    return [
        {
            "id": h["_id"],
            "naam": h["_source"].get("name", ""),
            "datum": h["_source"].get("start_date", "")[:10],
        }
        for h in hits
        if wil_vergadering(h["_source"].get("name", ""), vergadertypen)
    ]


def haal_documenten_ori(index: str, vergadering_id: str) -> list[dict]:
    """Haal documenten op voor een ORI-vergadering. Geeft [{naam, url}]."""
    agenda_hits = api_search(index, {
        "query": {"term": {"parent": vergadering_id}},
        "size": 100,
        "_source": ["attachment"],
    })
    attachment_ids = []
    meeting_hits = api_search(index, {'query': {'ids': {'values': [vergadering_id]}}, '_source': ['attachment']})
    if meeting_hits:
        val = meeting_hits[0]['_source'].get('attachment', [])
        if val:
            attachment_ids.extend(val if isinstance(val, list) else [val])

    meeting_hits = api_search(index, {"query": {"ids": {"values": [vergadering_id]}}, "_source": ["attachment"]})
    if meeting_hits:
        val = meeting_hits[0]["_source"].get("attachment", [])
        attachment_ids.extend(val if isinstance(val, list) else [val])

    for hit in agenda_hits:
        val = hit["_source"].get("attachment", []); attachment_ids.extend(val if isinstance(val, list) else [val])
    if not attachment_ids:
        return []

    media_hits = api_search(index, {
        "query": {"ids": {"values": attachment_ids}},
        "size": 500,
        "_source": ["name", "url", "@type"],
    })
    return [
        {"naam": h["_source"].get("name", "").strip(), "url": h["_source"].get("url", "")}
        for h in media_hits
        if h["_source"].get("@type") == "MediaObject"
        and h["_source"].get("url")
        and h["_source"].get("name", "").strip()
    ]


# ── Notubiz API ──────────────────────────────────────────────────────────────

NOTUBIZ_API = "https://api.notubiz.nl"
NOTUBIZ_VERSION = "1.17.0"


def notubiz_verzoek(endpoint: str) -> dict:
    """Doe een GET-verzoek naar de Notubiz API en geef het JSON-resultaat terug."""
    sep = "&" if "?" in endpoint else "?"
    url = f"{NOTUBIZ_API}/{endpoint}{sep}format=json&version={NOTUBIZ_VERSION}"
    req = urllib.request.Request(
        url, headers={"Accept": "application/json", "User-Agent": "Mozilla/5.0"},
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read())


def haal_vergaderingen_notubiz(org_id: int, vergadertypen: dict[str, bool] | None = None,
                                terugkijk_dagen: int = 730) -> list[dict]:
    """Haal vergaderingen op via de Notubiz API. Geeft [{id, naam, datum}].

    Als vergadertypen None is, worden alle vergaderingen meegenomen.
    """
    date_to = datetime.now().strftime("%Y-%m-%d 23:59:59")
    date_from = (datetime.now() - timedelta(days=terugkijk_dagen)).strftime("%Y-%m-%d 00:00:00")

    vergaderingen = []
    page = 1
    while True:
        data = notubiz_verzoek(
            f"events?organisation_id={org_id}"
            f"&date_from={date_from.replace(' ', '+')}"
            f"&date_to={date_to.replace(' ', '+')}"
            f"&page={page}"
        )
        for event in data.get("events", []):
            if event.get("permission_group") != "public":
                continue
            if event.get("canceled") or event.get("inactive"):
                continue

            datum = ""
            for planning in event.get("plannings", []):
                datum = planning.get("start_date", "")[:10]
                if datum:
                    break
            if not datum:
                datum = event.get("creation_date", "")[:10]

            naam = ""
            for attr in event.get("attributes", []):
                naam = attr.get("value", "").strip()
                if naam:
                    break
            if not naam:
                naam = f"vergadering-{event['id']}"

            if vergadertypen is not None and not wil_vergadering(naam, vergadertypen):
                continue

            vergaderingen.append({
                "id": str(event["id"]),
                "naam": naam,
                "datum": datum,
            })

        if not data.get("pagination", {}).get("has_more_pages"):
            break
        page += 1

    return vergaderingen


def haal_documenten_notubiz(meeting_id: str) -> list[dict]:
    """Haal documenten op voor een Notubiz-vergadering. Geeft [{naam, url}]."""
    data = notubiz_verzoek(f"events/meetings/{meeting_id}")
    meeting = data.get("meeting", {})
    documenten = []

    def verwerk_doc(doc: dict):
        if doc.get("confidential"):
            return
        url = doc.get("url", "")
        if not url:
            return
        bestandsnaam = ""
        for versie in doc.get("versions", []):
            if versie.get("mime_type") == "application/pdf":
                bestandsnaam = versie.get("file_name", "")
                break
        if not bestandsnaam:
            bestandsnaam = doc.get("title", f"document-{doc.get('id', '')}")
            if not bestandsnaam.lower().endswith(".pdf"):
                bestandsnaam += ".pdf"
        documenten.append({"naam": bestandsnaam, "url": url})

    for doc in meeting.get("documents", []):
        verwerk_doc(doc)
    for item in meeting.get("agenda_items", []):
        for doc in item.get("documents", []):
            verwerk_doc(doc)

    return documenten


# ── iBabs SOAP API ───────────────────────────────────────────────────────────

IBABS_ENDPOINT = "https://wcf.ibabs.eu/api/Public.svc"
IBABS_NS = "http://tempuri.org/"


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


def ibabs_tekst(el: ET.Element, tag: str) -> str:
    """Haal tekst op van een child-element in de iBabs-namespace."""
    child = el.find(f"{{{IBABS_NS}}}{tag}")
    return (child.text or "").strip() if child is not None else ""


def haal_vergadertypen_ibabs(sitename: str) -> dict[str, str]:
    """Geeft {id: naam} voor alle vergadertypen van een iBabs-organisatie."""
    body = f"<tns:Sitename>{sitename}</tns:Sitename>"
    try:
        root = ibabs_soap("GetMeetingtypes", body)
        result = {}
        for mt in root.iter(f"{{{IBABS_NS}}}iBabsMeetingtype"):
            mt_id = ibabs_tekst(mt, "Id")
            mt_naam = ibabs_tekst(mt, "Name")
            if mt_id:
                result[mt_id] = mt_naam
        return result
    except Exception as e:
        log(f"  ! GetMeetingtypes mislukt: {e}")
        return {}


def haal_vergaderingen_ibabs(sitename: str, vergadertypen: dict[str, bool],
                              terugkijk_dagen: int = 730) -> list[dict]:
    """Haal vergaderingen + documenten op via de iBabs SOAP API.

    Geeft [{id, naam, datum, documenten: [{naam, url}]}].
    """
    date_from = (datetime.now() - timedelta(days=terugkijk_dagen)).strftime("%Y-%m-%dT00:00:00")
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
        mt_id = ibabs_tekst(meeting, "MeetingtypeId")
        mt_naam = vergadertypen_map.get(mt_id, mt_id)

        if not wil_vergadering(mt_naam, vergadertypen):
            continue

        meeting_id = ibabs_tekst(meeting, "Id")
        datum_raw = ibabs_tekst(meeting, "MeetingDate")
        datum = datum_raw[:10] if datum_raw else ""

        documenten = []
        for doc in meeting.iter(f"{{{IBABS_NS}}}iBabsDocument"):
            confidential = ibabs_tekst(doc, "Confidential")
            if confidential == "true":
                continue
            url = ibabs_tekst(doc, "PublicDownloadURL")
            if not url:
                continue
            bestandsnaam = ibabs_tekst(doc, "FileName") or ibabs_tekst(doc, "DisplayName")
            if not bestandsnaam:
                bestandsnaam = f"document-{ibabs_tekst(doc, 'Id')}.pdf"
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


# ── iBabs Publieksportaal (HTML, gebruikt voor Gedeputeerde Staten) ─────────
#
# Naast de SOAP-API hierboven heeft iBabs ook een publiek, ongeauthenticeerd
# webportaal op https://<sitename>.bestuurlijkeinformatie.nl/ — hetzelfde
# portaal waar burgers vergaderstukken op inzien. Voor GS-besluiten (deze
# sectie) is dat de enige route: sommige provincies gebruiken voor GS een
# apart iBabs-portaal dat niet in de SOAP-directory staat (bijv. Limburg's
# limburggs.bestuurlijkeinformatie.nl) of publiceren de besluiten als platte
# tekst op de portaalpagina zelf zonder documentbijlagen (Utrecht). Bewust
# los gehouden van haal_vergaderingen_ibabs (SOAP) hierboven: andere bron,
# ander functienaam-suffix "_portaal" om verwarring te voorkomen.

IBABS_PORTAAL = "https://{sitename}.bestuurlijkeinformatie.nl"

_DUTCH_MAANDEN = {
    "januari": 1, "februari": 2, "maart": 3, "april": 4, "mei": 5, "juni": 6,
    "juli": 7, "augustus": 8, "september": 9, "oktober": 10, "november": 11,
    "december": 12,
}


def _ibabs_portaal_get(sitename: str, pad: str) -> str:
    """Haal een pagina op van het publieke iBabs-portaal van een organisatie."""
    url = f"{IBABS_PORTAAL.format(sitename=sitename)}{pad}"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode("utf-8", errors="replace")


def haal_categorieen_ibabs_portaal(sitename: str) -> dict[str, str]:
    """Geeft {agendatypeId: naam} van alle vergadercategorieën op het portaal."""
    html = _ibabs_portaal_get(sitename, "/Calendar")
    return dict(re.findall(r'href="/Calendar/OpenCategory/(\d+)"[^>]*>([^<]+)</a>', html))


def haal_vergaderingen_ibabs_portaal(sitename: str, vergadertypen: dict[str, bool],
                                      terugkijk_dagen: int = 730) -> list[dict]:
    """Haal vergaderingen + documenten op via het publieke iBabs-portaal.

    Geeft [{id, naam, datum, documenten: [{naam, url}]}] — zelfde vorm als
    haal_vergaderingen_ibabs (SOAP), dus bruikbaar met dezelfde
    download_vergaderingen_ibabs()-downloadlus.
    """
    try:
        categorieen = haal_categorieen_ibabs_portaal(sitename)
    except Exception as e:
        log(f"  ! iBabs-portaal onbereikbaar voor '{sitename}': {e}")
        return []

    relevante_categorieen = {
        cat_id: naam.strip() for cat_id, naam in categorieen.items()
        if wil_vergadering(naam, vergadertypen)
    }
    if not relevante_categorieen:
        return []

    vandaag = datetime.now()
    vroegste = vandaag - timedelta(days=terugkijk_dagen)

    vergaderingen = []
    for cat_id, cat_naam in relevante_categorieen.items():
        for jaar in range(vroegste.year, vandaag.year + 1):
            try:
                jaar_html = _ibabs_portaal_get(
                    sitename, f"/Agenda/RetrieveAgendasForYear?agendatypeId={cat_id}&year={jaar}")
            except Exception as e:
                log(f"  ! iBabs-fout bij ophalen {jaar} voor '{sitename}': {e}")
                continue

            for guid, dag, maand, jaartal in re.findall(
                r'href="/Agenda/Index/([0-9a-f-]{36})"[^>]*>\s*'
                r'<div class="agenda-link-title">\w+ (\d{1,2}) ([a-zA-Zéï]+) '
                r'<span class="sr-only">(\d{4})</span></div>',
                jaar_html,
            ):
                maand_nr = _DUTCH_MAANDEN.get(maand.lower())
                if not maand_nr:
                    continue
                try:
                    datum_obj = datetime(int(jaartal), maand_nr, int(dag))
                except ValueError:
                    continue
                if not (vroegste <= datum_obj <= vandaag):
                    continue

                try:
                    detail_html = _ibabs_portaal_get(sitename, f"/Agenda/Index/{guid}")
                except Exception as e:
                    log(f"  ! iBabs-fout bij ophalen vergadering {guid} voor '{sitename}': {e}")
                    continue

                documenten = []
                for doc_id, ruwe_naam in re.findall(
                    rf'href="/Agenda/Document/{re.escape(guid)}\?documentId='
                    r'([0-9a-f-]{36})[^"]*"[^>]*>(?:\s*<span[^>]*></span>)?\s*(.*?)\s*<span class="badge',
                    detail_html, re.DOTALL,
                ):
                    naam = " ".join(re.sub(r"<[^>]+>", "", ruwe_naam).split())
                    if not naam:
                        naam = f"document-{doc_id}"
                    if not naam.lower().endswith(".pdf"):
                        naam += ".pdf"
                    url = (f"{IBABS_PORTAAL.format(sitename=sitename)}"
                           f"/Document/LoadAgendaDocument/{doc_id}?agendaId={guid}")
                    documenten.append({"naam": naam, "url": url})

                vergaderingen.append({
                    "id": guid,
                    "naam": cat_naam,
                    "datum": datum_obj.strftime("%Y-%m-%d"),
                    "documenten": documenten,
                })

    return vergaderingen


# ── Download-lus (gedeeld patroon) ──────────────────────────────────────────

def download_vergaderingen_ori(vergaderingen: list[dict], index: str,
                                output_map: Path, droog: bool = False) -> tuple[int, int, int]:
    """Download documenten voor ORI-vergaderingen. Geeft (nieuw, overgeslagen, fouten)."""
    totaal_nieuw = totaal_overgeslagen = totaal_fout = 0

    for verg in vergaderingen:
        docs = haal_documenten_ori(index, verg["id"])
        if not docs:
            continue

        doelmap = output_map / veilige_naam(verg["naam"]) / verg["datum"]
        nieuwe_docs = [d for d in docs
                       if not (doelmap / (veilige_naam(d["naam"]) + ".pdf")).exists()]

        if not nieuwe_docs:
            totaal_overgeslagen += len(docs)
            continue

        log(f"\n  {verg['naam']} ({verg['datum']}) — {len(nieuwe_docs)} nieuw van {len(docs)}")

        if not droog:
            doelmap.mkdir(parents=True, exist_ok=True)

        for doc in docs:
            bestandsnaam = veilige_naam(doc["naam"]) + ".pdf"
            bestemming = doelmap / bestandsnaam

            if bestemming.exists():
                totaal_overgeslagen += 1
                continue

            if droog:
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

    return totaal_nieuw, totaal_overgeslagen, totaal_fout


def download_vergaderingen_notubiz(vergaderingen: list[dict],
                                    output_map: Path, droog: bool = False) -> tuple[int, int, int]:
    """Download documenten voor Notubiz-vergaderingen. Geeft (nieuw, overgeslagen, fouten)."""
    totaal_nieuw = totaal_overgeslagen = totaal_fout = 0

    for verg in vergaderingen:
        docs = haal_documenten_notubiz(verg["id"])
        if not docs:
            continue

        doelmap = output_map / veilige_naam(verg["naam"]) / verg["datum"]
        nieuwe_docs = [d for d in docs if not (doelmap / d["naam"]).exists()]

        if not nieuwe_docs:
            totaal_overgeslagen += len(docs)
            continue

        log(f"\n  {verg['naam']} ({verg['datum']}) — {len(nieuwe_docs)} nieuw van {len(docs)}")

        if not droog:
            doelmap.mkdir(parents=True, exist_ok=True)

        for doc in docs:
            bestemming = doelmap / doc["naam"]
            if bestemming.exists():
                totaal_overgeslagen += 1
                continue
            if droog:
                log(f"    [DROOG] {doc['naam']}")
                totaal_nieuw += 1
                continue
            try:
                grootte = download(doc["url"], bestemming)
                log(f"    + {doc['naam']} ({grootte / 1024:.0f} KB)")
                totaal_nieuw += 1
            except Exception as e:
                log(f"    ! FOUT: {doc['naam']} — {e}")
                totaal_fout += 1

    return totaal_nieuw, totaal_overgeslagen, totaal_fout


def download_vergaderingen_ibabs(vergaderingen: list[dict],
                                  output_map: Path, droog: bool = False) -> tuple[int, int, int]:
    """Download documenten voor iBabs-vergaderingen. Geeft (nieuw, overgeslagen, fouten)."""
    totaal_nieuw = totaal_overgeslagen = totaal_fout = 0

    for verg in vergaderingen:
        docs = verg["documenten"]
        if not docs:
            continue

        doelmap = output_map / veilige_naam(verg["naam"]) / verg["datum"]
        nieuwe_docs = [d for d in docs
                       if not (doelmap / (veilige_naam(d["naam"]) + ".pdf")).exists()]

        if not nieuwe_docs:
            totaal_overgeslagen += len(docs)
            continue

        log(f"\n  {verg['naam']} ({verg['datum']}) — {len(nieuwe_docs)} nieuw van {len(docs)}")

        if not droog:
            doelmap.mkdir(parents=True, exist_ok=True)

        for doc in docs:
            bestandsnaam = veilige_naam(doc["naam"]) + ".pdf"
            bestemming = doelmap / bestandsnaam

            if bestemming.exists():
                totaal_overgeslagen += 1
                continue

            if droog:
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

    return totaal_nieuw, totaal_overgeslagen, totaal_fout


def parse_jaren_arg(standaard_dagen: int = 730) -> tuple[str | None, int]:
    """Lees --jaren N uit sys.argv. Geeft (vanaf_datum, terugkijk_dagen).

    vanaf_datum: ISO-datumstring voor ORI-queries (of None als niet opgegeven).
    terugkijk_dagen: aantal dagen terug, bruikbaar voor Notubiz en iBabs.
    Standaard: standaard_dagen (default 730 = 2 jaar).
    """
    argv = sys.argv[1:]
    if "--jaren" not in argv:
        return None, standaard_dagen

    idx = argv.index("--jaren")
    if idx + 1 >= len(argv):
        return None, standaard_dagen

    try:
        jaren = float(argv[idx + 1])
        dagen = int(jaren * 365)
        vanaf = (datetime.now() - timedelta(days=dagen)).strftime("%Y-%m-%d")
        return vanaf, dagen
    except ValueError:
        return None, standaard_dagen


def log_samenvatting(nieuw: int, overgeslagen: int, fouten: int, output_map: Path):
    """Print een standaard-samenvatting na het downloaden."""
    log("")
    log("─" * 60)
    log(f"Nieuw gedownload : {nieuw}")
    log(f"Al aanwezig      : {overgeslagen}")
    log(f"Fouten           : {fouten}")
    log(f"Opgeslagen in    : {output_map}")
    log("─" * 60)


# ── Gedeputeerde Staten: eigen-website-backends (geen vergaderportaal) ──────
#
# Een deel van de provincies publiceert GS-besluiten niet via een
# vergaderportaal (Notubiz/iBabs/ORI) maar als eigen website: een simpele
# PDF-index (Flevoland, Groningen, Noord-Brabant, Noord-Holland), een
# jaar->maand-geneste index (Drenthe), een doorzoekbare Woo-index (Zeeland),
# een per-besluit-pagina (Zuid-Holland) of één statische pagina per jaar
# (Fryslân). Gebruikt door scraper_gs.py; zie het geneste "gs"-veld per
# provincie in bronnen/provincies.json voor welke backend van toepassing is.

GS_EIGEN_WEBSITE_BACKENDS = (
    "zuid-holland-website", "pdf-index", "pdf-index-genest",
    "fryslan-website", "utrecht-tekst", "zeeland-website",
)


def _http_get_text(url: str) -> str:
    """Haal een pagina op als tekst (gebruikt door de losse GS-website-backends)."""
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode("utf-8", errors="replace")


def _besluitenlijst_datum(tekst: str, fallback_jaar_maand: tuple[int, int] | None = None) -> str:
    """Best-effort datum-extractie uit een bestandsnaam/linktekst.

    Probeert 'dd-maandnaam-yyyy' (met -, _ of spatie), 'yyyy-mm-dd',
    'dd-mm-yyyy', 'yyyymmdd' (geen scheidingstekens, bijv. Noord-Brabants
    '20260831_obl_activiteiten.pdf') en 'yyyy ... week nn' (ISO-weeknummer,
    maandag als datum). Geeft 'YYYY-MM-DD'.

    Als niets herkend wordt: met fallback_jaar_maand (jaar, maand) — gebruikt
    door de geneste crawl (haal_besluiten_pdf_index_genest), waar de
    maand-subpagina zelf al een betrouwbare jaar/maand-context geeft — de 1e
    van die maand; anders 'onbekende-datum' (document wordt alsnog
    gedownload, alleen niet op datum gegroepeerd).
    """
    tekst_laag = tekst.lower()
    maandpatroon = "|".join(_DUTCH_MAANDEN.keys())

    m = re.search(rf'(\d{{1,2}})[-_ ](' + maandpatroon + r')[-_ ](\d{4})', tekst_laag)
    if m:
        dag, maand_naam, jaar = m.groups()
        try:
            return datetime(int(jaar), _DUTCH_MAANDEN[maand_naam], int(dag)).strftime("%Y-%m-%d")
        except ValueError:
            pass

    m = re.search(r'(?<!\d)(20\d{2})-(\d{1,2})-(\d{1,2})(?!\d)', tekst)
    if m:
        jaar, maand, dag = m.groups()
        try:
            return datetime(int(jaar), int(maand), int(dag)).strftime("%Y-%m-%d")
        except ValueError:
            pass

    m = re.search(r'(\d{1,2})-(\d{1,2})-(\d{4})', tekst)
    if m:
        dag, maand, jaar = m.groups()
        try:
            return datetime(int(jaar), int(maand), int(dag)).strftime("%Y-%m-%d")
        except ValueError:
            pass

    m = re.search(r'(?<!\d)(20\d{2})(\d{2})(\d{2})(?!\d)', tekst)
    if m:
        jaar, maand, dag = m.groups()
        try:
            return datetime(int(jaar), int(maand), int(dag)).strftime("%Y-%m-%d")
        except ValueError:
            pass

    m = re.search(r'(\d{4}).*?week[_\s-]*(\d{1,2})', tekst_laag)
    if m:
        jaar, week = int(m.group(1)), int(m.group(2))
        try:
            return datetime.fromisocalendar(jaar, week, 1).strftime("%Y-%m-%d")
        except ValueError:
            pass

    if fallback_jaar_maand:
        jaar, maand = fallback_jaar_maand
        return datetime(jaar, maand, 1).strftime("%Y-%m-%d")

    return "onbekende-datum"


def haal_besluiten_pdf_index(basis_url: str, terugkijk_dagen: int = 730,
                              pagina_param: str | None = None) -> list[dict]:
    """Haal GS-besluiten op van een simpele PDF-index-pagina.

    Groepeert alle gevonden PDF-links per herkende datum tot 'vergadering'-
    achtige items ({id, naam, datum, documenten}), zodat de bestaande
    downloadlus (download_vergaderingen_ibabs) hergebruikt kan worden.

    Als pagina_param is gegeven (bijv. 'tx_bwibabs_overview[currentPage]'),
    wordt doorgebladerd (pagina=2, 3, ...) totdat een pagina geen documenten
    meer oplevert binnen het tijdvenster — dit gaat ervan uit dat de index
    nieuwste-eerst gesorteerd is, zoals bij de bekende gevallen.
    """
    vroegste = datetime.now() - timedelta(days=terugkijk_dagen)
    per_datum: dict[str, list[dict]] = {}

    pagina = 1
    while True:
        if pagina == 1 or not pagina_param:
            url = basis_url
        else:
            sep = "&" if "?" in basis_url else "?"
            url = f"{basis_url}{sep}{urllib.parse.quote(pagina_param)}={pagina}"

        html = _http_get_text(url)

        nieuw_binnen_venster = 0
        for match in re.finditer(r'<a\s+[^>]*href="([^"]+\.pdf)"[^>]*>(.*?)</a>',
                                  html, re.IGNORECASE | re.DOTALL):
            href, binnentekst = match.groups()
            titel_attr = re.search(r'title="([^"]*)"', match.group(0))
            binnentekst_schoon = re.sub(r"<[^>]+>", " ", binnentekst).strip()
            bestandsnaam = href.rsplit("/", 1)[-1]
            datum_bron = " ".join(filter(None, [
                bestandsnaam, binnentekst_schoon, titel_attr.group(1) if titel_attr else ""]))
            datum = _besluitenlijst_datum(datum_bron)

            if datum != "onbekende-datum":
                if datetime.strptime(datum, "%Y-%m-%d") < vroegste:
                    continue
                nieuw_binnen_venster += 1

            volledige_url = urllib.parse.urljoin(url, href)
            per_datum.setdefault(datum, []).append({"naam": bestandsnaam, "url": volledige_url})

        if not pagina_param or nieuw_binnen_venster == 0:
            break
        pagina += 1
        if pagina > 100:
            break

    return [
        {"id": datum, "naam": "GS-besluiten", "datum": datum, "documenten": docs}
        for datum, docs in per_datum.items()
    ]


def haal_besluiten_pdf_index_genest(overzicht_url: str, terugkijk_dagen: int = 730) -> list[dict]:
    """Haal GS-besluiten op van een tweetraps-index: jaaroverzicht met
    maand-subpagina's, elk met besluitenlijst-PDF's (bijv. Drenthe).

    Anders dan haal_besluiten_pdf_index staan de PDF's niet direct op de
    overzichtspagina maar op per-maand-subpagina's (linktekst 'Januari
    2026' e.d., iprox-CMS 'siteLink'-patroon). De bestandsnamen zelf zijn
    inconsistent (soms zonder jaar of dag) — de maand-subpagina is de enige
    betrouwbare datumbron, dus een PDF zonder herkenbare eigen datum krijgt
    de 1e van die maand toegewezen via _besluitenlijst_datum's
    fallback_jaar_maand (weekprecisie is voor dit doel voldoende).
    """
    vroegste = datetime.now() - timedelta(days=terugkijk_dagen)

    html = _http_get_text(overzicht_url)
    maand_links = []
    for url, linktekst in re.findall(r'<a class="siteLink" href="([^"]+)">([^<]+)</a>', html):
        m = re.search(r'([a-zA-Z]+)\s+(\d{4})', linktekst)
        if not m:
            continue
        maand_nr = _DUTCH_MAANDEN.get(m.group(1).lower())
        if not maand_nr:
            continue
        jaar = int(m.group(2))
        try:
            if datetime(jaar, maand_nr, 1) < vroegste.replace(day=1):
                continue
        except ValueError:
            continue
        maand_links.append((url, jaar, maand_nr))

    per_datum: dict[str, list[dict]] = {}
    for maand_url, jaar, maand_nr in maand_links:
        try:
            maand_html = _http_get_text(maand_url)
        except Exception as e:
            log(f"  ! FOUT bij ophalen maandpagina '{maand_url}': {e}")
            continue

        for match in re.finditer(r'<a\s+[^>]*href="([^"]+\.pdf)"[^>]*>(.*?)</a>',
                                  maand_html, re.IGNORECASE | re.DOTALL):
            href, binnentekst = match.groups()
            titel_attr = re.search(r'title="([^"]*)"', match.group(0))
            binnentekst_schoon = re.sub(r"<[^>]+>", " ", binnentekst).strip()
            bestandsnaam = href.rsplit("/", 1)[-1]
            datum_bron = " ".join(filter(None, [
                bestandsnaam, binnentekst_schoon, titel_attr.group(1) if titel_attr else ""]))
            datum = _besluitenlijst_datum(datum_bron, fallback_jaar_maand=(jaar, maand_nr))

            if datetime.strptime(datum, "%Y-%m-%d") < vroegste:
                continue

            volledige_url = urllib.parse.urljoin(maand_url, href)
            per_datum.setdefault(datum, []).append({"naam": bestandsnaam, "url": volledige_url})

    return [
        {"id": datum, "naam": "GS-besluiten", "datum": datum, "documenten": docs}
        for datum, docs in per_datum.items()
    ]


def haal_besluiten_fryslan(terugkijk_dagen: int = 730) -> list[dict]:
    """Haal GS-besluiten van Fryslân op via hun eigen website.

    Elk jaar staat op een eigen, voorspelbare statische pagina
    (`/besluitenlijsten-<jaar>`, bijv. `besluitenlijsten-2026`) in plaats van
    één doorlopende of geneste index. De pagina is een Next.js-app maar de
    PDF-links staan gewoon server-side-gerenderd in de HTML (geen
    JS-uitvoering nodig). De bestandsnaam bevat altijd een dd-mm-yyyy-datum
    ('GS Besluitenlijst 02-06-2026.pdf' / 'gs_besluitenlijst_17-12-2024_0.pdf'),
    dus _besluitenlijst_datum() vindt hem zonder fallback. Fryslân verwijst
    zelf naar een eigen webarchief voor besluiten van vóór 2021 — die jaren
    worden hier niet opgehaald.
    """
    vroegste = datetime.now() - timedelta(days=terugkijk_dagen)
    jaar_van = max(vroegste.year, 2021)

    per_datum: dict[str, list[dict]] = {}
    for jaar in range(datetime.now().year, jaar_van - 1, -1):
        url = f"https://www.fryslan.frl/besluitenlijsten-{jaar}"
        try:
            html = _http_get_text(url)
        except Exception as e:
            log(f"  ! FOUT bij ophalen '{url}': {e}")
            continue

        for href in re.findall(r'<a\s+[^>]*href="([^"]+\.pdf[^"]*)"[^>]*>', html, re.IGNORECASE):
            href_schoon = urllib.parse.unquote(href)
            bestandsnaam = href_schoon.rsplit("/", 1)[-1].split("?")[0]
            datum = _besluitenlijst_datum(bestandsnaam)

            if datum != "onbekende-datum" and datetime.strptime(datum, "%Y-%m-%d") < vroegste:
                continue

            per_datum.setdefault(datum, []).append({"naam": bestandsnaam, "url": href})

    return [
        {"id": datum, "naam": "GS-besluiten", "datum": datum, "documenten": docs}
        for datum, docs in per_datum.items()
    ]


ZEELAND_WOO_URL = "https://www.zeeland.nl/loket/woo/agendas-en-besluitenlijsten-gedeputeerde-staten"


def haal_besluiten_zeeland(terugkijk_dagen: int = 730) -> list[dict]:
    """Haal GS-agenda's en -besluitenlijsten van Zeeland op via hun Woo-index.

    Zeeland publiceert GS-agenda's en -besluitenlijsten niet via een
    vergaderportaal maar als doorzoekbare Woo-index (Drupal Search API +
    Facets), gepagineerd met '?page=0,1,2,...' (nul-geïndexeerd — anders dan
    de 1-geïndexeerde pagina_param van haal_besluiten_pdf_index, vandaar een
    eigen functie). Elk resultaat linkt rechtstreeks naar het PDF-bestand
    zelf (geen tussenliggende detailpagina, geen '.pdf'-extensie in de URL —
    Content-Type bepaalt het bestandstype, niet de padnaam). De titel bevat
    de datum ('Besluitenlijst Gedeputeerde Staten van Zeeland 30 juni 2026').
    """
    vroegste = datetime.now() - timedelta(days=terugkijk_dagen)
    per_datum: dict[str, list[dict]] = {}

    pagina = 0
    while True:
        url = ZEELAND_WOO_URL if pagina == 0 else f"{ZEELAND_WOO_URL}?page={pagina}"
        html = _http_get_text(url)

        nieuw_binnen_venster = 0
        for href, titel in re.findall(
            r'<a href="(/digitaal-archief/[^"]+)"\s*class="search-result[^"]*"\s*>\s*'
            r'<h3 class="search-result__title[^"]*">\s*([^<]+?)\s*</h3>',
            html,
        ):
            titel = titel.strip()
            datum = _besluitenlijst_datum(titel)
            if datum != "onbekende-datum":
                if datetime.strptime(datum, "%Y-%m-%d") < vroegste:
                    continue
                nieuw_binnen_venster += 1

            volledige_url = urllib.parse.urljoin(url, href)
            per_datum.setdefault(datum, []).append({"naam": titel, "url": volledige_url})

        if nieuw_binnen_venster == 0:
            break
        pagina += 1
        if pagina > 100:
            break

    return [
        {"id": datum, "naam": "GS-besluiten", "datum": datum, "documenten": docs}
        for datum, docs in per_datum.items()
    ]


ZH_BESLUITEN_URL = "https://www.zuid-holland.nl/politiek-bestuur/gedeputeerde-staten/besluiten/"


def haal_besluiten_zuid_holland(terugkijk_dagen: int = 730) -> list[dict]:
    """Haal GS-besluiten van Zuid-Holland op via hun eigen website.

    Anders dan de andere provincies publiceert Zuid-Holland GS-besluiten niet
    via een vergaderportaal maar als los doorzoekbare, individuele pagina's —
    elk besluit met eigen bijlagen, geen vergaderdatum met meerdere
    agendapunten. Geeft dezelfde [{id, naam, datum, documenten: [{naam, url}]}]
    -vorm terug als de vergadering-gebaseerde bronnen (één 'besluit' per
    item), zodat de bestaande downloadlus (download_vergaderingen_ibabs)
    hergebruikt kan worden. Traag door het ontbreken van een bulk-API: één
    verzoek per indexpagina (10 besluiten) plus één verzoek per besluit voor
    de bijlagen — voor het standaard-tijdvenster van 2 jaar al gauw honderden
    verzoeken.
    """
    date_from = (datetime.now() - timedelta(days=terugkijk_dagen)).strftime("%d-%m-%Y")

    eerste_pagina = _http_get_text(f"{ZH_BESLUITEN_URL}?date_from={date_from}")
    laatste_pagina = max(
        (int(p) for p in re.findall(r'data-page="(\d+)"', eerste_pagina)), default=0)

    besluiten = []
    for pagina in range(laatste_pagina + 1):
        html = eerste_pagina if pagina == 0 else _http_get_text(
            f"{ZH_BESLUITEN_URL}?date_from={date_from}&pager_page={pagina}")

        for url, titel, datum_tekst in re.findall(
            r'<a class="siteLink" href="([^"]+)">([^<]+)</a>.*?'
            r'class="iprox-content iprox-date date">([^<]+)</div>',
            html, re.DOTALL,
        ):
            delen = datum_tekst.strip().split()
            if len(delen) != 3:
                continue
            dag, maand_naam, jaar = delen
            maand_nr = _DUTCH_MAANDEN.get(maand_naam.lower())
            if not maand_nr:
                continue
            try:
                datum_obj = datetime(int(jaar), maand_nr, int(dag))
            except ValueError:
                continue

            try:
                detail_html = _http_get_text(url)
            except Exception as e:
                log(f"  ! FOUT bij ophalen besluit '{titel.strip()}': {e}")
                continue

            documenten = [
                {
                    "naam": pdf_url.rsplit("/", 1)[-1],
                    "url": f"https://www.zuid-holland.nl{pdf_url}" if pdf_url.startswith("/") else pdf_url,
                }
                for pdf_url in re.findall(r'href="([^"]+\.pdf)"', detail_html, re.IGNORECASE)
            ]

            besluiten.append({
                "id": url.rsplit("/", 1)[-1],
                "naam": titel.strip(),
                "datum": datum_obj.strftime("%Y-%m-%d"),
                "documenten": documenten,
            })

    return besluiten


def haal_besluiten_utrecht(terugkijk_dagen: int = 730) -> list[dict]:
    """Haal GS-besluiten van Utrecht op — als platte tekst, niet als PDF.

    Utrecht heeft een eigen iBabs-portaal (provincieutrecht.bestuurlijkeinformatie.nl,
    los van het ORI-portaal dat voor Provinciale Staten gebruikt wordt) met een
    categorie 'GS-Besluiten' en wekelijkse vergaderingen sinds 2023. Anders dan
    bij elke andere bron in dit project hangen daar geen documenten aan de
    vergaderingen — maar de volledige besluitenlijst (per agendapunt: nummer,
    titel, essentie/samenvatting, besluit) staat gewoon als platte,
    server-gerenderde HTML op de vergaderpagina zelf.

    Geeft [{id, naam, datum, documenten: [{naam, tekst}]}] terug — met 'tekst'
    in plaats van 'url', want er valt niets te downloaden. Wordt daarom niet
    met download_vergaderingen_ibabs verwerkt maar met de eigen
    schrijf_besluiten_utrecht().
    """
    sitename = "provincieutrecht"
    categorieen = haal_categorieen_ibabs_portaal(sitename)
    gs_categorieen = [cid for cid, naam in categorieen.items()
                       if "gs-besluiten" in naam.strip().lower()]
    if not gs_categorieen:
        return []

    vandaag = datetime.now()
    vroegste = vandaag - timedelta(days=terugkijk_dagen)

    vergaderingen = []
    for cat_id in gs_categorieen:
        for jaar in range(vroegste.year, vandaag.year + 1):
            try:
                jaar_html = _ibabs_portaal_get(
                    sitename, f"/Agenda/RetrieveAgendasForYear?agendatypeId={cat_id}&year={jaar}")
            except Exception as e:
                log(f"  ! iBabs-fout bij ophalen {jaar}: {e}")
                continue

            for guid, dag, maand, jaartal in re.findall(
                r'href="/Agenda/Index/([0-9a-f-]{36})"[^>]*>\s*'
                r'<div class="agenda-link-title">\w+ (\d{1,2}) ([a-zA-Zéï]+) '
                r'<span class="sr-only">(\d{4})</span></div>',
                jaar_html,
            ):
                maand_nr = _DUTCH_MAANDEN.get(maand.lower())
                if not maand_nr:
                    continue
                try:
                    datum_obj = datetime(int(jaartal), maand_nr, int(dag))
                except ValueError:
                    continue
                if not (vroegste <= datum_obj <= vandaag):
                    continue

                try:
                    detail_html = _ibabs_portaal_get(sitename, f"/Agenda/Index/{guid}")
                except Exception as e:
                    log(f"  ! iBabs-fout bij ophalen vergadering {guid}: {e}")
                    continue

                agendapunten = []
                for chunk in re.split(
                        r'<div\s+class="panel panel-default agenda-item"', detail_html)[1:]:
                    chunk = re.sub(r'^[^<]*>', '', chunk, count=1)
                    m_id = re.search(r'class="panel-id">([^<]*)</div>', chunk)
                    m_titel = re.search(
                        r'class="panel-title-label"[^>]*>\s*(.*?)\s*</span>', chunk, re.DOTALL)
                    nummer = m_id.group(1).strip() if m_id else ""
                    titel = html_unescape(re.sub(r'\s+', ' ', m_titel.group(1)).strip()) if m_titel else "agendapunt"

                    tekst = re.sub(r'<[^>]+>', ' ', chunk)
                    tekst = tekst.replace('\xa0', ' ').replace('\r\n', '\n').replace('\r', '\n')
                    tekst = re.sub(r'[ \t]+', ' ', tekst)
                    tekst = re.sub(r' *\n *', '\n', tekst)
                    tekst = re.sub(r'\n{2,}', '\n\n', tekst).strip()
                    tekst = html_unescape(tekst)

                    bestandsnaam = f"{nummer}-{titel}".strip("-") if nummer else titel
                    agendapunten.append({"naam": bestandsnaam, "tekst": tekst})

                vergaderingen.append({
                    "id": guid,
                    "naam": "GS-Besluiten",
                    "datum": datum_obj.strftime("%Y-%m-%d"),
                    "documenten": agendapunten,
                })

    return vergaderingen


def schrijf_besluiten_utrecht(vergaderingen: list[dict], output_map: Path,
                               droog: bool = False) -> tuple[int, int, int]:
    """Schrijf Utrechts GS-besluiten (platte tekst per agendapunt) naar bestand.

    Analoog aan download_vergaderingen_ibabs, maar schrijft tekst rechtstreeks
    weg in plaats van een URL te downloaden — Utrecht's bron heeft geen
    document-bijlagen (zie haal_besluiten_utrecht).
    """
    totaal_nieuw = totaal_overgeslagen = totaal_fout = 0

    for verg in vergaderingen:
        agendapunten = verg["documenten"]
        if not agendapunten:
            continue

        doelmap = output_map / veilige_naam(verg["naam"]) / verg["datum"]
        nieuwe = [a for a in agendapunten
                  if not (doelmap / (veilige_naam(a["naam"]) + ".txt")).exists()]

        if not nieuwe:
            totaal_overgeslagen += len(agendapunten)
            continue

        log(f"\n  {verg['naam']} ({verg['datum']}) — {len(nieuwe)} nieuw van {len(agendapunten)}")

        if not droog:
            doelmap.mkdir(parents=True, exist_ok=True)

        for punt in agendapunten:
            bestandsnaam = veilige_naam(punt["naam"]) + ".txt"
            bestemming = doelmap / bestandsnaam

            if bestemming.exists():
                totaal_overgeslagen += 1
                continue

            if droog:
                log(f"    [DROOG] {bestandsnaam}")
                totaal_nieuw += 1
                continue

            try:
                bestemming.write_text(punt["tekst"], encoding="utf-8")
                log(f"    + {bestandsnaam} ({len(punt['tekst'])} tekens)")
                totaal_nieuw += 1
            except Exception as e:
                log(f"    ! FOUT bij schrijven {bestandsnaam}: {e}")
                totaal_fout += 1

    return totaal_nieuw, totaal_overgeslagen, totaal_fout


def vraag_doorzoekbaar_maken(nieuw: int, output_map: Path):
    """Vraag interactief of nieuwe documenten doorzoekbaar gemaakt moeten worden.

    Alleen actief als er nieuwe documenten zijn en de sessie interactief is.
    In cron of piped mode wordt de vraag stilletjes overgeslagen.
    """
    if nieuw == 0:
        return
    if not sys.stdin.isatty():
        return

    if nieuw <= 20:
        tijdschatting = "even"
    else:
        minuten = max(2, nieuw * 3 // 60)
        tijdschatting = f"~{minuten} minuten"

    doc_woord = "document" if nieuw == 1 else "documenten"
    print(f"\nWil je de {nieuw} nieuwe {doc_woord} nu doorzoekbaar maken?")
    print(f"Dit duurt {tijdschatting}. [j/n] ", end="", flush=True)

    try:
        antwoord = input().strip().lower()
    except (EOFError, KeyboardInterrupt):
        print()
        return

    if antwoord != "j":
        print()
        return

    print()
    index_script = TOOLKIT_MAP / "index.py"
    # output_map.name alleen zou de submap laten vallen (bijv. "gs" of
    # "provincies") — bij een provincie bestaan PS en GS onder dezelfde slug,
    # dus zonder submap-voorvoegsel kan index.py niet weten welke van de twee
    # bedoeld is. relative_to(OUTPUT_BASIS) geeft de volledige, ondubbelzinnige
    # vorm (bijv. "gs/utrecht").
    orgaan_pad = output_map.relative_to(OUTPUT_BASIS)
    subprocess.run([sys.executable, str(index_script), str(orgaan_pad)])


# ── Documentenmap-resolutie (gedeeld door index.py, server.py) ──────────────

ORGAAN_SUBMAPPEN = ("regelingen", "waterschappen", "veiligheidsregios", "provincies", "gs")


def resolveer_docs_map(orgaan: str) -> tuple[Path | None, list[Path]]:
    """Zoek de documentenmap voor een orgaan-slug of expliciet 'submap/slug'-pad.

    Probeert eerst OUTPUT_BASIS/orgaan direct — dat dekt zowel gemeenten (kale
    slug) als een expliciete submap-vorm zoals 'gs/utrecht' of
    'provincies/utrecht' (Path behandelt de '/' gewoon als padscheiding).
    Bestaat dat niet, dan wordt gezocht in de bekende submappen.

    Geeft (pad, kandidaten) terug:
      - 1 kandidaat gevonden:  pad = die kandidaat.
      - 0 kandidaten:          pad = None, kandidaten = [].
      - 2+ kandidaten:         pad = None (ambigu — bijv. een provincie met
                               zowel PS als GS gedownload, zelfde slug in twee
                               submappen). De aanroeper moet de gebruiker dan
                               vragen de submap/slug-vorm expliciet te gebruiken.
    """
    direct = OUTPUT_BASIS / orgaan
    if direct.exists():
        return direct, [direct]

    kandidaten = [
        pad for submap in ORGAAN_SUBMAPPEN
        if (pad := OUTPUT_BASIS / submap / orgaan).exists()
    ]
    if len(kandidaten) == 1:
        return kandidaten[0], kandidaten
    return None, kandidaten


# ── Bestuurlijke context (provincie, VR, waterschap, GRs per gemeente) ───────

_GRS_CACHE_PAD = BRONNEN_MAP / "grs_cache.json"
_GRS_CACHE_TTL_UREN = 24


def _lees_grs_cache() -> dict:
    if not _GRS_CACHE_PAD.exists():
        return {}
    try:
        return json.loads(_GRS_CACHE_PAD.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _schrijf_grs_cache(cache: dict) -> None:
    cache.setdefault("_opmerking",
        f"Cache van organisaties.overheid.nl GR-deelname per gemeente. "
        f"Per gemeente {_GRS_CACHE_TTL_UREN} uur geldig."
    )
    try:
        _GRS_CACHE_PAD.write_text(
            json.dumps(cache, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
    except Exception:
        pass


def _cache_geldig(entry: dict) -> bool:
    opgehaald = entry.get("_opgehaald", "")
    if not opgehaald:
        return False
    try:
        dt = datetime.fromisoformat(opgehaald)
    except ValueError:
        return False
    leeftijd = datetime.now(dt.tzinfo) - dt
    return leeftijd < timedelta(hours=_GRS_CACHE_TTL_UREN)


def haal_grs_voor_gemeente(slug: str, gebruik_cache: bool = True) -> list[dict]:
    """Haal de GRs op waaraan een gemeente deelneemt via organisaties.overheid.nl.

    Geeft een lijst van dicts met 'slug', 'naam' en 'overheid_id'.
    Resultaten worden 24 uur lokaal gecached in bronnen/grs_cache.json.
    Zet gebruik_cache=False om de cache over te slaan (b.v. bij refresh).
    """
    cache = _lees_grs_cache() if gebruik_cache else {}
    entry = cache.get(slug)
    if entry and _cache_geldig(entry):
        return entry.get("grs", [])

    mapping_pad = BRONNEN_MAP / "gemeenten_overheid.json"
    try:
        mapping = json.loads(mapping_pad.read_text(encoding="utf-8"))
    except Exception:
        return []

    info = mapping.get(slug)
    if not info:
        return []

    overheid_id = info["overheid_id"]
    gemeente_naam = info["naam"].replace(" ", "_").replace("'", "")
    url = f"https://organisaties.overheid.nl/{overheid_id}/Gemeente_{gemeente_naam}"

    try:
        req = urllib.request.Request(url, headers={"User-Agent": "lokaalbestuur-toolkit/1.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            html = resp.read().decode("utf-8")
    except Exception:
        # Netwerk faalde: val terug op cache, ook als die verlopen is
        if entry:
            return entry.get("grs", [])
        return []

    # Laad GR-index voor nette namen (indien beschikbaar)
    gr_index_pad = BRONNEN_MAP / "regelingen_overheid.json"
    gr_index = {}
    if gr_index_pad.exists():
        try:
            gr_index = {
                k: v for k, v in
                json.loads(gr_index_pad.read_text(encoding="utf-8")).items()
                if not k.startswith("_")
            }
        except Exception:
            pass

    # Haal alle GR-links op (/samenwerkingen/ID/Naam/)
    grs = []
    for m in re.finditer(
        r'href="[^"]*?/samenwerkingen/(\d+)/([^/"]+)/"',
        html
    ):
        overheid_gr_id, slug_raw = m.group(1), m.group(2)

        # Gebruik de index voor een nette naam; val terug op URL-afleiding
        if overheid_gr_id in gr_index:
            naam = gr_index[overheid_gr_id]["naam"]
        else:
            naam = re.sub(r"_+", " ", slug_raw).strip()
            naam = re.sub(r"^Gemeenschappelijk[e]?\s+[Rr]egeling\s+", "", naam)
            naam = naam[0].upper() + naam[1:] if naam else naam

        gr_slug = re.sub(
            r"^gemeenschappelijk[e]?-regeling-", "",
            slug_raw.lower().replace("_", "-")
        )
        grs.append({
            "slug": gr_slug,
            "naam": naam,
            "overheid_id": overheid_gr_id,
        })

    # Schrijf naar cache
    cache[slug] = {
        "_opgehaald": datetime.now().astimezone().isoformat(timespec="seconds"),
        "grs": grs,
    }
    _schrijf_grs_cache(cache)
    return grs


def _orgaan_status(pad: Path) -> tuple[bool, int]:
    """Geef (gedownload, n_docs) voor een orgaan-map."""
    if not pad.exists():
        return False, 0
    n = sum(1 for _ in pad.rglob("*.pdf"))
    return n > 0, n


_BRONBESTAND_PER_TYPE = {
    "waterschap":       "waterschappen.json",
    "veiligheidsregio": "veiligheidsregios.json",
    "gr":               "regelingen.json",
    "provincie":        "provincies.json",
}


def toon_deelnemende_gemeenten(orgaan_type: str, slug: str) -> None:
    """Toon na een scraper-run welke gemeenten bij dit orgaan horen.

    orgaan_type: 'waterschap', 'veiligheidsregio', 'gr' of 'provincie'.
    Per gemeente: vinkje als al gedownload (PDF's in OUTPUT_BASIS/<slug>/),
    anders het scraper-commando om hem op te halen.
    Stilte als er geen catalogusgegevens zijn — beter geen weergave dan ruis.
    """
    bestandsnaam = _BRONBESTAND_PER_TYPE.get(orgaan_type)
    if not bestandsnaam:
        return

    pad = BRONNEN_MAP / bestandsnaam
    if not pad.exists():
        return

    try:
        data = json.loads(pad.read_text(encoding="utf-8"))
    except Exception:
        return

    info = data.get(slug)
    if not info:
        return

    gemeenten = info.get("gemeenten", [])
    if not gemeenten:
        return

    items: list[tuple[str, bool, int]] = []
    for g_slug in sorted(gemeenten):
        g_map = OUTPUT_BASIS / g_slug
        gedownload, n_docs = _orgaan_status(g_map)
        items.append((g_slug, gedownload, n_docs))

    al_gedownload = [i for i in items if i[1]]

    log("")
    log(f"  Deelnemende gemeenten ({len(items)}, waarvan {len(al_gedownload)} al gedownload)")
    log("  " + "─" * 56)
    for g_slug, gedownload, n_docs in items:
        if gedownload:
            log(f"    ✓ {g_slug:<35s} ({n_docs} docs)")
        else:
            log(f"    ○ {g_slug:<35s} python3 scraper.py {g_slug}")
    log("  " + "─" * 56)


def haal_bestuurlijke_context(gemeente: str, gebruik_cache: bool = True) -> dict:
    """Geef de complete bestuurlijke context van een gemeente terug.

    Bevraagt organisaties.overheid.nl voor GRs (met 24-uurs cache) en de
    lokale catalogus voor provincie/VR/waterschap. Per orgaan: of er al
    documenten zijn gedownload, en hoe je het zou downloaden.

    Geeft een dict met sleutels 'provincie', 'gs', 'veiligheidsregio',
    'waterschap', 'gr'. Elke waarde is een lijst van dicts met:
        slug:         str   — voor scraper-commando en folder
        naam:         str   — voor display
        gedownload:   bool  — al PDF's gevonden in OUTPUT_BASIS
        n_docs:       int   — aantal PDF's (0 als niet gedownload)
        pad:          Path  — waar de PDF's staan/zouden staan
        downloadbaar: bool  — of er een automatische bron is
        scraper_cmd:  str   — kant-en-klaar shell-commando, of toelichting
                              als downloadbaar = False

    Extra velden:
        provincie-items: 'brontype' (str, "geen" voor zonder scraper)
        gr-items:        'overheid_id' (str)
    """
    context: dict[str, list[dict]] = {
        "provincie": [],
        "gs": [],
        "veiligheidsregio": [],
        "waterschap": [],
        "gr": [],
    }

    # ── Provincie ────────────────────────────────────────────────────────
    prov_pad = BRONNEN_MAP / "provincies.json"
    if prov_pad.exists():
        try:
            prov_config = json.loads(prov_pad.read_text(encoding="utf-8"))
            for slug, info in prov_config.items():
                if slug.startswith("_"):
                    continue
                if gemeente not in info.get("gemeenten", []):
                    continue
                pad = OUTPUT_BASIS / "provincies" / slug
                gedownload, n_docs = _orgaan_status(pad)
                brontype = info.get("brontype", "")
                downloadbaar = brontype != "geen"
                scraper_cmd = (
                    f"python3 scraper_provincie.py {slug}"
                    if downloadbaar else "(geen geautomatiseerde bron)"
                )
                context["provincie"].append({
                    "slug": slug,
                    "naam": info.get("naam", slug),
                    "gedownload": gedownload,
                    "n_docs": n_docs,
                    "pad": pad,
                    "downloadbaar": downloadbaar,
                    "scraper_cmd": scraper_cmd,
                    "brontype": brontype,
                })

                # Gedeputeerde Staten (dagelijks bestuur) — zelfde provincie,
                # aparte bron/scraper (scraper_gs.py), zie het geneste
                # "gs"-veld in provincies.json.
                gs_info = info.get("gs", {})
                gs_pad = OUTPUT_BASIS / "gs" / slug
                gs_gedownload, gs_n_docs = _orgaan_status(gs_pad)
                gs_heeft_bron = any(gs_info.get(v) for v in ("notubiz_id", "ibabs_naam"))
                gs_downloadbaar = gs_heeft_bron or gs_info.get("backend") in GS_EIGEN_WEBSITE_BACKENDS
                gs_scraper_cmd = (
                    f"python3 scraper_gs.py {slug}" if gs_downloadbaar
                    else f"(geen geautomatiseerde bron: {gs_info.get('reden', 'onbekend')})"
                )
                context["gs"].append({
                    "slug": slug,
                    "naam": f"Gedeputeerde Staten {info.get('naam', slug)}",
                    "gedownload": gs_gedownload,
                    "n_docs": gs_n_docs,
                    "pad": gs_pad,
                    "downloadbaar": gs_downloadbaar,
                    "scraper_cmd": gs_scraper_cmd,
                })
        except Exception:
            pass

    # ── Veiligheidsregio ─────────────────────────────────────────────────
    vr_pad = BRONNEN_MAP / "veiligheidsregios.json"
    if vr_pad.exists():
        try:
            vr_config = json.loads(vr_pad.read_text(encoding="utf-8"))
            for slug, info in vr_config.items():
                if slug.startswith("_"):
                    continue
                if gemeente not in info.get("gemeenten", []):
                    continue
                pad = OUTPUT_BASIS / "veiligheidsregios" / slug
                gedownload, n_docs = _orgaan_status(pad)
                context["veiligheidsregio"].append({
                    "slug": slug,
                    "naam": info.get("naam", slug),
                    "gedownload": gedownload,
                    "n_docs": n_docs,
                    "pad": pad,
                    "downloadbaar": True,
                    "scraper_cmd": f"python3 scraper_vr.py {slug}",
                })
        except Exception:
            pass

    # ── Waterschap ───────────────────────────────────────────────────────
    ws_pad = BRONNEN_MAP / "waterschappen.json"
    if ws_pad.exists():
        try:
            ws_config = json.loads(ws_pad.read_text(encoding="utf-8"))
            for slug, info in ws_config.items():
                if slug.startswith("_"):
                    continue
                if gemeente not in info.get("gemeenten", []):
                    continue
                pad = OUTPUT_BASIS / "waterschappen" / slug
                gedownload, n_docs = _orgaan_status(pad)
                context["waterschap"].append({
                    "slug": slug,
                    "naam": info.get("naam", slug),
                    "gedownload": gedownload,
                    "n_docs": n_docs,
                    "pad": pad,
                    "downloadbaar": True,
                    "scraper_cmd": f"python3 scraper_waterschap.py {slug}",
                })
        except Exception:
            pass

    # ── Gemeenschappelijke regelingen (overheid.nl) ──────────────────────
    # Bouw overheid_id → slug mapping voor geconfigureerde GRs in regelingen.json
    # zodat we de juiste folder/scraper-slug gebruiken bij matches.
    reg_pad = BRONNEN_MAP / "regelingen.json"
    overheid_id_naar_slug: dict[str, str] = {}
    if reg_pad.exists():
        try:
            for slug, info in json.loads(reg_pad.read_text(encoding="utf-8")).items():
                if slug.startswith("_"):
                    continue
                oid = str(info.get("overheid_id", ""))
                if oid:
                    overheid_id_naar_slug[oid] = slug
        except Exception:
            pass

    officieel_grs = haal_grs_voor_gemeente(gemeente, gebruik_cache=gebruik_cache)
    if officieel_grs:
        for gr in officieel_grs:
            cat_slug = overheid_id_naar_slug.get(str(gr["overheid_id"]))
            in_catalogus = cat_slug is not None
            slug = cat_slug if in_catalogus else gr["slug"]
            pad = OUTPUT_BASIS / "regelingen" / slug
            gedownload, n_docs = _orgaan_status(pad)
            context["gr"].append({
                "slug": slug,
                "naam": gr["naam"],
                "gedownload": gedownload,
                "n_docs": n_docs,
                "pad": pad,
                "downloadbaar": True,
                "scraper_cmd": f"python3 scraper_gr.py {slug}",
                "overheid_id": gr["overheid_id"],
                "in_catalogus": in_catalogus,
            })
    elif reg_pad.exists():
        # Overheid.nl onbereikbaar → val terug op regelingen.json met gemeente-filter
        try:
            for slug, info in json.loads(reg_pad.read_text(encoding="utf-8")).items():
                if slug.startswith("_"):
                    continue
                gemeenten_gr = info.get("gemeenten", [])
                if gemeenten_gr and gemeente not in gemeenten_gr:
                    continue
                pad = OUTPUT_BASIS / "regelingen" / slug
                gedownload, n_docs = _orgaan_status(pad)
                context["gr"].append({
                    "slug": slug,
                    "naam": info.get("naam", slug),
                    "gedownload": gedownload,
                    "n_docs": n_docs,
                    "pad": pad,
                    "downloadbaar": True,
                    "scraper_cmd": f"python3 scraper_gr.py {slug}",
                    "overheid_id": str(info.get("overheid_id", "")),
                    "in_catalogus": True,
                })
        except Exception:
            pass

    return context
