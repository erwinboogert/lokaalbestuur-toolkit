"""
Scraper voor vergaderstukken van Nederlandse veiligheidsregio's.

Alle 25 veiligheidsregio's worden ondersteund, ongeacht publicatievorm:
  - website   : generieke PDF-scraper (22 regio's)
  - notubiz   : Notubiz API (Zeeland)
  - ibabs     : iBabs SOAP API (Brabant-Noord)

Gebruik:
    python3 scraper_vr.py rotterdam-rijnmond      # download vergaderstukken
    python3 scraper_vr.py rotterdam-rijnmond --droog
    python3 scraper_vr.py --lijst                  # toon beschikbare regio's
    python3 scraper_vr.py --welke <gemeente>       # welke VR hoort bij gemeente?

Configuratie: bronnen/veiligheidsregios.json
Output:       ~/Documents/notulen/veiligheidsregios/<naam>/
"""

import sys
import json
import re
import logging
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from pathlib import Path
from html.parser import HTMLParser

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
CATALOGUS_PAD = BRONNEN_MAP / "veiligheidsregios.json"

NOTUBIZ_API = "https://api.notubiz.nl"
NOTUBIZ_VERSION = "1.17.0"
TERUGKIJK_DAGEN = 730

IBABS_ENDPOINT = "https://wcf.ibabs.eu/api/Public.svc"
IBABS_NS = "http://tempuri.org/"

DROOG = "--droog" in sys.argv

HEADERS = {"User-Agent": "lokaalbestuur-toolkit/1.0"}


# ══════════════════════════════════════════════════════════════════════════════
# SETUP & LOGGING
# ══════════════════════════════════════════════════════════════════════════════

def setup(slug: str) -> Path:
    output_map = OUTPUT_BASIS / "veiligheidsregios" / slug
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
    return output_map


def log(msg):
    logging.info(msg)


# ══════════════════════════════════════════════════════════════════════════════
# CATALOGUS
# ══════════════════════════════════════════════════════════════════════════════

def laad_catalogus() -> dict:
    if not CATALOGUS_PAD.exists():
        print(f"\nCatalogus niet gevonden: {CATALOGUS_PAD}\n")
        sys.exit(1)
    return {k: v for k, v in json.loads(CATALOGUS_PAD.read_text(encoding="utf-8")).items()
            if not k.startswith("_")}


def vr_voor_gemeente(gemeente: str) -> list[tuple[str, dict]]:
    """Geef de veiligheidsregio('s) waarbij een gemeente is aangesloten."""
    catalogus = laad_catalogus()
    slug = gemeente.lower().strip()
    return [(s, info) for s, info in catalogus.items()
            if slug in info.get("gemeenten", [])]


# ══════════════════════════════════════════════════════════════════════════════
# WEBSITE-SCRAPER (generiek, type=website)
# ══════════════════════════════════════════════════════════════════════════════

class _LinkParser(HTMLParser):
    """Verzamelt alle href-waarden uit <a>-tags."""
    def __init__(self):
        super().__init__()
        self.links: list[str] = []

    def handle_starttag(self, tag, attrs):
        if tag == "a":
            for k, v in attrs:
                if k == "href" and v:
                    self.links.append(v)


def _haal_links(url: str) -> list[str]:
    """Haal alle links op van een pagina."""
    try:
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=15) as r:
            html = r.read().decode("utf-8", errors="replace")
    except Exception as e:
        log(f"Kan pagina niet ophalen ({url}): {e}")
        return []
    parser = _LinkParser()
    parser.feed(html)
    return parser.links


def _is_pdf_link(href: str) -> bool:
    return bool(href) and href.lower().split("?")[0].endswith(".pdf")


def _absoluut(href: str, basis: str) -> str:
    return urllib.parse.urljoin(basis, href)


