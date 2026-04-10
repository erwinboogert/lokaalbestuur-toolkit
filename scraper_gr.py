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

import sys
import json
import urllib.request
import re
import logging
import xml.etree.ElementTree as ET
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
NOTUBIZ_API = "https://api.notubiz.nl"
NOTUBIZ_VERSION = "1.17.0"
NOTUBIZ_TERUGKIJK_DAGEN = 730  # ~2 jaar

IBABS_ENDPOINT = "https://wcf.ibabs.eu/api/Public.svc"
IBABS_NS = "http://tempuri.org/"
IBABS_TERUGKIJK_DAGEN = 730  # ~2 jaar

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


# ── Notubiz API direct ────────────────────────────────────────────────────────

def notubiz_id_voor(naam: str) -> int | None:
    """Lees notubiz_id uit regelingen.json voor de opgegeven GR."""
    pad = BRONNEN_MAP / "regelingen.json"
    if not pad.exists():
        return None
    try:
        config = json.loads(pad.read_text(encoding="utf-8"))
        return config.get(naam, {}).get("notubiz_id")
    except Exception:
        return None


def notubiz_verzoek(endpoint: str) -> dict:
    """Doe een GET-verzoek naar de Notubiz API en geef het JSON-resultaat terug."""
    sep = "&" if "?" in endpoint else "?"
    url = f"{NOTUBIZ_API}/{endpoint}{sep}format=json&version={NOTUBIZ_VERSION}"
    req = urllib.request.Request(
        url, headers={"Accept": "application/json", "User-Agent": "Mozilla/5.0"}
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read())


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


def haal_vergaderingen_notubiz(org_id: int) -> list[dict]:
    """Haal vergaderingen op via de Notubiz API. Geeft [{id, naam, datum}]."""
    date_to = datetime.now().strftime("%Y-%m-%d 23:59:59")
    date_from = (datetime.now() - timedelta(days=NOTUBIZ_TERUGKIJK_DAGEN)).strftime("%Y-%m-%d 00:00:00")

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


# ── iBabs SOAP API ────────────────────────────────────────────────────────────

def ibabs_naam_voor(naam: str) -> str | None:
    """Lees ibabs_naam uit regelingen.json voor de opgegeven GR."""
    pad = BRONNEN_MAP / "regelingen.json"
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

        # Verzamel alle documenten (meeting-niveau én agenda-items) recursief
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

    laad_regeling_config(naam)
    output_map = setup(naam)

    log("=" * 60)
    log(f"GR: {naam}  {'(DROOG)' if DROOG else ''}")
    log("=" * 60)

    notubiz_id = notubiz_id_voor(naam)
    ibabs_naam = ibabs_naam_voor(naam)

    if notubiz_id:
        # ── Notubiz direct ────────────────────────────────────────────
        log(f"Bron: Notubiz API (org_id={notubiz_id})")
        vergaderingen = haal_vergaderingen_notubiz(notubiz_id)
        log(f"{len(vergaderingen)} vergaderingen gevonden")

        totaal_nieuw = totaal_overgeslagen = totaal_fout = 0

        for verg in vergaderingen:
            docs = haal_documenten_notubiz(verg["id"])
            if not docs:
                continue

            doelmap = vergadering_map(output_map, verg)
            nieuwe_docs = [d for d in docs if not (doelmap / d["naam"]).exists()]

            if not nieuwe_docs:
                totaal_overgeslagen += len(docs)
                continue

            log(f"\n  {verg['naam']} ({verg['datum']}) — {len(nieuwe_docs)} nieuw van {len(docs)}")

            if not DROOG:
                doelmap.mkdir(parents=True, exist_ok=True)

            for doc in docs:
                bestemming = doelmap / doc["naam"]
                if bestemming.exists():
                    totaal_overgeslagen += 1
                    continue
                if DROOG:
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

    elif ibabs_naam:
        # ── iBabs SOAP API ────────────────────────────────────────────
        log(f"Bron: iBabs API (sitename={ibabs_naam})")
        vergaderingen = haal_vergaderingen_ibabs(ibabs_naam)
        log(f"{len(vergaderingen)} vergaderingen gevonden")

        totaal_nieuw = totaal_overgeslagen = totaal_fout = 0

        for verg in vergaderingen:
            docs = verg["documenten"]
            if not docs:
                continue

            doelmap = vergadering_map(output_map, verg)
            nieuwe_docs = [d for d in docs if not (doelmap / d["naam"]).exists()]

            if not nieuwe_docs:
                totaal_overgeslagen += len(docs)
                continue

            log(f"\n  {verg['naam']} ({verg['datum']}) — {len(nieuwe_docs)} nieuw van {len(docs)}")

            if not DROOG:
                doelmap.mkdir(parents=True, exist_ok=True)

            for doc in docs:
                bestemming = doelmap / doc["naam"]
                if bestemming.exists():
                    totaal_overgeslagen += 1
                    continue
                if DROOG:
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

    else:
        # ── ORI API ───────────────────────────────────────────────────
        index = find_index(naam)
        if not index:
            log(f"FOUT: geen ORI-index, notubiz_id of ibabs_naam gevonden voor '{naam}'.")
            log("Gebruik --lijst-ori om beschikbare GRs in ORI te ontdekken.")
            log("Gebruik --zoek <naam> om een Notubiz-organisatie op te zoeken.")
            log("Voeg de GR toe via: python3 toolkit.py nieuwe-regeling")
            sys.exit(1)
        log(f"Bron: ORI API (index={index})")

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
