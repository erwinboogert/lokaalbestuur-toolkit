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

import json
import re
import sys
import urllib.parse
import urllib.request
from datetime import datetime, timedelta
from html.parser import HTMLParser
from pathlib import Path

from api import (
    OUTPUT_BASIS, BRONNEN_MAP,
    setup_logging, log, log_samenvatting, vraag_doorzoekbaar_maken,
    toon_deelnemende_gemeenten,
    download,
    notubiz_verzoek,
    ibabs_soap, ibabs_tekst, IBABS_NS,
    parse_jaren_arg,
)

# ══════════════════════════════════════════════════════════════════════════════
# CONFIGURATIE
# ══════════════════════════════════════════════════════════════════════════════

CATALOGUS_PAD = BRONNEN_MAP / "veiligheidsregios.json"
TERUGKIJK_DAGEN = 730
HEADERS = {"User-Agent": "lokaalbestuur-toolkit/1.0"}


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
    pad = urllib.parse.urlparse(abs_url).path.lower()
    trefwoorden = ["vergader", "vergadering", "stuk", "agenda", "notulen", "besluit",
                   "bestuur", "2020", "2021", "2022", "2023", "2024", "2025", "2026"]
    return any(t in pad for t in trefwoorden)


def scrape_website(slug: str, info: dict, output_map: Path, droog: bool) -> tuple[int, int, int]:
    """Scrape PDF's van een veiligheidsregio-website."""
    docs_url = info.get("docs_url", "")
    if not docs_url:
        log("Geen docs_url geconfigureerd.")
        return 0, 0, 0

    log(f"Documenten-pagina: {docs_url}")
    links = _haal_links(docs_url)

    pdf_links = [_absoluut(h, docs_url) for h in links if _is_pdf_link(h)]

    if len(pdf_links) < 3:
        sub_links = [_absoluut(h, docs_url) for h in links if _kan_subpagina_zijn(h, docs_url)]
        sub_links = list(dict.fromkeys(sub_links))[:20]
        if sub_links:
            log(f"  Weinig directe PDFs — subpagina's verkennen ({len(sub_links)})…")
        for sub_url in sub_links:
            sub_hrefs = _haal_links(sub_url)
            for h in sub_hrefs:
                if _is_pdf_link(h):
                    abs_pdf = _absoluut(h, sub_url)
                    if abs_pdf not in pdf_links:
                        pdf_links.append(abs_pdf)

    pdf_links = list(dict.fromkeys(pdf_links))
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

        if droog:
            log(f"  [droog] {bestandsnaam}")
            nieuw += 1
            continue

        try:
            grootte = download(url, bestemming)
            log(f"  ✓ {bestandsnaam}")
            nieuw += 1
        except Exception as e:
            log(f"  ✗ {bestandsnaam}: {e}")
            fouten += 1

    return nieuw, aanwezig, fouten


# ══════════════════════════════════════════════════════════════════════════════
# NOTUBIZ-SCRAPER (type=notubiz)
# ══════════════════════════════════════════════════════════════════════════════

def scrape_notubiz(slug: str, info: dict, output_map: Path, droog: bool) -> tuple[int, int, int]:
    """Scrape vergaderstukken via de Notubiz API (VR-specifiek)."""
    notubiz_id = info.get("notubiz_id")
    if not notubiz_id:
        log("Geen notubiz_id geconfigureerd.")
        return 0, 0, 0

    vanaf = (datetime.now() - timedelta(days=TERUGKIJK_DAGEN)).strftime("%Y-%m-%d")
    log(f"Notubiz-ID: {notubiz_id} | vanaf: {vanaf}")

    try:
        data = notubiz_verzoek(f"events?organisation_id={notubiz_id}&date_from={vanaf}&count=100")
    except Exception as e:
        log(f"Notubiz API fout: {e}")
        return 0, 0, 0

    events_raw = data.get("events", [])
    if isinstance(events_raw, dict):
        vergaderingen = events_raw.get("results", [])
    else:
        vergaderingen = events_raw
    log(f"  {len(vergaderingen)} vergaderingen gevonden")

    nieuw = aanwezig = fouten = 0
    for verg in vergaderingen:
        verg_id = verg.get("id")
        datum = verg.get("plannings_date", "onbekend")[:10]
        soort = verg.get("attribute", {}).get("name", "vergadering")

        try:
            detail = notubiz_verzoek(f"events/{verg_id}")
        except Exception as e:
            log(f"  Vergadering {verg_id} overgeslagen: {e}")
            continue

        for doc in detail.get("event", {}).get("documents", []):
            url = doc.get("url") or doc.get("download_url")
            naam = doc.get("filename") or doc.get("title", "document")
            if not url or not url.lower().endswith(".pdf"):
                continue

            veilige = re.sub(r'[^\w\-.]', '_', f"{datum}_{soort}_{naam}")
            if not veilige.lower().endswith(".pdf"):
                veilige += ".pdf"
            bestemming = output_map / veilige

            if bestemming.exists():
                aanwezig += 1
                continue

            if droog:
                log(f"  [droog] {veilige}")
                nieuw += 1
                continue

            try:
                download(url, bestemming)
                log(f"  ✓ {veilige}")
                nieuw += 1
            except Exception as e:
                log(f"  ✗ {veilige}: {e}")
                fouten += 1

    return nieuw, aanwezig, fouten