def _kan_subpagina_zijn(href: str, basis: str) -> bool:
    """Heuristiek: is dit een link naar een vergaderpagina (geen PDF, geen extern)?"""
    if not href or href.startswith(("#", "mailto:", "tel:", "javascript:")):
        return False
    if _is_pdf_link(href):
        return False
    abs_url = _absoluut(href, basis)
    basis_host = urllib.parse.urlparse(basis).netloc
    link_host = urllib.parse.urlparse(abs_url).netloc
    if link_host and link_host != basis_host:
        return False
    # Zoek op jaar-/vergaderingswoorden in het pad
    pad = urllib.parse.urlparse(abs_url).path.lower()
    trefwoorden = ["vergader", "vergadering", "stuk", "agenda", "notulen", "besluit",
                   "bestuur", "2020", "2021", "2022", "2023", "2024", "2025", "2026"]
    return any(t in pad for t in trefwoorden)


def scrape_website(slug: str, info: dict, output_map: Path) -> tuple[int, int, int]:
    """
    Scrape PDF's van een veiligheidsregio-website.
    Geeft (nieuw, aanwezig, fouten) terug.
    """
    docs_url = info.get("docs_url", "")
    if not docs_url:
        log("Geen docs_url geconfigureerd.")
        return 0, 0, 0

    log(f"Documenten-pagina: {docs_url}")
    links = _haal_links(docs_url)

    pdf_links = [_absoluut(h, docs_url) for h in links if _is_pdf_link(h)]

    # Als er weinig directe PDFs zijn, één niveau dieper zoeken
    if len(pdf_links) < 3:
        sub_links = [_absoluut(h, docs_url) for h in links if _kan_subpagina_zijn(h, docs_url)]
        sub_links = list(dict.fromkeys(sub_links))[:20]  # max 20 subpagina's
        if sub_links:
            log(f"  Weinig directe PDFs — subpagina's verkennen ({len(sub_links)})…")
        for sub_url in sub_links:
            sub_hrefs = _haal_links(sub_url)
            for h in sub_hrefs:
                if _is_pdf_link(h):
                    abs_pdf = _absoluut(h, sub_url)
                    if abs_pdf not in pdf_links:
                        pdf_links.append(abs_pdf)

    pdf_links = list(dict.fromkeys(pdf_links))  # dedupliceer
    log(f"  {len(pdf_links)} PDF's gevonden")

    nieuw = aanwezig = fouten = 0
    for url in pdf_links:
        bestandsnaam = urllib.parse.unquote(url.split("/")[-1].split("?")[0])
        if not bestandsnaam.lower().endswith(".pdf"):
            bestandsnaam += ".pdf"
        bestemming = output_map / bestandsnaam

        if bestemming.exists():
            aanwezig += 1
            continue

        if DROOG:
            log(f"  [droog] {bestandsnaam}")
            nieuw += 1
            continue

        try:
            req = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=30) as r:
                bestemming.write_bytes(r.read())
            log(f"  ✓ {bestandsnaam}")
            nieuw += 1
        except Exception as e:
            log(f"  ✗ {bestandsnaam}: {e}")
            fouten += 1

    return nieuw, aanwezig, fouten


# ══════════════════════════════════════════════════════════════════════════════
# NOTUBIZ-SCRAPER (type=notubiz)
# ══════════════════════════════════════════════════════════════════════════════

def _notubiz_verzoek(endpoint: str) -> dict:
    sep = "&" if "?" in endpoint else "?"
    url = f"{NOTUBIZ_API}/{endpoint}{sep}version={NOTUBIZ_VERSION}&format=json"
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read())


def scrape_notubiz(slug: str, info: dict, output_map: Path) -> tuple[int, int, int]:
    notubiz_id = info.get("notubiz_id")
    if not notubiz_id:
        log("Geen notubiz_id geconfigureerd.")
        return 0, 0, 0

    vanaf = (datetime.now() - timedelta(days=TERUGKIJK_DAGEN)).strftime("%Y-%m-%d")
    log(f"Notubiz-ID: {notubiz_id} | vanaf: {vanaf}")

    try:
        data = _notubiz_verzoek(f"events?organisation_id={notubiz_id}&date_from={vanaf}&count=100")
    except Exception as e:
        log(f"Notubiz API fout: {e}")
        return 0, 0, 0

    vergaderingen = data.get("events", {}).get("results", [])
    log(f"  {len(vergaderingen)} vergaderingen gevonden")

    nieuw = aanwezig = fouten = 0
    for verg in vergaderingen:
        verg_id = verg.get("id")
        datum = verg.get("plannings_date", "onbekend")[:10]
        soort = verg.get("attribute", {}).get("name", "vergadering")

        try:
            detail = _notubiz_verzoek(f"events/{verg_id}")
        except Exception as e:
            log(f"  Vergadering {verg_id} overgeslagen: {e}")
            continue

        for doc in detail.get("event", {}).get("documents", []):
            url = doc.get("url") or doc.get("download_url")
            naam = doc.get("filename") or doc.get("title", "document")
            if not url or not url.lower().endswith(".pdf"):
                continue

            veilige_naam = re.sub(r'[^\w\-.]', '_', f"{datum}_{soort}_{naam}")
            if not veilige_naam.lower().endswith(".pdf"):
                veilige_naam += ".pdf"
            bestemming = output_map / veilige_naam

            if bestemming.exists():
                aanwezig += 1
                continue

            if DROOG:
                log(f"  [droog] {veilige_naam}")
                nieuw += 1
                continue

            try:
                req = urllib.request.Request(url, headers=HEADERS)
                with urllib.request.urlopen(req, timeout=30) as r:
                    bestemming.write_bytes(r.read())
                log(f"  ✓ {veilige_naam}")
                nieuw += 1
            except Exception as e:
                log(f"  ✗ {veilige_naam}: {e}")
                fouten += 1

    return nieuw, aanwezig, fouten


# ══════════════════════════════════════════════════════════════════════════════
# IBABS-SCRAPER (type=ibabs)
# ══════════════════════════════════════════════════════════════════════════════