# ══════════════════════════════════════════════════════════════════════════════
# IBABS-SCRAPER (type=ibabs)
# ══════════════════════════════════════════════════════════════════════════════

def scrape_ibabs(slug: str, info: dict, output_map: Path, droog: bool) -> tuple[int, int, int]:
    """Scrape vergaderstukken via de iBabs SOAP API (VR-specifiek)."""
    ibabs_naam = info.get("ibabs_naam", "")
    if not ibabs_naam:
        log("Geen ibabs_naam geconfigureerd.")
        return 0, 0, 0

    vanaf = (datetime.now() - timedelta(days=TERUGKIJK_DAGEN)).strftime("%Y-%m-%dT00:00:00")
    log(f"iBabs site: {ibabs_naam} | vanaf: {vanaf[:10]}")

    try:
        root = ibabs_soap("GetMeetings", (
            f"<tns:siteName>{ibabs_naam}</tns:siteName>"
            f"<tns:listName></tns:listName>"
            f"<tns:dateFrom>{vanaf}</tns:dateFrom>"
            f"<tns:dateTo>{datetime.now().strftime('%Y-%m-%dT23:59:59')}</tns:dateTo>"
        ))
    except Exception as e:
        log(f"iBabs API fout: {e}")
        return 0, 0, 0

    vergaderingen = root.findall(f".//{{{IBABS_NS}}}iBabsMeeting")
    log(f"  {len(vergaderingen)} vergaderingen gevonden")

    nieuw = aanwezig = fouten = 0
    for verg in vergaderingen:
        verg_id = ibabs_tekst(verg, "Id")
        datum = ibabs_tekst(verg, "MeetingDate")[:10]
        soort = ibabs_tekst(verg, "MeetingType")

        try:
            detail_root = ibabs_soap("GetMeetingWithItems", (
                f"<tns:siteName>{ibabs_naam}</tns:siteName>"
                f"<tns:meetingId>{verg_id}</tns:meetingId>"
            ))
        except Exception as e:
            log(f"  Vergadering {verg_id} overgeslagen: {e}")
            continue

        for doc in detail_root.findall(f".//{{{IBABS_NS}}}iBabsDocument"):
            url = ibabs_tekst(doc, "PublicDownloadURL") or ibabs_tekst(doc, "DownloadURL")
            naam = ibabs_tekst(doc, "DisplayName") or ibabs_tekst(doc, "FileName")
            if not url or not url.lower().endswith(".pdf"):
                continue

            veilige = re.sub(r'[^\w\-.]', '_', f"{datum}_{soort}_{naam}")
            if not veilige.lower().endswith(".pdf"):
                veilige += ".pdf"
            bestemming = output_map / veilige

            if bestemming.exists():
                aanwezig += 1
                continue

            if droog:
                log(f"  [droog] {veilige}")
                nieuw += 1
                continue

            try:
                download(url, bestemming)
                log(f"  ✓ {veilige}")
                nieuw += 1
            except Exception as e:
                log(f"  ✗ {veilige}: {e}")
                fouten += 1

    return nieuw, aanwezig, fouten


# ══════════════════════════════════════════════════════════════════════════════
# HOOFDFUNCTIE
# ══════════════════════════════════════════════════════════════════════════════

def scrape(slug: str, droog: bool):
    catalogus = laad_catalogus()
    if slug not in catalogus:
        print(f"\nOnbekende veiligheidsregio: '{slug}'")
        print("Gebruik --lijst voor een overzicht.\n")
        sys.exit(1)

    info = catalogus[slug]
    naam = info.get("naam", slug)
    brontype = info.get("type", "website")

    output_map = OUTPUT_BASIS / "veiligheidsregios" / slug
    setup_logging(output_map)
    output_map.mkdir(parents=True, exist_ok=True)

    log("=" * 60)
    log(f"Veiligheidsregio: {naam}")
    log(f"Type: {brontype}")
    log("=" * 60)

    if brontype == "notubiz":
        nieuw, aanwezig, fouten = scrape_notubiz(slug, info, output_map, droog)
    elif brontype == "ibabs":
        nieuw, aanwezig, fouten = scrape_ibabs(slug, info, output_map, droog)
    else:
        nieuw, aanwezig, fouten = scrape_website(slug, info, output_map, droog)

    if opmerking := info.get("opmerking"):
        log(f"  Let op: {opmerking}")

    log_samenvatting(nieuw, aanwezig, fouten, output_map)
    if not droog:
        vraag_doorzoekbaar_maken(nieuw, output_map)
    toon_deelnemende_gemeenten("veiligheidsregio", slug)


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
    droog = "--droog" in sys.argv
    args = [a for a in sys.argv[1:] if a not in ("--droog",)]

    # Pas TERUGKIJK_DAGEN aan op basis van --jaren N (bijv. --jaren 0.5 = 6 mnd)
    _, TERUGKIJK_DAGEN = parse_jaren_arg(TERUGKIJK_DAGEN)

    if not args or args[0] in ("-h", "--help", "-?", "help"):
        print(__doc__)
        sys.exit(0)

    if args[0] == "--lijst":
        toon_lijst()
    elif args[0] == "--welke" and len(args) > 1:
        toon_welke(args[1])
    else:
        scrape(args[0], droog)