def _ibabs_soap(actie: str, body_xml: str) -> ET.Element:
    envelope = f"""<?xml version="1.0" encoding="utf-8"?>
<soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/"
               xmlns:tns="{IBABS_NS}">
  <soap:Body>{body_xml}</soap:Body>
</soap:Envelope>"""
    req = urllib.request.Request(
        IBABS_ENDPOINT,
        data=envelope.encode("utf-8"),
        headers={
            "Content-Type": "text/xml; charset=utf-8",
            "SOAPAction": f'"{IBABS_NS}{actie}"',
        },
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        return ET.fromstring(r.read())


def _ibabs_tekst(element: ET.Element, tag: str) -> str:
    el = element.find(f".//{{{IBABS_NS}}}{tag}")
    return el.text or "" if el is not None else ""


def scrape_ibabs(slug: str, info: dict, output_map: Path) -> tuple[int, int, int]:
    ibabs_naam = info.get("ibabs_naam", "")
    if not ibabs_naam:
        log("Geen ibabs_naam geconfigureerd.")
        return 0, 0, 0

    vanaf = (datetime.now() - timedelta(days=TERUGKIJK_DAGEN)).strftime("%Y-%m-%dT00:00:00")
    log(f"iBabs site: {ibabs_naam} | vanaf: {vanaf[:10]}")

    try:
        root = _ibabs_soap("GetMeetings", f"""
<tns:GetMeetings>
  <tns:siteName>{ibabs_naam}</tns:siteName>
  <tns:listName></tns:listName>
  <tns:dateFrom>{vanaf}</tns:dateFrom>
  <tns:dateTo>{datetime.now().strftime('%Y-%m-%dT23:59:59')}</tns:dateTo>
</tns:GetMeetings>""")
    except Exception as e:
        log(f"iBabs API fout: {e}")
        return 0, 0, 0

    vergaderingen = root.findall(f".//{{{IBABS_NS}}}iBabsMeeting")
    log(f"  {len(vergaderingen)} vergaderingen gevonden")

    nieuw = aanwezig = fouten = 0
    for verg in vergaderingen:
        verg_id = _ibabs_tekst(verg, "Id")
        datum = _ibabs_tekst(verg, "MeetingDate")[:10]
        soort = _ibabs_tekst(verg, "MeetingType")

        try:
            detail_root = _ibabs_soap("GetMeetingWithItems", f"""
<tns:GetMeetingWithItems>
  <tns:siteName>{ibabs_naam}</tns:siteName>
  <tns:meetingId>{verg_id}</tns:meetingId>
</tns:GetMeetingWithItems>""")
        except Exception as e:
            log(f"  Vergadering {verg_id} overgeslagen: {e}")
            continue

        for doc in detail_root.findall(f".//{{{IBABS_NS}}}iBabsDocument"):
            url = _ibabs_tekst(doc, "PublicDownloadURL") or _ibabs_tekst(doc, "DownloadURL")
            naam = _ibabs_tekst(doc, "DisplayName") or _ibabs_tekst(doc, "FileName")
            if not url or not url.lower().endswith(".pdf"):
                continue

            veilige_naam = re.sub(r'[^\w\-.]', '_', f"{datum}_{soort}_{naam}")
            if not veilige_naam.lower().endswith(".pdf"):
                veilige_naam += ".pdf"
            bestemming = output_map / veilige_naam

            if bestemming.exists():
                aanwezig += 1
                continue

            if DROOG:
                log(f"  [droog] {veilige_naam}")
                nieuw += 1
                continue

            try:
                req = urllib.request.Request(url, headers=HEADERS)
                with urllib.request.urlopen(req, timeout=30) as r:
                    bestemming.write_bytes(r.read())
                log(f"  ✓ {veilige_naam}")
                nieuw += 1
            except Exception as e:
                log(f"  ✗ {veilige_naam}: {e}")
                fouten += 1

    return nieuw, aanwezig, fouten


# ══════════════════════════════════════════════════════════════════════════════
# HOOFDFUNCTIE
# ══════════════════════════════════════════════════════════════════════════════

def scrape(slug: str):
    catalogus = laad_catalogus()
    if slug not in catalogus:
        print(f"\nOnbekende veiligheidsregio: '{slug}'")
        print("Gebruik --lijst voor een overzicht.\n")
        sys.exit(1)

    info = catalogus[slug]
    naam = info.get("naam", slug)
    brontype = info.get("type", "website")

    output_map = setup(slug)
    output_map.mkdir(parents=True, exist_ok=True)

    log("=" * 60)
    log(f"Veiligheidsregio: {naam}")
    log(f"Type: {brontype}")
    log("=" * 60)

    if brontype == "notubiz":
        nieuw, aanwezig, fouten = scrape_notubiz(slug, info, output_map)
    elif brontype == "ibabs":
        nieuw, aanwezig, fouten = scrape_ibabs(slug, info, output_map)
    else:
        nieuw, aanwezig, fouten = scrape_website(slug, info, output_map)

    if opmerking := info.get("opmerking"):
        log(f"  Let op: {opmerking}")

    log("")
    log("─" * 60)
    log(f"Nieuw gedownload : {nieuw}")
    log(f"Al aanwezig      : {aanwezig}")
    log(f"Fouten           : {fouten}")
    log(f"Opgeslagen in    : {output_map}")
    log("─" * 60)


def toon_lijst():
    catalogus = laad_catalogus()
    print()
    print(f"{'Slug':<30} {'Naam':<45} Type")
    print("─" * 85)
    for slug, info in sorted(catalogus.items()):
        print(f"  {slug:<28} {info.get('naam', slug):<45} {info.get('type', 'website')}")
    print()
    print(f"  Totaal: {len(catalogus)} veiligheidsregio's")
    print()


def toon_welke(gemeente: str):
    resultaten = vr_voor_gemeente(gemeente)
    if not resultaten:
        print(f"\nGeen veiligheidsregio gevonden voor '{gemeente}'.")
        print("Controleer de spelling of voeg de gemeente toe aan bronnen/veiligheidsregios.json\n")
        return
    print()
    for slug, info in resultaten:
        print(f"  {info['naam']} → python3 scraper_vr.py {slug}")
    print()


# ══════════════════════════════════════════════════════════════════════════════
# CLI
# ══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if a != "--droog"]

    if not args or args[0] in ("-h", "--help", "-?", "help"):
        print(__doc__)
        sys.exit(0)

    if args[0] == "--lijst":
        toon_lijst()
    elif args[0] == "--welke" and len(args) > 1:
        toon_welke(args[1])
    else:
        scrape(args[0])
