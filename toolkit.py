"""
Lokaalbestuur Toolkit — dashboard en interface

Gebruik:
    python3 toolkit.py                       toon dashboard (overzicht van actieve dossiers)
    python3 toolkit.py onderzoek <gemeente>  bereid Claude Code-sessie voor (bronnencheck + briefing)
    python3 toolkit.py scrape <orgaan>       download nieuwe vergaderstukken voor een orgaan
    python3 toolkit.py scrape --alles        download nieuwe vergaderstukken voor alle organen
    python3 toolkit.py nieuw-orgaan          voeg een orgaan toe (gemeente, waterschap of GR)
    python3 toolkit.py nieuw-dossier         stel een monitoringsdossier in (trefwoorden + alerts)
    python3 toolkit.py status                uitgebreid statusoverzicht
    python3 toolkit.py check                 controleer installatie
"""

from __future__ import annotations

import json
import re
import sqlite3
import subprocess
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

TOOLKIT_MAP = Path(__file__).parent
PYTHON = sys.executable

BRONNEN_MAP             = TOOLKIT_MAP / "bronnen"
GR_INDEX_PAD            = BRONNEN_MAP / "regelingen_overheid.json"
VEROUDERD_DREMPEL_DAGEN = 180  # 6 maanden


def _lees_config() -> dict:
    pad = TOOLKIT_MAP / "config.local.json"
    if pad.exists():
        try:
            return json.loads(pad.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}


_cfg = _lees_config()
_data_map = Path(_cfg["data_map"]).expanduser() if "data_map" in _cfg else None

DOSSIERS_MAP = (_data_map / "dossiers") if _data_map else (TOOLKIT_MAP / "dossiers")
ORGANEN_MAP = (_data_map / "organen") if _data_map else (TOOLKIT_MAP / "organen")
OUTPUT_BASIS = _data_map if _data_map else (Path.home() / "Documents" / "notulen")

# Standaard vergadertypen per orgaantype — gebruikt bij aanmaken nieuw orgaan
VERGADERTYPEN_PER_TYPE = {
    "gemeente":   ["gemeenteraad", "commissie", "raadsbrede commissie"],
    "waterschap": ["algemeen bestuur", "college van dijkgraaf en heemraden"],
    "gr":         ["algemeen bestuur", "dagelijks bestuur", "portefeuillehoudersoverleg"],
    "provincie":  ["provinciale staten", "gedeputeerde staten", "statencommissie", "commissie"],
}


# ── Hulpfuncties ──────────────────────────────────────────────────────────────

def lees_dossiers() -> list[dict]:
    """Lees alle dossierconfigs uit dossiers/."""
    if not DOSSIERS_MAP.exists():
        return []
    dossiers = []
    for pad in sorted(DOSSIERS_MAP.glob("*.json")):
        try:
            config = json.loads(pad.read_text(encoding="utf-8"))
            config["_naam"] = pad.stem
            dossiers.append(config)
        except Exception:
            pass
    return dossiers


def lees_organen() -> list[str]:
    """Geef lijst van beschikbare orgaannamen (bestandsstam van organen/*.json)."""
    if not ORGANEN_MAP.exists():
        return []
    return sorted(p.stem for p in ORGANEN_MAP.glob("*.json"))


def orgaan_van_dossier(dossier: dict) -> str:
    """Lees orgaannaam uit dossier-config; ondersteunt zowel 'orgaan' als oud 'gemeente' veld."""
    return dossier.get("orgaan") or dossier.get("gemeente", "—")


def laatste_run(orgaan: str, dossier_naam: str) -> str:
    """Haal datum van laatste analyse-run op."""
    staat_pad = OUTPUT_BASIS / orgaan / "logs" / f"analyse-staat-{dossier_naam}.json"
    if not staat_pad.exists():
        staat_pad = OUTPUT_BASIS / orgaan / "logs" / "analyse-staat.json"
    if not staat_pad.exists():
        return "nog niet gedraaid"
    try:
        data = json.loads(staat_pad.read_text(encoding="utf-8"))
        ts = data.get("laatste_run", "")
        if ts:
            dt = datetime.fromisoformat(ts)
            return dt.strftime("%d %b %Y, %H:%M")
        return "onbekend"
    except Exception:
        return "onbekend"


def vraag(prompt: str, standaard: str = "") -> str:
    """Stel een vraag; gebruik standaardwaarde als invoer leeg is."""
    if standaard:
        antwoord = input(f"  {prompt} [{standaard}]: ").strip()
        return antwoord or standaard
    while True:
        antwoord = input(f"  {prompt}: ").strip()
        if antwoord:
            return antwoord
        print("    (verplicht veld)")


def vraag_terugkijkperiode() -> list[str]:
    """Vraag de gebruiker hoe ver terug te kijken. Geeft een lijst met scraper-argumenten."""
    opties = [
        ("6 maanden",  "0.5"),
        ("12 maanden", "1"),
        ("18 maanden", "1.5"),
        ("24 maanden", "2", "← aanbevolen"),
    ]
    print()
    print("  Hoe ver wil je terugkijken bij de eerste download?")
    print()
    for i, optie in enumerate(opties, 1):
        label, _, *extra = optie
        toelichting = f"  {extra[0]}" if extra else ""
        print(f"    {i}.  {label}{toelichting}")
    print()
    while True:
        keuze = input("  Keuze [1-4]: ").strip()
        if keuze in ("1", "2", "3", "4"):
            _, jaren = opties[int(keuze) - 1][:2]
            return ["--jaren", jaren]
        print("  Voer een getal in van 1 tot 4.")


def voeg_crontabregel_toe(commentaar: str, regel: str):
    """Voeg een crontabregel toe als die er nog niet in staat. Geen bevestiging: wordt
    alleen aangeroepen vanuit setup-wizards waar de gebruiker dit gedrag verwacht."""
    result = subprocess.run(["crontab", "-l"], capture_output=True, text=True)
    bestaand = result.stdout if result.returncode == 0 else ""
    if regel in bestaand:
        return
    nieuw = bestaand.rstrip() + f"\n\n# {commentaar}\n{regel}\n"
    subprocess.run(["crontab", "-"], input=nieuw, text=True, check=True)
    print(f"  ✓ Crontabregel toegevoegd: {commentaar}")


# ── Commando's ────────────────────────────────────────────────────────────────

def dashboard():
    """Hoofddashboard: overzicht van actieve dossiers en beschikbare commando's."""
    print()
    print("Lokaalbestuur Toolkit")
    print("─" * 50)

    dossiers = lees_dossiers()

    if dossiers:
        print(f"\nActieve dossiers ({len(dossiers)}):\n")
        for d in dossiers:
            naam = d["_naam"]
            orgaan = orgaan_van_dossier(d)
            run = laatste_run(orgaan, naam)
            print(f"  • {naam:<22} {orgaan:<18} laatste run: {run}")
    else:
        print("\n  Geen dossiers gevonden.")
        print("  Maak er een aan met: python3 toolkit.py nieuw-dossier")

    # Bronnen-overzicht
    _toon_bronnen_status()

    print()
    print("─" * 50)
    print()
    print("  python3 toolkit.py onderzoek <gemeente>  → Claude-sessie voorbereiden")
    print("  python3 toolkit.py nieuw-orgaan          → orgaan toevoegen")
    print("  python3 toolkit.py nieuw-dossier         → monitoringsdossier aanmaken")
    print("  python3 toolkit.py status                → uitgebreid overzicht")
    print()


def _toon_bronnen_status():
    """Toon een compacte statusregel per brontype op het dashboard."""
    regels = []

    # Gemeenten (organen/*.json van type gemeente)
    organen = lees_organen()
    gemeenten = []
    for o in organen:
        pad = ORGANEN_MAP / f"{o}.json"
        try:
            cfg = json.loads(pad.read_text(encoding="utf-8"))
            if cfg.get("type", "gemeente") == "gemeente":
                gemeenten.append(o)
        except Exception:
            pass
    if gemeenten:
        regels.append(f"  Raadsstukken    {len(gemeenten)} gemeente(n)")

    # Regelingen
    reg_pad = TOOLKIT_MAP / "bronnen" / "regelingen.json"
    if reg_pad.exists():
        try:
            reg_cfg = json.loads(reg_pad.read_text(encoding="utf-8"))
            n_reg = sum(1 for k in reg_cfg if not k.startswith("_"))
            if n_reg:
                regels.append(f"  Regelingen      {n_reg} actief")
        except Exception:
            pass

    # Waterschappen
    ws_pad = TOOLKIT_MAP / "bronnen" / "waterschappen.json"
    if ws_pad.exists():
        try:
            ws_cfg = json.loads(ws_pad.read_text(encoding="utf-8"))
            n_ws = sum(1 for k in ws_cfg if not k.startswith("_"))
            if n_ws:
                regels.append(f"  Waterschappen   {n_ws} geconfigureerd")
        except Exception:
            pass

    # Veiligheidsregio's
    vr_pad = TOOLKIT_MAP / "bronnen" / "veiligheidsregios.json"
    if vr_pad.exists():
        try:
            vr_cfg = json.loads(vr_pad.read_text(encoding="utf-8"))
            n_vr = sum(
                1 for k, v in vr_cfg.items()
                if not k.startswith("_")
                and (OUTPUT_BASIS / "veiligheidsregios" / k).exists()
                and any((OUTPUT_BASIS / "veiligheidsregios" / k).rglob("*.pdf"))
            )
            if n_vr:
                regels.append(f"  Veiligheidsregio's  {n_vr} gedownload")
        except Exception:
            pass

    # Provincies
    prov_pad = TOOLKIT_MAP / "bronnen" / "provincies.json"
    if prov_pad.exists():
        try:
            prov_cfg = json.loads(prov_pad.read_text(encoding="utf-8"))
            n_prov = sum(
                1 for k, v in prov_cfg.items()
                if not k.startswith("_")
                and (OUTPUT_BASIS / "provincies" / k).exists()
                and any((OUTPUT_BASIS / "provincies" / k).rglob("*.pdf"))
            )
            if n_prov:
                regels.append(f"  Provincies      {n_prov} gedownload")
        except Exception:
            pass

    if regels:
        print()
        print("Actieve bronnen:")
        for r in regels:
            print(r)


def nieuw_dossier():
    """Interactieve wizard voor een nieuw dossier."""
    print()
    print("Nieuw dossier aanmaken")
    print("─" * 50)
    print()

    naam = vraag("Naam van het dossier (bijv. woningbouw, grond, jeugdzorg)")
    naam = naam.lower().replace(" ", "-")

    dossier_pad = DOSSIERS_MAP / f"{naam}.json"
    if dossier_pad.exists():
        print(f"\n  Let op: dossier '{naam}' bestaat al.")
        keuze = input("  Overschrijven? (j/n): ").strip().lower()
        if keuze != "j":
            print("  Afgebroken.")
            return

    label = vraag("Label voor rapporten", naam)

    # Kies orgaan uit beschikbare orgaan-configs
    organen = lees_organen()
    if organen:
        print()
        print(f"  Beschikbare organen: {', '.join(organen)}")
        orgaan = vraag("Orgaan (naam uit bovenstaande lijst, of nieuw)").lower()
    else:
        print()
        print("  Nog geen organen aangemaakt. Voer eerst 'python3 toolkit.py nieuwe-gemeente' uit.")
        orgaan = vraag("Orgaannaam (bijv. rotterdam, hollandse-delta)").lower()

    print()
    print("  Trefwoorden — typ ze één voor één in, lege regel om te stoppen:")
    print()
    trefwoorden = []
    while True:
        woord = input(f"    Trefwoord {len(trefwoorden) + 1}: ").strip().lower()
        if not woord:
            if trefwoorden:
                break
            print("    (voer minimaal één trefwoord in)")
        else:
            trefwoorden.append(woord)

    config = {
        "label": label,
        "orgaan": orgaan,
        "trefwoorden": trefwoorden,
    }

    DOSSIERS_MAP.mkdir(exist_ok=True)
    dossier_pad.write_text(json.dumps(config, indent=2, ensure_ascii=False), encoding="utf-8")

    print()
    print(f"  ✓ Dossier opgeslagen: {dossier_pad}")

    log_pad = OUTPUT_BASIS / orgaan / "logs" / f"analyse-{naam}.log"
    cron_regel = (
        f"30 9 * * 3 {PYTHON} {TOOLKIT_MAP / 'analyse.py'} "
        f"--dossier {naam} >> {log_pad} 2>&1"
    )
    voeg_crontabregel_toe(f"Analyse dossier {naam} — {orgaan}", cron_regel)

    print()
    print(f"  Direct uitvoeren:")
    print(f"  python3 analyse.py --dossier {naam}")
    print()


# ── Notubiz-catalogus ─────────────────────────────────────────────────────────

_NOTUBIZ_PREFIXES = re.compile(
    r"^(gemeenschappelijke?\s+regeling\s*[-–]?\s*"
    r"|samenwerkingsverband\s+"
    r"|samenwerkingsorgaan\s+"
    r"|uitvoeringsorganisatie\s+)",
    re.IGNORECASE,
)

_NOTUBIZ_RUIS = re.compile(
    r"\b(demo|test|pilot|zzz|zz|sales|circle|poc|screencasts|presentatie)\b",
    re.IGNORECASE,
)


def _normaliseer_gr_naam(naam: str) -> str:
    """Strip bekende prefixen en normaliseer voor vergelijking."""
    naam = _NOTUBIZ_PREFIXES.sub("", naam.strip())
    return re.sub(r"[\s\-_]+", " ", naam.lower()).strip()


def laad_notubiz_catalogus() -> dict[str, dict]:
    """Laad de Notubiz-organisatiecatalogus; bouw opnieuw als ouder dan 30 dagen.

    Geeft {genormaliseerde_naam: {"id": int, "naam": str}}.
    """
    pad = TOOLKIT_MAP / "bronnen" / "notubiz_catalogus.json"
    if pad.exists():
        try:
            data = json.loads(pad.read_text(encoding="utf-8"))
            if data.get("_gebouwd"):
                gebouwd = datetime.fromisoformat(data["_gebouwd"])
                if gebouwd.tzinfo is None:
                    gebouwd = gebouwd.replace(tzinfo=timezone.utc)
                if (datetime.now(tz=timezone.utc) - gebouwd).days < 30:
                    return {k: v for k, v in data.items() if not k.startswith("_")}
        except Exception:
            pass

    return _bouw_notubiz_catalogus(pad)


def _bouw_notubiz_catalogus(pad: Path) -> dict[str, dict]:
    """Haal alle Notubiz-organisaties op en sla op als lookup-tabel."""
    try:
        url = "https://api.notubiz.nl/organisations?format=json&version=1.17.0"
        req = urllib.request.Request(
            url, headers={"Accept": "application/json", "User-Agent": "Mozilla/5.0"}
        )
        with urllib.request.urlopen(req, timeout=15) as r:
            data = json.loads(r.read())
        orgs = data["organisations"]["organisation"]
    except Exception:
        return {}

    catalogus: dict[str, dict] = {}
    for org in orgs:
        naam = org.get("name", "").strip()
        org_id = org.get("@attributes", {}).get("id")
        if not naam or not org_id:
            continue
        if _NOTUBIZ_RUIS.search(naam):
            continue
        norm = _normaliseer_gr_naam(naam)
        if len(norm) < 3:
            continue
        catalogus[norm] = {"id": org_id, "naam": naam}

    catalogus["_gebouwd"] = datetime.now(tz=timezone.utc).isoformat()
    pad.write_text(json.dumps(catalogus, indent=2, ensure_ascii=False), encoding="utf-8")
    return {k: v for k, v in catalogus.items() if not k.startswith("_")}


def zoek_notubiz_id(naam: str) -> dict | None:
    """Zoek een Notubiz-organisatie op naam. Geeft {"id", "naam"} of None."""
    catalogus = laad_notubiz_catalogus()
    if not catalogus:
        return None
    zoek = _normaliseer_gr_naam(naam)
    # Exacte match
    if zoek in catalogus:
        return catalogus[zoek]
    # Substring-match: zoekterm bevat catalogusnaam of omgekeerd
    for norm, entry in catalogus.items():
        if len(norm) < 4:
            continue
        if norm in zoek or zoek in norm:
            return entry
    return None


def ververs_notubiz_catalogus():
    """Forceer verversing van de Notubiz-organisatiecatalogus."""
    pad = TOOLKIT_MAP / "bronnen" / "notubiz_catalogus.json"
    print("\n  Notubiz-catalogus ophalen…")
    resultaat = _bouw_notubiz_catalogus(pad)
    if resultaat:
        print(f"  ✓ {len(resultaat)} organisaties opgeslagen in bronnen/notubiz_catalogus.json")
    else:
        print("  Mislukt — controleer je internetverbinding.")
    print()


# ── GR-detectie via overheid.nl ───────────────────────────────────────────────

# ── Brondata-beheer ───────────────────────────────────────────────────────────

def _brondata_leeftijd_dagen():
    """Geef het aantal dagen sinds de laatste GR-index-update, of None als onbekend."""
    if not GR_INDEX_PAD.exists():
        return None
    try:
        data = json.loads(GR_INDEX_PAD.read_text(encoding="utf-8"))
        gegenereerd = data.get("_gegenereerd", "")
        if gegenereerd:
            dt = datetime.strptime(gegenereerd, "%Y-%m-%d").replace(tzinfo=timezone.utc)
            return (datetime.now(timezone.utc) - dt).days
    except Exception:
        pass
    return None


def _controleer_brondata():
    """Waarschuw als de GR-index verouderd is en bied aan om bij te werken."""
    dagen = _brondata_leeftijd_dagen()
    if dagen is None or dagen < VEROUDERD_DREMPEL_DAGEN:
        return

    maanden = round(dagen / 30)
    print()
    print(f"  Let op: de GR-index is {maanden} maanden oud.")
    print(f"  Nieuwe of hernoemde gemeenschappelijke regelingen worden")
    print(f"  mogelijk niet herkend. Bijwerken duurt enkele seconden.")
    print()
    antwoord = input("  Nu bijwerken? (j/n) [j]: ").strip().lower() or "j"
    if antwoord == "j":
        brondata_bijwerken(stil=False)
    else:
        print()


def brondata_bijwerken(stil=False):
    """Ververs de GR-index en vul ontbrekende overheid_ids bij in regelingen.json."""
    if not stil:
        print()
        print("  Brondata bijwerken…")
    script = TOOLKIT_MAP / "bouw_gr_index.py"
    result = subprocess.run([PYTHON, str(script), "--update-catalogus"])
    if result.returncode != 0 and not stil:
        print("  ! Bijwerken mislukt. Controleer je internetverbinding.")
    if not stil:
        print()


def haal_grs_voor_gemeente(slug: str) -> list[dict]:
    """Haal de GRs op waaraan een gemeente deelneemt via organisaties.overheid.nl."""
    mapping_pad = TOOLKIT_MAP / "bronnen" / "gemeenten_overheid.json"
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
        return []

    # Laad GR-index voor nette namen (indien beschikbaar)
    gr_index = {}
    if GR_INDEX_PAD.exists():
        try:
            gr_index = {
                k: v for k, v in
                json.loads(GR_INDEX_PAD.read_text(encoding="utf-8")).items()
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

        gr_slug = re.sub(r"^gemeenschappelijk[e]?-regeling-", "", slug_raw.lower().replace("_", "-"))
        grs.append({
            "slug": gr_slug,
            "naam": naam,
            "overheid_id": overheid_gr_id,
        })
    return grs


def nieuwe_gemeente():
    """Gids voor het toevoegen van een nieuw orgaan (gemeente, waterschap of GR)."""
    print()
    print("Nieuw orgaan toevoegen")
    print("─" * 50)
    print()

    orgaan = vraag("Naam van het orgaan (bijv. rotterdam, hollandse-delta)").lower()

    print()
    print("  Type orgaan:")
    print("    1  gemeente")
    print("    2  waterschap")
    print("    3  gemeenschappelijke regeling (GR)")
    print("    4  provincie")
    keuze_type = input("  Keuze [1]: ").strip() or "1"
    type_map = {"1": "gemeente", "2": "waterschap", "3": "gr", "4": "provincie"}
    orgaan_type = type_map.get(keuze_type, "gemeente")

    standaard = VERGADERTYPEN_PER_TYPE[orgaan_type]
    print()
    print(f"  Standaard vergadertypen voor {orgaan_type}:")
    for vt in standaard:
        print(f"    - {vt}")
    keuze_vt = input("  Gebruik deze vergadertypen? (j/n) [j]: ").strip().lower() or "j"
    if keuze_vt == "j":
        vergadertypen = standaard
    else:
        print("  Typ vergadertypen één voor één in, lege regel om te stoppen:")
        vergadertypen = []
        while True:
            vt = input(f"    Vergadertype {len(vergadertypen) + 1}: ").strip().lower()
            if not vt:
                if vergadertypen:
                    break
                print("    (voer minimaal één vergadertype in)")
            else:
                vergadertypen.append(vt)

    # Sla orgaan-config op
    orgaan_config = {
        "naam": orgaan.capitalize(),
        "type": orgaan_type,
        "bron": "ori",
        "vergadertypen": vergadertypen,
    }
    ORGANEN_MAP.mkdir(exist_ok=True)
    orgaan_pad = ORGANEN_MAP / f"{orgaan}.json"
    orgaan_pad.write_text(json.dumps(orgaan_config, indent=2, ensure_ascii=False), encoding="utf-8")
    print()
    print(f"  ✓ Orgaan-config opgeslagen: {orgaan_pad}")

    jaren_arg = vraag_terugkijkperiode()

    print()
    keuze_droog = input("  Eerst droog uitvoeren (wat zou er gedownload worden)? (j/n): ").strip().lower()
    if keuze_droog == "j":
        subprocess.run([PYTHON, str(TOOLKIT_MAP / "scraper.py"), orgaan, "--droog"] + jaren_arg)
        print()
        keuze_dl = input("  Nu echt downloaden? (j/n): ").strip().lower()
        if keuze_dl != "j":
            print("  Gestopt na droog uitvoeren.")
            print(f"  Downloaden later: python3 scraper.py {orgaan} {' '.join(jaren_arg)}")
            print()
            return

    subprocess.run([PYTHON, str(TOOLKIT_MAP / "scraper.py"), orgaan] + jaren_arg)

    log_pad = OUTPUT_BASIS / orgaan / "logs" / "scraper.log"
    cron_scraper = (
        f"0 9 * * 3 {PYTHON} {TOOLKIT_MAP / 'scraper.py'} {orgaan} >> {log_pad} 2>&1"
        f" && {PYTHON} {TOOLKIT_MAP / 'index.py'} {orgaan} >> {log_pad} 2>&1"
    )
    voeg_crontabregel_toe(f"Scraper + index — {orgaan}", cron_scraper)

    # GR-suggesties voor gemeenten
    if orgaan_type == "gemeente":
        print()
        print("  GRs opzoeken voor deze gemeente…")
        grs = haal_grs_voor_gemeente(orgaan)
        if grs:
            print(f"  {len(grs)} gemeenschappelijke regelingen gevonden voor {orgaan}:")
            print()
            for i, gr in enumerate(grs, 1):
                print(f"    {i:2}.  {gr['naam']}")
            print()
            keuze_grs = input("  Welke wil je toevoegen aan de catalogus? (nummers, kommagescheiden, of leeglaten): ").strip()
            if keuze_grs:
                gekozen = []
                for deel in keuze_grs.split(","):
                    try:
                        idx = int(deel.strip()) - 1
                        if 0 <= idx < len(grs):
                            gekozen.append(grs[idx])
                    except ValueError:
                        pass

                if gekozen:
                    reg_pad = TOOLKIT_MAP / "bronnen" / "regelingen.json"
                    try:
                        reg_config = json.loads(reg_pad.read_text(encoding="utf-8"))
                    except Exception:
                        reg_config = {}

                    print()
                    handmatig = []
                    for gr in gekozen:
                        bestaand = reg_config.get(gr["slug"], {})
                        deelnemers = bestaand.get("deelnemers", [])
                        if orgaan not in deelnemers:
                            deelnemers.append(orgaan)

                        notubiz = zoek_notubiz_id(gr["naam"]) if not bestaand.get("notubiz_id") else None
                        if notubiz:
                            reg_config[gr["slug"]] = {
                                **bestaand,
                                "naam": gr["naam"],
                                "notubiz_id": notubiz["id"],
                                "deelnemers": deelnemers,
                            }
                            print(f"  ✓ {gr['naam']} — Notubiz-ID {notubiz['id']} automatisch gevonden")
                        else:
                            reg_config[gr["slug"]] = {
                                **bestaand,
                                "naam": gr["naam"],
                                "brontype": bestaand.get("brontype", "geen"),
                                "deelnemers": deelnemers,
                            }
                            print(f"  ✓ {gr['naam']} — brontype onbekend (niet gevonden in Notubiz)")
                            handmatig.append(gr["naam"])

                    reg_pad.write_text(json.dumps(reg_config, indent=2, ensure_ascii=False), encoding="utf-8")
                    if handmatig:
                        print()
                        print("  Controleer voor deze GRs handmatig of ze via iBabs of een eigen portaal publiceren:")
                        for naam in handmatig:
                            print(f"    - {naam}")
        elif orgaan in json.loads((TOOLKIT_MAP / "bronnen" / "gemeenten_overheid.json").read_text(encoding="utf-8")):
            print("  Geen GRs gevonden (of verbinding mislukt). Voeg later toe via: python3 toolkit.py nieuwe-regeling")
        else:
            print(f"  Gemeente '{orgaan}' niet gevonden in de mapping — GR-suggesties niet beschikbaar.")
            print("  Voeg later handmatig toe via: python3 toolkit.py nieuwe-regeling")

    print()
    print(f"  Volgende stap: dossier aanmaken voor {orgaan}")
    print(f"  python3 toolkit.py nieuw-dossier")
    print()


def nieuwe_regeling():
    """Wizard: voeg een gemeenschappelijke regeling toe aan bronnen/regelingen.json."""
    print()
    print("Nieuwe gemeenschappelijke regeling toevoegen")
    print("─" * 50)
    print()
    print("  Tip: gebruik eerst 'python3 scraper_gr.py --lijst-ori' om te zien")
    print("  welke GRs beschikbaar zijn in de ORI API.")
    print()

    slug = vraag("Slug (bijv. drechtsteden, veiligheidsregio-rotterdam)").lower()
    naam = vraag("Volledige naam (bijv. Drechtsteden)")
    ori_index = vraag("ORI-indexnaam (naam zonder 'ori_'-prefix en tijdstempel)")

    print()
    print("  Vergadertypen — typ ze één voor één in, lege regel voor standaard:")
    print("  (standaard: algemeen bestuur, dagelijks bestuur, portefeuillehoudersoverleg)")
    print()
    vergadertypen = []
    while True:
        vtype = input(f"    Vergadertype {len(vergadertypen) + 1}: ").strip().lower()
        if not vtype:
            break
        vergadertypen.append(vtype)

    if not vergadertypen:
        vergadertypen = ["algemeen bestuur", "dagelijks bestuur", "portefeuillehoudersoverleg"]

    pad = TOOLKIT_MAP / "bronnen" / "regelingen.json"
    try:
        config = json.loads(pad.read_text(encoding="utf-8"))
    except Exception:
        config = {}

    config[slug] = {
        "naam": naam,
        "ori_index": ori_index,
        "vergadertypen": vergadertypen,
    }

    pad.write_text(json.dumps(config, indent=2, ensure_ascii=False), encoding="utf-8")

    print()
    print(f"  ✓ Opgeslagen in: {pad}")
    print()
    keuze_dl = input("  Wil je de vergaderstukken nu downloaden? (j/n): ").strip().lower()
    if keuze_dl == "j":
        jaren_arg = vraag_terugkijkperiode()
        print()
        subprocess.run([PYTHON, str(TOOLKIT_MAP / "scraper_gr.py"), slug] + jaren_arg)
    else:
        print(f"  Downloaden later: python3 scraper_gr.py {slug} --jaren 2")
    print()


def nieuw_waterschap():
    """Wizard: voeg een waterschap toe aan bronnen/waterschappen.json."""
    print()
    print("Nieuw waterschap toevoegen")
    print("─" * 50)
    print()
    print("  Tip: gebruik eerst 'python3 scraper_waterschap.py --lijst-ori' om te zien")
    print("  welke waterschappen beschikbaar zijn in de ORI API.")
    print()

    slug = vraag("Slug (bijv. hollandse-delta, delfland)").lower()
    naam = vraag("Volledige naam (bijv. Waterschap Hollandse Delta)")
    ori_index = vraag("ORI-indexnaam (naam zonder 'owi_'-prefix en tijdstempel)")

    print()
    print("  Vergadertypen — typ ze één voor één in, lege regel voor standaard:")
    print("  (standaard: algemeen bestuur, college van dijkgraaf en heemraden)")
    print()
    vergadertypen = []
    while True:
        vtype = input(f"    Vergadertype {len(vergadertypen) + 1}: ").strip().lower()
        if not vtype:
            break
        vergadertypen.append(vtype)

    if not vergadertypen:
        vergadertypen = ["algemeen bestuur", "college van dijkgraaf en heemraden"]

    pad = TOOLKIT_MAP / "bronnen" / "waterschappen.json"
    try:
        config = json.loads(pad.read_text(encoding="utf-8"))
    except Exception:
        config = {}

    config[slug] = {
        "naam": naam,
        "ori_index": ori_index,
        "vergadertypen": vergadertypen,
    }

    pad.write_text(json.dumps(config, indent=2, ensure_ascii=False), encoding="utf-8")

    print()
    print(f"  ✓ Opgeslagen in: {pad}")
    print()
    keuze_dl = input("  Wil je de vergaderstukken nu downloaden? (j/n): ").strip().lower()
    if keuze_dl == "j":
        jaren_arg = vraag_terugkijkperiode()
        print()
        subprocess.run([PYTHON, str(TOOLKIT_MAP / "scraper_waterschap.py"), slug] + jaren_arg)
    else:
        print(f"  Downloaden later: python3 scraper_waterschap.py {slug} --jaren 2")
    print()


def nieuwe_provincie():
    """Wizard: voeg een provincie toe of pas de configuratie aan."""
    print()
    print("Provincie configureren")
    print("─" * 50)
    print()

    pad = TOOLKIT_MAP / "bronnen" / "provincies.json"
    try:
        config = json.loads(pad.read_text(encoding="utf-8"))
    except Exception:
        config = {}

    provincies = {k: v for k, v in config.items() if not k.startswith("_")}
    beschikbaar = [(s, p) for s, p in sorted(provincies.items())
                   if p.get("ori_index") or p.get("notubiz_id")]

    if not beschikbaar:
        print("  Geen provincies met geautomatiseerde bron gevonden.")
        return

    print("  Beschikbare provincies:\n")
    for i, (slug, info) in enumerate(beschikbaar, 1):
        naam = info.get("naam", slug)
        if "ori_index" in info:
            bron = "ORI"
        elif "notubiz_id" in info:
            bron = "Notubiz"
        else:
            bron = "?"
        print(f"    {i:2}.  {naam:<30} ({bron})")

    print()
    keuze = input("  Welke provincie wil je downloaden? (nummer): ").strip()
    try:
        idx = int(keuze) - 1
        if 0 <= idx < len(beschikbaar):
            slug = beschikbaar[idx][0]
            print()
            subprocess.run([PYTHON, str(TOOLKIT_MAP / "scraper_provincie.py"), slug])
        else:
            print("  Ongeldig nummer.")
    except ValueError:
        print("  Ongeldig nummer.")
    print()


def scrape_provincies():
    """Download nieuwe vergaderstukken voor alle geconfigureerde provincies."""
    pad = TOOLKIT_MAP / "bronnen" / "provincies.json"
    if not pad.exists():
        print("\nGeen bronnen/provincies.json gevonden.\n")
        return
    try:
        config = json.loads(pad.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"\nFout bij lezen provincies.json: {e}\n")
        return

    provincies = {k: v for k, v in config.items()
                  if not k.startswith("_") and (v.get("ori_index") or v.get("notubiz_id"))}
    if not provincies:
        print("\nGeen provincies met geautomatiseerde bron geconfigureerd.\n")
        return

    print(f"\n{len(provincies)} provincies scrapen…\n")
    for slug in provincies:
        print(f"  → {slug}")
        subprocess.run([PYTHON, str(TOOLKIT_MAP / "scraper_provincie.py"), slug])
        print()


def scrape_waterschappen():
    """Download nieuwe vergaderstukken voor alle geconfigureerde waterschappen."""
    pad = TOOLKIT_MAP / "bronnen" / "waterschappen.json"
    if not pad.exists():
        print("\nGeen bronnen/waterschappen.json gevonden. Voeg eerst een waterschap toe via: python3 toolkit.py nieuw-waterschap\n")
        return
    try:
        config = json.loads(pad.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"\nFout bij lezen waterschappen.json: {e}\n")
        return

    waterschappen = {k: v for k, v in config.items() if not k.startswith("_")}
    if not waterschappen:
        print("\nNog geen waterschappen geconfigureerd. Gebruik: python3 toolkit.py nieuw-waterschap\n")
        return

    print(f"\n{len(waterschappen)} waterschappen scrapen…\n")
    for slug in waterschappen:
        print(f"  → {slug}")
        subprocess.run([PYTHON, str(TOOLKIT_MAP / "scraper_waterschap.py"), slug])
        print()


def scrape_regelingen():
    """Download nieuwe vergaderstukken voor alle geconfigureerde GRs."""
    pad = TOOLKIT_MAP / "bronnen" / "regelingen.json"
    if not pad.exists():
        print("\nGeen bronnen/regelingen.json gevonden. Voeg eerst een GR toe via: python3 toolkit.py nieuwe-regeling\n")
        return
    try:
        config = json.loads(pad.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"\nFout bij lezen regelingen.json: {e}\n")
        return

    regelingen = {k: v for k, v in config.items() if not k.startswith("_")}
    if not regelingen:
        print("\nNog geen regelingen geconfigureerd. Gebruik: python3 toolkit.py nieuwe-regeling\n")
        return

    print(f"\n{len(regelingen)} regelingen scrapen…\n")
    for slug in regelingen:
        print(f"  → {slug}")
        subprocess.run([PYTHON, str(TOOLKIT_MAP / "scraper_gr.py"), slug])
        print()


def _genereer_briefing(gemeente: str, beschikbaar: list, ontbrekend: list, gevonden_grs: list | None = None) -> str:
    """Genereer een contextbriefing voor Claude Code bij een onderzoekssessie."""
    regels = []
    regels.append("## Onderzoekscontext — lokaalbestuur-toolkit")
    regels.append("")
    regels.append(
        f"Je helpt een journalist onderzoek doen naar **gemeente {gemeente.capitalize()}** "
        "en de bestuursorganen die daarmee samenwerken."
    )
    regels.append("")

    if beschikbaar:
        regels.append("### Beschikbare bronnen")
        regels.append("")
        for b in beschikbaar:
            type_labels = {
                "gemeente": "Gemeente",
                "gr": "Gemeenschappelijke regeling",
                "waterschap": "Waterschap",
                "veiligheidsregio": "Veiligheidsregio",
                "provincie": "Provincie",
            }
            label = type_labels.get(b["type"], b["type"])
            regels.append(f"**{b['naam']}** ({label}) — {b['n_docs']} documenten")
            regels.append(f"- Pad: `{b['pad']}`")
            if b["type"] == "gemeente" and b["index"]:
                regels.append(
                    f"- Doorzoekbaar via: "
                    f"`python3 {TOOLKIT_MAP}/index.py {gemeente} \"zoekterm\"`"
                )
            else:
                regels.append("- Lees PDF's direct via Read-tool of Bash")
            regels.append("")

    regels.append("### Domeinkennis over de bronnen")
    regels.append("")
    regels.append(
        "Gemeenschappelijke regelingen (GRs) zijn samenwerkingsverbanden tussen gemeenten. "
        "Ze behandelen taken die de gemeente heeft uitbesteed. Relevante domeinen per GR-type:"
    )
    regels.append("")
    regels.append("- **Jeugdhulp / jeugdzorg** → jeugd, opvoeding, gezondheid jongeren, obesitas")
    regels.append("- **Omgevingsdienst / milieu** → vergunningen, bouwen, luchtkwaliteit, bodem")
    regels.append("- **Veiligheidsregio** → brandweer, crisisbeheersing, rampenbestrijding")
    regels.append("- **Sociale dienst / werk** → bijstand, re-integratie, armoede")
    regels.append("- **GGD** → volksgezondheid, preventie, epidemiologie")
    regels.append("- **Metropoolregio / regio** → ruimtelijke ordening, mobiliteit, wonen")
    regels.append("")
    regels.append(
        "Waterschappen zijn relevant bij: waterveiligheid, dijken, klimaatadaptatie, "
        "grondwater, rioolwaterzuivering, stedelijk water."
    )
    regels.append("")
    regels.append(
        "Provincies zijn relevant bij: ruimtelijke ordening, natuur en stikstof, "
        "woningbouwafspraken, regionale infrastructuur (wegen, OV), economisch beleid, "
        "energietransitie, cultureel erfgoed en interbestuurlijk toezicht op gemeenten."
    )
    regels.append("")

    if gevonden_grs:
        regels.append(f"### Actieve GRs in {gemeente.capitalize()} (gedetecteerd uit vergaderstukken)")
        regels.append("")
        regels.append(
            "De volgende gemeenschappelijke regelingen komen voor in de beschikbare vergaderstukken. "
            "Raadpleeg hun documenten als je onderzoeksvraag raakvlakken heeft met hun domein:"
        )
        regels.append("")
        for gr in gevonden_grs:
            regels.append(f"- **{gr['naam']}** ({gr['vermeldingen']}× vermeld)")
        regels.append("")

    if ontbrekend:
        regels.append("### Bronnen in catalogus maar niet gedownload")
        regels.append("")
        regels.append(
            "De journalist heeft deze bronnen geconfigureerd maar nog niet gedownload. "
            "Meld dit als ze relevant zijn voor de onderzoeksvraag:"
        )
        regels.append("")
        for b in ontbrekend:
            regels.append(f"- {b['naam']} ({b['type']}) — `{b['commando']}`")
        regels.append("")

    regels.append("### Werkwijze")
    regels.append("")
    regels.append(
        "1. Gebruik `index.py` voor gerichte zoekopdrachten in gemeentedocumenten "
        "(snel, doorzoekt alle PDF's tegelijk)"
    )
    regels.append(
        "2. Lees PDF's van GRs en waterschappen direct als de onderzoeksvraag "
        "raakvlakken heeft met hun domein"
    )
    regels.append(
        "3. Raadsstukken bevatten formele besluiten en vergaderverslagen — "
        "ze vertellen wat er besloten is, niet altijd waarom"
    )
    regels.append(
        "4. Signaleer als je een relevant onderwerp tegenkomt dat niet in de "
        "beschikbare bronnen zit maar wel in een niet-gedownloade bron kan zitten"
    )
    regels.append("")
    regels.append("---")
    regels.append("")
    regels.append("**Onderzoeksvraag van de journalist:**")
    regels.append("")
    regels.append("[vul hier je vraag in]")
    regels.append("")
    regels.append("---")
    regels.append("")
    regels.append("### Wat kun je na je analyse doen?")
    regels.append("")
    regels.append("**Prompts** — plak de inhoud van het bestand in dit gesprek:")
    regels.append("")
    prompts_map = TOOLKIT_MAP / "prompts"
    uitgesloten = {"vrije-vraag.md"}
    for pad in sorted(prompts_map.glob("*.md")):
        if pad.name in uitgesloten:
            continue
        try:
            eerste_regel = pad.read_text(encoding="utf-8").splitlines()[0].lstrip("# ").strip()
        except Exception:
            eerste_regel = pad.stem
        regels.append(f"- `prompts/{pad.name}` — {eerste_regel}")
    regels.append("")
    regels.append("**Skills** — typ de opdracht in dit gesprek:")
    regels.append("")
    skills_map = TOOLKIT_MAP / ".claude" / "commands"
    for pad in sorted(skills_map.glob("*.md")):
        naam = pad.stem
        beschrijving = naam
        hint = ""
        try:
            tekst = pad.read_text(encoding="utf-8")
            for regel in tekst.splitlines():
                if regel.startswith("description:"):
                    beschrijving = regel.split(":", 1)[1].strip()
                if regel.startswith("argument-hint:"):
                    hint = " " + regel.split(":", 1)[1].strip()
                if regel.strip() == "---" and beschrijving != naam:
                    break
        except Exception:
            pass
        regels.append(f"- `/{naam}{hint}` — {beschrijving}")

    return "\n".join(regels)


# ── GR-detectie ───────────────────────────────────────────────────────────────

def detecteer_regelingen_in_index(gemeente_map: Path) -> list[dict]:
    """Detecteer gemeenschappelijke regelingen via de zoekindex. Geeft [{naam, vermeldingen}]."""
    db_pad = gemeente_map / "index.db"
    if not db_pad.exists():
        return []
    try:
        con = sqlite3.connect(str(db_pad))
        rows = con.execute(
            "SELECT tekst FROM tekst_fts WHERE tekst MATCH ?",
            ("gemeenschappelijke regeling",)
        ).fetchall()
        con.close()
    except Exception:
        return []

    teller: dict[str, int] = {}
    for (tekst,) in rows:
        matches = re.findall(
            r'Gemeenschappelijke\s+[Rr]egeling\s+([A-Z][^\n,(]{2,55}?)(?=\s*[\(,.\n]|\s{2}|$)',
            tekst
        )
        for m in matches:
            naam = re.sub(r'\s+', ' ', m).strip()
            # Strip staartwoorden die geen deel zijn van de naam
            naam = re.sub(r'\s+(van|de|het|en|voor|per|in|op|uit|aan|tot|over|door)\s*$', '', naam, flags=re.IGNORECASE)
            naam = naam.rstrip(' -–')
            # Sla over als naam speciale tekens, cijfers of te weinig woorden bevat
            if len(naam) < 4:
                continue
            if re.search(r'[€$%\d]', naam):
                continue
            if re.search(r'\d{4}', naam):
                continue
            teller[naam] = teller.get(naam, 0) + 1

    def _normaliseer(n: str) -> str:
        """Verwijder leestekens en lowercase voor vergelijking."""
        return re.sub(r'[\s\-_]+', ' ', n.lower().strip())

    # Dedupliceer: groepeer namen die na normalisatie op elkaar lijken
    namen = sorted(teller.keys(), key=lambda n: -teller[n])
    deduped: list[dict] = []
    for naam in namen:
        norm = _normaliseer(naam)
        vergelijkbaar = any(
            norm in _normaliseer(b["naam"]) or _normaliseer(b["naam"]) in norm
            for b in deduped
        )
        if not vergelijkbaar:
            deduped.append({"naam": naam, "vermeldingen": teller[naam]})
        else:
            # Tel vermeldingen mee bij de al opgenomen variant
            for b in deduped:
                if norm in _normaliseer(b["naam"]) or _normaliseer(b["naam"]) in norm:
                    b["vermeldingen"] += teller[naam]
                    break

    return sorted(deduped, key=lambda x: -x["vermeldingen"])


def _schrijf_regelingen_md(
    gemeente: str,
    gemeente_map: Path,
    regelingen: list[dict],
    officieel: list[dict] | None = None,
) -> Path:
    """Schrijf gevonden GRs naar regelingen.md en geef het pad terug.

    regelingen: gedetecteerd via zoekindex (met vermeldingen-telling)
    officieel:  lijst van overheid.nl ({naam, slug}) — officiële deelname
    """
    datum = datetime.now().strftime("%Y-%m-%d")
    totaal = sum(r["vermeldingen"] for r in regelingen)
    regels = [
        f"# Gemeenschappelijke regelingen — {gemeente.capitalize()}",
        "",
        f"Automatisch gedetecteerd op {datum} op basis van {totaal} vermeldingen in de vergaderstukken.",
        "",
        "| Naam | Vermeldingen |",
        "|------|-------------|",
    ]
    for r in regelingen:
        regels.append(f"| {r['naam']} | {r['vermeldingen']} |")

    # Voeg officiële GRs toe die niet in de stukken zijn gevonden
    if officieel:
        gevonden_namen_lower = {r["naam"].lower() for r in regelingen}
        niet_gevonden = [
            o for o in officieel
            if not any(o["naam"].lower() in gn or gn in o["naam"].lower()
                       for gn in gevonden_namen_lower)
        ]
        if niet_gevonden:
            regels += [
                "",
                "## Officieel deelnemer — niet aangetroffen in vergaderstukken",
                "",
                "| Naam |",
                "|------|",
            ]
            for o in niet_gevonden:
                regels.append(f"| {o['naam']} |")

    regels += [
        "",
        "---",
        "",
        f"Ververs met: `python3 toolkit.py onderzoek {gemeente} --ververs-regelingen`",
        "",
    ]
    pad = gemeente_map / "regelingen.md"
    pad.write_text("\n".join(regels), encoding="utf-8")
    return pad


def onderzoek(args: list):
    """Bereid een onderzoekssessie voor: bronnencheck, index bijwerken, Claude-briefing."""
    if not args:
        print("\nGebruik: python3 toolkit.py onderzoek <gemeente>\n")
        return

    ververs_gr = "--ververs-regelingen" in args
    args = [a for a in args if a != "--ververs-regelingen"]

    gemeente = args[0].lower()
    gemeente_map = OUTPUT_BASIS / gemeente

    print()
    print(f"Onderzoeksomgeving — {gemeente.capitalize()}")
    print("─" * 50)

    if not gemeente_map.exists() or not any(gemeente_map.rglob("*.pdf")):
        print(f"\n  ! Geen documenten gevonden voor '{gemeente}'.")
        print(f"    Download eerst: python3 scraper.py {gemeente}\n")
        return

    beschikbaar = []
    ontbrekend = []

    # Gemeente
    n_docs = sum(1 for _ in gemeente_map.rglob("*.pdf"))
    print(f"\n  Index bijwerken voor {gemeente}…")
    subprocess.run(
        [PYTHON, str(TOOLKIT_MAP / "index.py"), gemeente],
        capture_output=True,
    )
    index_aanwezig = (gemeente_map / "index.db").exists()
    beschikbaar.append({
        "naam": f"Gemeente {gemeente.capitalize()}",
        "type": "gemeente",
        "n_docs": n_docs,
        "pad": str(gemeente_map),
        "index": index_aanwezig,
        "slug": gemeente,
    })

    # GR-detectie via index + officiële deelname via overheid.nl
    regelingen_pad = gemeente_map / "regelingen.md"
    gevonden_grs: list[dict] = []
    if index_aanwezig and (not regelingen_pad.exists() or ververs_gr):
        print(f"  GRs detecteren in vergaderstukken…")
        gevonden_grs = detecteer_regelingen_in_index(gemeente_map)
        print(f"  Officiële GR-deelname ophalen via overheid.nl…")
        officieel = haal_grs_voor_gemeente(gemeente)
        _schrijf_regelingen_md(gemeente, gemeente_map, gevonden_grs, officieel)
        if gevonden_grs:
            print(f"  → {len(gevonden_grs)} gemeenschappelijke regelingen gevonden in stukken")
        else:
            print("  → Geen GRs gevonden in de stukken")
        if officieel:
            print(f"  → {len(officieel)} officiële GRs via overheid.nl")
        print(f"    Opgeslagen: {regelingen_pad}")
    elif regelingen_pad.exists():
        # Lees bestaande detectie voor de briefing
        for regel in regelingen_pad.read_text(encoding="utf-8").splitlines():
            m = re.match(r'\|\s+(.+?)\s+\|\s+(\d+)\s+\|', regel)
            if m and m.group(1) != "Naam":
                gevonden_grs.append({"naam": m.group(1), "vermeldingen": int(m.group(2))})

    # GRs
    reg_pad = TOOLKIT_MAP / "bronnen" / "regelingen.json"
    if reg_pad.exists():
        try:
            regelingen = {
                k: v for k, v in json.loads(reg_pad.read_text(encoding="utf-8")).items()
                if not k.startswith("_")
            }
            for slug, info in regelingen.items():
                deelnemers = info.get("deelnemers", [])
                if deelnemers and gemeente not in deelnemers:
                    continue
                naam = info.get("naam", slug)
                gr_map = OUTPUT_BASIS / "regelingen" / slug
                if gr_map.exists() and any(gr_map.rglob("*.pdf")):
                    n = sum(1 for _ in gr_map.rglob("*.pdf"))
                    beschikbaar.append({
                        "naam": naam, "type": "gr", "n_docs": n,
                        "pad": str(gr_map), "index": False, "slug": slug,
                    })
                else:
                    ontbrekend.append({
                        "naam": naam, "type": "gr",
                        "commando": f"python3 scraper_gr.py {slug}",
                    })
        except Exception:
            pass

    # Waterschappen
    ws_pad = TOOLKIT_MAP / "bronnen" / "waterschappen.json"
    if ws_pad.exists():
        try:
            waterschappen = {
                k: v for k, v in json.loads(ws_pad.read_text(encoding="utf-8")).items()
                if not k.startswith("_")
            }
            for slug, info in waterschappen.items():
                naam = info.get("naam", slug)
                ws_map = OUTPUT_BASIS / "waterschappen" / slug
                if ws_map.exists() and any(ws_map.rglob("*.pdf")):
                    n = sum(1 for _ in ws_map.rglob("*.pdf"))
                    beschikbaar.append({
                        "naam": naam, "type": "waterschap", "n_docs": n,
                        "pad": str(ws_map), "index": False, "slug": slug,
                    })
                else:
                    ontbrekend.append({
                        "naam": naam, "type": "waterschap",
                        "commando": f"python3 scraper_waterschap.py {slug}",
                    })
        except Exception:
            pass

    # Veiligheidsregio's
    vr_pad = TOOLKIT_MAP / "bronnen" / "veiligheidsregios.json"
    if vr_pad.exists():
        try:
            vr_config = {
                k: v for k, v in json.loads(vr_pad.read_text(encoding="utf-8")).items()
                if not k.startswith("_")
            }
            for slug, info in vr_config.items():
                if gemeente not in info.get("gemeenten", []):
                    continue
                naam = info.get("naam", slug)
                vr_map = OUTPUT_BASIS / "veiligheidsregios" / slug
                if vr_map.exists() and any(vr_map.rglob("*.pdf")):
                    n = sum(1 for _ in vr_map.rglob("*.pdf"))
                    beschikbaar.append({
                        "naam": naam, "type": "veiligheidsregio", "n_docs": n,
                        "pad": str(vr_map), "index": False, "slug": slug,
                    })
                else:
                    ontbrekend.append({
                        "naam": naam, "type": "veiligheidsregio",
                        "commando": f"python3 scraper_vr.py {slug}",
                    })
        except Exception:
            pass

    # Provincies
    prov_pad = TOOLKIT_MAP / "bronnen" / "provincies.json"
    if prov_pad.exists():
        try:
            prov_config = {
                k: v for k, v in json.loads(prov_pad.read_text(encoding="utf-8")).items()
                if not k.startswith("_")
            }
            for slug, info in prov_config.items():
                if gemeente not in info.get("gemeenten", []):
                    continue
                naam = info.get("naam", slug)
                prov_map = OUTPUT_BASIS / "provincies" / slug
                brontype = info.get("brontype", "")
                if brontype == "geen":
                    ontbrekend.append({
                        "naam": naam, "type": "provincie",
                        "commando": "(geen geautomatiseerde bron)",
                    })
                elif prov_map.exists() and any(prov_map.rglob("*.pdf")):
                    n = sum(1 for _ in prov_map.rglob("*.pdf"))
                    beschikbaar.append({
                        "naam": naam, "type": "provincie", "n_docs": n,
                        "pad": str(prov_map), "index": False, "slug": slug,
                    })
                else:
                    ontbrekend.append({
                        "naam": naam, "type": "provincie",
                        "commando": f"python3 scraper_provincie.py {slug}",
                    })
        except Exception:
            pass

    # Resultaat tonen
    print()
    if beschikbaar:
        print("  Beschikbare bronnen:\n")
        for b in beschikbaar:
            index_label = "  index ✓" if b.get("index") else ""
            print(f"  ✓  {b['naam']:<42} {b['n_docs']:>4} doc  {index_label}")

    if ontbrekend:
        print()
        print("  In catalogus, nog niet gedownload:\n")
        for b in ontbrekend:
            print(f"  ○  {b['naam']:<42} → {b['commando']}")

    briefing = _genereer_briefing(gemeente, beschikbaar, ontbrekend, gevonden_grs)

    context_pad = gemeente_map / "context.md"
    context_pad.write_text(briefing, encoding="utf-8")

    print()
    print("─" * 50)
    print()
    print("  Open Claude Code in de documentenmap:")
    print()
    print(f"    claude {gemeente_map}")
    print()
    print(f"  Contextbriefing opgeslagen als: {context_pad}")
    print("  Plak de inhoud vóór je vraag, of lees hem op in Claude met:")
    print()
    print(f"    Lees context.md")
    print()


def status():
    """Uitgebreid statusoverzicht per dossier."""
    print()
    print("Status — Lokaalbestuur Toolkit")
    print("─" * 50)

    dossiers = lees_dossiers()
    if not dossiers:
        print("\n  Geen dossiers gevonden.\n")
        return

    for d in dossiers:
        naam = d["_naam"]
        orgaan = orgaan_van_dossier(d)
        label = d.get("label", naam)
        trefwoorden = d.get("trefwoorden", [])
        run = laatste_run(orgaan, naam)

        docs_map = OUTPUT_BASIS / orgaan
        n_pdfs = len(list(docs_map.rglob("*.pdf"))) if docs_map.exists() else 0

        alerts_map = docs_map / "alerts"
        n_alerts = len(list(alerts_map.glob("alert-*.md"))) if alerts_map.exists() else 0

        preview = ", ".join(trefwoorden[:4]) + ("…" if len(trefwoorden) > 4 else "")

        print()
        print(f"  {naam}  ({orgaan})")
        print(f"    Label         : {label}")
        print(f"    Trefwoorden   : {len(trefwoorden)}  ({preview})")
        print(f"    Laatste run   : {run}")
        print(f"    PDF's in archief : {n_pdfs}")
        print(f"    Alertrapporten   : {n_alerts}")

    print()
    print("─" * 50)
    print()


def nieuw_alert(args: list):
    """
    Maak een dossier JSON en crontabregel aan op basis van opgegeven parameters.
    Bedoeld om door Claude aan te roepen na het opslaan van een analyserapport.

    Gebruik:
        python3 toolkit.py nieuw-alert --dossier naam --gemeente naam
                                       --trefwoorden "woord1,woord2,woord3"
                                       --frequentie wekelijks|maandelijks
    """

    def haal_arg(vlag: str) -> str:
        if vlag in args:
            idx = args.index(vlag)
            if idx + 1 < len(args):
                return args[idx + 1]
        return ""

    dossier_naam = haal_arg("--dossier").lower().replace(" ", "-")
    orgaan = haal_arg("--orgaan").lower() or haal_arg("--gemeente").lower()
    trefwoorden_raw = haal_arg("--trefwoorden")
    frequentie = haal_arg("--frequentie") or "wekelijks"

    # Valideer verplichte velden
    ontbrekend = [v for v, w in [("--dossier", dossier_naam), ("--orgaan", orgaan), ("--trefwoorden", trefwoorden_raw)] if not w]
    if ontbrekend:
        print(f"\nFout: ontbrekende argumenten: {', '.join(ontbrekend)}")
        print("Gebruik: python3 toolkit.py nieuw-alert --dossier naam --orgaan naam --trefwoorden \"woord1,woord2\" --frequentie wekelijks")
        sys.exit(1)

    trefwoorden = [t.strip().lower() for t in trefwoorden_raw.split(",") if t.strip()]

    # Stel crontab-timing in
    if frequentie == "maandelijks":
        cron_tijdstip = "30 9 1 * *"
        frequentie_label = "maandelijks (1e van de maand)"
    else:
        cron_tijdstip = "30 9 * * 3"
        frequentie_label = "wekelijks (woensdag)"

    # Maak dossier JSON aan
    dossier_pad = DOSSIERS_MAP / f"{dossier_naam}.json"
    if dossier_pad.exists():
        print(f"\n  Let op: dossier '{dossier_naam}' bestaat al en wordt overschreven.")

    config = {
        "label": dossier_naam,
        "orgaan": orgaan,
        "trefwoorden": trefwoorden,
    }

    DOSSIERS_MAP.mkdir(exist_ok=True)
    dossier_pad.write_text(json.dumps(config, indent=2, ensure_ascii=False), encoding="utf-8")

    # Voeg crontabregel toe
    log_pad = OUTPUT_BASIS / orgaan / "logs" / f"analyse-{dossier_naam}.log"
    cron_regel = (
        f"{cron_tijdstip} {PYTHON} {TOOLKIT_MAP / 'analyse.py'} "
        f"--dossier {dossier_naam} >> {log_pad} 2>&1"
    )

    result = subprocess.run(["crontab", "-l"], capture_output=True, text=True)
    bestaand = result.stdout if result.returncode == 0 else ""

    if cron_regel not in bestaand:
        nieuw = bestaand.rstrip() + f"\n\n# Alert: {dossier_naam} — {orgaan}\n{cron_regel}\n"
        subprocess.run(["crontab", "-"], input=nieuw, text=True, check=True)

    # Bevestiging
    print()
    print(f"  ✓ Dossier aangemaakt : {dossier_pad}")
    print(f"  ✓ Trefwoorden        : {', '.join(trefwoorden)}")
    print(f"  ✓ Orgaan             : {orgaan}")
    print(f"  ✓ Frequentie         : {frequentie_label}")
    print(f"  ✓ Crontabregel       : toegevoegd")
    print()
    print(f"  De eerste alert verschijnt na de eerstvolgende geplande run")
    print(f"  in: ~/Documents/notulen/{orgaan}/alerts/")
    print()


def setup():
    """Interactieve installatie: controleer vereisten, installeer afhankelijkheden, configureer paden."""
    print()
    print("Lokaalbestuur Toolkit — installatie")
    print("─" * 50)
    print()

    fouten = 0

    # 1. Python-versie
    v = sys.version_info
    if v >= (3, 10):
        print(f"  ✓ Python {v.major}.{v.minor}")
    else:
        print(f"  ✗ Python {v.major}.{v.minor} — versie 3.10 of hoger vereist.")
        print("    Installeer een nieuwere versie via https://www.python.org/downloads/")
        print("    en start setup opnieuw.")
        sys.exit(1)

    # 2. pdfplumber
    try:
        import pdfplumber  # noqa: F401
        print("  ✓ pdfplumber al geïnstalleerd")
    except ImportError:
        print("  … pdfplumber installeren…")
        result = subprocess.run(
            [PYTHON, "-m", "pip", "install", "pdfplumber"],
            capture_output=True, text=True,
        )
        if result.returncode == 0:
            print("  ✓ pdfplumber geïnstalleerd")
        else:
            print("  ✗ pdfplumber installatie mislukt:")
            for regel in result.stderr.strip().splitlines()[-3:]:
                print(f"    {regel}")
            fouten += 1

    # 3. API bereikbaar
    print("  … verbinding met Open Raadsinformatie API testen…")
    try:
        urllib.request.urlopen(
            "https://api.openraadsinformatie.nl/v1/elastic/_cat/indices?h=index&format=json",
            timeout=10,
        )
        print("  ✓ API bereikbaar")
    except Exception:
        print("  ✗ API niet bereikbaar — controleer je internetverbinding.")
        print("    De toolkit heeft internet nodig om documenten te downloaden.")
        fouten += 1

    # 4. Documentenmap instellen
    config_pad = TOOLKIT_MAP / "config.local.json"
    standaard_map = Path.home() / "Documents" / "notulen"

    if config_pad.exists():
        bestaand = _lees_config()
        huidige_map = Path(bestaand["data_map"]).expanduser() if "data_map" in bestaand else standaard_map
        print(f"  ✓ Documentenmap al ingesteld: {huidige_map}")
    else:
        print()
        print("  Waar wil je de gedownloade documenten opslaan?")
        print(f"  Druk Enter voor de standaardmap: {standaard_map}")
        print()
        keuze = input(f"  Documentenmap [{standaard_map}]: ").strip()
        gekozen_map = Path(keuze).expanduser() if keuze else standaard_map

        gekozen_map.mkdir(parents=True, exist_ok=True)

        config_pad.write_text(
            json.dumps({"data_map": str(gekozen_map)}, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        print(f"  ✓ Configuratie opgeslagen: {config_pad}")
        print(f"    Documenten komen in: {gekozen_map}")

    # 5. Samenvatting
    print()
    print("─" * 50)

    if fouten:
        print(f"  {fouten} probleem(en) gevonden. Los deze op en draai setup opnieuw.")
    else:
        print("  ✓ Installatie compleet. De toolkit is klaar voor gebruik.")
        print()
        print("  Volgende stap — kies een gemeente en verken wat er beschikbaar is:")
        print()
        print("    python3 toolkit.py verkennen <gemeente>")
        print()
        print("  Bijvoorbeeld:")
        print()
        print("    python3 toolkit.py verkennen rotterdam")
        print("    python3 toolkit.py verkennen groningen")
        print("    python3 toolkit.py verkennen veere")

    print()


def check():
    """Controleer of de toolkit correct is geïnstalleerd en klaar voor gebruik."""
    print()
    print("Installatiecheck — Lokaalbestuur Toolkit")
    print("─" * 50)
    print()

    fouten = 0

    # Python-versie
    v = sys.version_info
    if v >= (3, 10):
        print(f"  ✓ Python {v.major}.{v.minor}")
    else:
        print(f"  ✗ Python {v.major}.{v.minor} — versie 3.10 of hoger vereist")
        fouten += 1

    # pdfplumber
    try:
        import pdfplumber  # noqa: F401
        print("  ✓ pdfplumber geïnstalleerd")
    except ImportError:
        print("  ✗ pdfplumber niet gevonden — installeer met: pip install pdfplumber")
        fouten += 1

    # API bereikbaar
    try:
        urllib.request.urlopen(
            "https://api.openraadsinformatie.nl/v1/elastic/_cat/indices?h=index&format=json",
            timeout=10
        )
        print("  ✓ Open Raadsinformatie API bereikbaar")
    except Exception:
        print("  ✗ Open Raadsinformatie API niet bereikbaar — controleer je internetverbinding")
        fouten += 1

    # Organen
    organen = lees_organen()
    if organen:
        print(f"  ✓ {len(organen)} orgaan-config(s) gevonden: {', '.join(organen)}")
    else:
        print("  ! Geen organen aangemaakt — gebruik: python3 toolkit.py nieuw-orgaan")

    # Dossiers
    dossiers = lees_dossiers()
    if dossiers:
        print(f"  ✓ {len(dossiers)} dossier(s) gevonden: {', '.join(d['_naam'] for d in dossiers)}")
        # Controleer of elk dossier verwijst naar een bestaand orgaan
        ontbrekende_organen = [
            d["_naam"] for d in dossiers
            if orgaan_van_dossier(d) != "—" and orgaan_van_dossier(d) not in organen
        ]
        if ontbrekende_organen:
            for naam in ontbrekende_organen:
                print(f"  ! Dossier '{naam}' verwijst naar een orgaan zonder config — gebruik: python3 toolkit.py nieuw-orgaan")
    else:
        print("  ! Geen dossiers aangemaakt — gebruik: python3 toolkit.py nieuw-dossier")

    # Crontab
    result = subprocess.run(["crontab", "-l"], capture_output=True, text=True)
    crontab = result.stdout
    if "scraper.py" in crontab:
        scraper_zonder_index = [
            r for r in crontab.splitlines()
            if "scraper.py" in r and "index.py" not in r and not r.startswith("#")
        ]
        if scraper_zonder_index:
            print("  ! Scraper-crontab aanwezig maar zonder zoekindex-stap — herstel met: python3 toolkit.py fix-cron")
        else:
            print("  ✓ Crontab scraper + index aanwezig")
    else:
        print("  ! Geen scraper-crontab — gebruik: python3 toolkit.py nieuw-orgaan")
    if "analyse.py" in crontab:
        print("  ✓ Crontab analyse aanwezig")
    else:
        print("  ! Geen analyse-crontab — gebruik: python3 toolkit.py nieuw-dossier")

    # Archief
    if OUTPUT_BASIS.exists():
        archieven = [p.name for p in OUTPUT_BASIS.iterdir() if p.is_dir()]
        if archieven:
            print(f"  ✓ Archief aanwezig voor: {', '.join(archieven)}")
        else:
            print("  ! Archiefmap bestaat maar is leeg — run eerst: python3 scraper.py <orgaan>")
    else:
        print("  ! Nog geen documenten gedownload — run eerst: python3 scraper.py <orgaan>")

    print()
    print("─" * 50)
    if fouten == 0:
        print("  Alles in orde. De toolkit is klaar voor gebruik.")
    else:
        print(f"  {fouten} probleem/problemen gevonden. Los deze op voor je begint.")
    print()


def scrape(args: list):
    """Download nieuwe vergaderstukken voor een orgaan of alle organen."""
    if not args or args[0] == "--alles":
        # Alle geconfigureerde organen
        organen = lees_organen()
        if not organen:
            print("\nGeen organen geconfigureerd. Gebruik: python3 toolkit.py nieuw-orgaan\n")
            return
        print(f"\n{len(organen)} organen bijwerken…\n")
        for slug in organen:
            pad = ORGANEN_MAP / f"{slug}.json"
            try:
                cfg = json.loads(pad.read_text(encoding="utf-8"))
                orgaan_type = cfg.get("type", "gemeente")
            except Exception:
                orgaan_type = "gemeente"
            _scrape_orgaan(slug, orgaan_type)
        return

    slug = args[0].lower()
    droog = "--droog" in args

    # Zoek orgaantype op in config
    orgaan_pad = ORGANEN_MAP / f"{slug}.json"
    if orgaan_pad.exists():
        try:
            cfg = json.loads(orgaan_pad.read_text(encoding="utf-8"))
            orgaan_type = cfg.get("type", "gemeente")
        except Exception:
            orgaan_type = "gemeente"
    else:
        # Probeer te raden uit bronnen-catalogussen
        reg_pad = TOOLKIT_MAP / "bronnen" / "regelingen.json"
        ws_pad = TOOLKIT_MAP / "bronnen" / "waterschappen.json"
        prov_pad = TOOLKIT_MAP / "bronnen" / "provincies.json"
        try:
            if reg_pad.exists() and slug in json.loads(reg_pad.read_text(encoding="utf-8")):
                orgaan_type = "gr"
            elif ws_pad.exists() and slug in json.loads(ws_pad.read_text(encoding="utf-8")):
                orgaan_type = "waterschap"
            elif prov_pad.exists() and slug in json.loads(prov_pad.read_text(encoding="utf-8")):
                orgaan_type = "provincie"
            else:
                orgaan_type = "gemeente"
        except Exception:
            orgaan_type = "gemeente"

    _scrape_orgaan(slug, orgaan_type, droog=droog)


def _scrape_orgaan(slug: str, orgaan_type: str, droog: bool = False):
    """Roep de juiste scraper aan op basis van het orgaantype."""
    scraper_map = {
        "gemeente": "scraper.py",
        "waterschap": "scraper_waterschap.py",
        "gr": "scraper_gr.py",
        "provincie": "scraper_provincie.py",
    }
    scraper = scraper_map.get(orgaan_type, "scraper.py")
    cmd = [PYTHON, str(TOOLKIT_MAP / scraper), slug]
    if droog:
        cmd.append("--droog")
    print(f"\n  → {slug} ({orgaan_type})")
    subprocess.run(cmd)
    print()


def verkennen(args: list):
    """Toon welke GRs, veiligheidsregio en waterschap horen bij een gemeente — zonder te downloaden."""
    if not args:
        print("\nGebruik: python3 toolkit.py verkennen <gemeente>\n")
        return

    _controleer_brondata()

    gemeente = args[0].lower()
    naam = gemeente.capitalize()

    print()
    print(f"  We gaan de raadsdocumenten van gemeente {naam} downloaden.")
    print(f"  Start hiervoor het volgende commando:")
    print()
    print(f"    python3 scraper.py {gemeente}")
    print()
    print("─" * 50)

    # Verzamel achtergrondinfo — stil, dan pas tonen
    print(f"\n  Vooronderzoek voor {naam}…")

    # Veiligheidsregio
    gevonden_vr = []
    vr_pad = TOOLKIT_MAP / "bronnen" / "veiligheidsregios.json"
    if vr_pad.exists():
        try:
            vr_config = {k: v for k, v in json.loads(vr_pad.read_text(encoding="utf-8")).items()
                         if not k.startswith("_")}
            gevonden_vr = [(slug, info) for slug, info in vr_config.items()
                           if gemeente in info.get("gemeenten", [])]
        except Exception:
            pass

    # GRs
    grs = haal_grs_voor_gemeente(gemeente)

    # Waterschappen — gefilterd op gemeente
    ws_pad = TOOLKIT_MAP / "bronnen" / "waterschappen.json"
    relevante_ws = []
    if ws_pad.exists():
        try:
            for slug, info in json.loads(ws_pad.read_text(encoding="utf-8")).items():
                if slug.startswith("_"):
                    continue
                if gemeente not in info.get("gemeenten", []):
                    continue
                ws_map = OUTPUT_BASIS / "waterschappen" / slug
                al = ws_map.exists() and any(ws_map.rglob("*.pdf"))
                relevante_ws.append((slug, info, al))
        except Exception:
            pass

    # Provincie — gefilterd op gemeente
    prov_pad = TOOLKIT_MAP / "bronnen" / "provincies.json"
    gevonden_prov = []
    if prov_pad.exists():
        try:
            prov_config = {k: v for k, v in json.loads(prov_pad.read_text(encoding="utf-8")).items()
                          if not k.startswith("_")}
            gevonden_prov = [(slug, info) for slug, info in prov_config.items()
                            if gemeente in info.get("gemeenten", [])]
        except Exception:
            pass

    # Tonen
    print()
    print("─" * 50)
    print(f"\n  Uit het vooronderzoek voor {naam}:\n")

    if gevonden_prov:
        for slug, info in gevonden_prov:
            prov_map = OUTPUT_BASIS / "provincies" / slug
            al = prov_map.exists() and any(prov_map.rglob("*.pdf"))
            brontype = info.get("brontype", "")
            if brontype == "geen":
                label = "geen geautomatiseerde bron"
            elif al:
                label = "al gedownload"
            else:
                label = "nog niet gedownload"
            print(f"  Provincie         {info['naam']} ({label})")
    else:
        print(f"  Provincie         niet gevonden in catalogus")

    if gevonden_vr:
        for slug, info in gevonden_vr:
            vr_map = OUTPUT_BASIS / "veiligheidsregios" / slug
            al = vr_map.exists() and any(vr_map.rglob("*.pdf"))
            label = "al gedownload" if al else "nog niet gedownload"
            print(f"  Veiligheidsregio  {info['naam']} ({label})")
    else:
        print(f"  Veiligheidsregio  niet gevonden in catalogus")

    print()

    if grs:
        print(f"  Gemeenschappelijke regelingen ({len(grs)}):")
        for gr in grs:
            gr_map = OUTPUT_BASIS / "regelingen" / gr["slug"]
            al = gr_map.exists() and any(gr_map.rglob("*.pdf"))
            label = " ✓" if al else ""
            print(f"    • {gr['naam']}{label}")
    else:
        print("  Gemeenschappelijke regelingen: geen gevonden")

    if relevante_ws:
        print()
        print(f"  Waterschap{'pen' if len(relevante_ws) > 1 else ''}:")
        for slug, info, al in relevante_ws:
            label = "al gedownload" if al else "nog niet gedownload"
            print(f"    • {info.get('naam', slug)} ({label})")

    # Afsluiting
    print()
    print("─" * 50)
    print()
    print(f"  De raadsdocumenten van {naam} worden sowieso opgehaald.")
    print(f"  Wil je ook stukken van de veiligheidsregio, een van de")
    print(f"  gemeenschappelijke regelingen of een waterschap downloaden?")
    print(f"  Laat het weten.")
    print()
    print(f"  Je hoeft nu geen keuze te maken. Alles wat je hier ziet")
    print(f"  kun je op elk later moment alsnog ophalen, zodra het")
    print(f"  relevant wordt voor je onderzoek.")
    print()


# ── Cron-migratie ─────────────────────────────────────────────────────────────

def fix_cron():
    """Voeg index.py toe aan alle scraper.py-crontabregels die dat nog missen."""
    print()
    print("fix-cron — zoekindex koppelen aan wekelijkse scraper")
    print("─" * 55)

    result = subprocess.run(["crontab", "-l"], capture_output=True, text=True)
    if result.returncode != 0 or not result.stdout.strip():
        print()
        print("  Geen crontab gevonden. Voeg eerst een orgaan toe via nieuw-orgaan.")
        return

    huidige_regels = result.stdout.splitlines(keepends=True)

    te_updaten = []  # lijst van (regelindex, oude_regel, nieuwe_regel)
    for i, regel in enumerate(huidige_regels):
        stripped = regel.rstrip("\n")
        if "scraper.py" in stripped and "index.py" not in stripped and not stripped.startswith("#"):
            # Orgaannaam extraheren: het eerste argument ná scraper.py
            delen = stripped.split()
            try:
                scraper_pos = next(j for j, d in enumerate(delen) if d.endswith("scraper.py"))
                orgaan = delen[scraper_pos + 1]
            except (StopIteration, IndexError):
                orgaan = None

            if orgaan:
                index_toevoeging = f" && {PYTHON} {TOOLKIT_MAP / 'index.py'} {orgaan}"
                # Toevoegen vóór eventuele output-redirectie (>>)
                if ">>" in stripped:
                    redirect_pos = stripped.index(">>")
                    log_deel = stripped[redirect_pos:]
                    basis = stripped[:redirect_pos].rstrip()
                    nieuwe_regel = basis + index_toevoeging + " " + log_deel
                else:
                    nieuwe_regel = stripped + index_toevoeging
                te_updaten.append((i, stripped, nieuwe_regel))

    if not te_updaten:
        print()
        print("  Alle scraper-crontabregels bevatten al een index-stap. Niets te doen.")
        return

    print()
    print(f"  Zoekindex wordt gekoppeld aan {len(te_updaten)} orgaan(en):")
    print()
    for _, oud, _ in te_updaten:
        delen = oud.split()
        scraper_pos = next(j for j, d in enumerate(delen) if d.endswith("scraper.py"))
        print(f"    • {delen[scraper_pos + 1]}")
    print()

    nieuwe_regels = list(huidige_regels)
    for i, _, nieuwe_regel in te_updaten:
        nieuwe_regels[i] = nieuwe_regel + "\n"

    nieuwe_crontab = "".join(nieuwe_regels)
    subprocess.run(["crontab", "-"], input=nieuwe_crontab, text=True, check=True)
    print(f"  ✓ Klaar. Nieuwe documenten worden voortaan automatisch geïndexeerd.")
    print()


# ── Hoofdprogramma ────────────────────────────────────────────────────────────

HELP_ALGEMEEN = """
Lokaalbestuur Toolkit — download en doorzoek vergaderstukken van Nederlandse overheden

Werkwijze voor een nieuwe gemeente:
  1. python3 toolkit.py verkennen <gemeente>   toon provincie, VR, GRs en waterschap
  2. python3 scraper.py <gemeente>             raadsdocumenten downloaden
  3. python3 scraper_provincie.py <slug>       optioneel: provincie
     python3 scraper_vr.py <slug>              optioneel: veiligheidsregio
     python3 scraper_gr.py <slug>              optioneel: gemeenschappelijke regeling
     python3 scraper_waterschap.py <slug>      optioneel: waterschap
  4. python3 toolkit.py onderzoek <gemeente>   zoekindex + Claude-briefing
  5. claude ~/Documents/notulen/<gemeente>     Claude Code openen

Alle commando's:
  python3 toolkit.py                          dashboard (actieve dossiers en alerts)
  python3 toolkit.py verkennen <gemeente>     vooronderzoek vóór het downloaden
  python3 toolkit.py onderzoek <gemeente>     zoekindex bijwerken + Claude-briefing
  python3 toolkit.py scrape <orgaan>          download nieuwe vergaderstukken
  python3 toolkit.py scrape --alles           alle geconfigureerde organen bijwerken
  python3 toolkit.py nieuw-orgaan             gemeente, waterschap of GR toevoegen
  python3 toolkit.py nieuw-dossier            monitoring instellen met trefwoorden
  python3 toolkit.py status                   uitgebreid overzicht dossiers en alerts
  python3 toolkit.py setup                    installatie (afhankelijkheden + configuratie)
  python3 toolkit.py check                    installatiecheck
  python3 toolkit.py fix-cron                 zoekindex koppelen aan bestaande scraper-crontabs

Downloaden met tijdsbegrenzing (scraper.py):
  python3 scraper.py <gemeente> --jaren 1          alleen het afgelopen jaar
  python3 scraper.py <gemeente> --jaren 2          de afgelopen 2 jaar
  python3 scraper.py <gemeente> --vanaf 2024-01-01 vanaf een specifieke datum

Veiligheidsregio's (scraper_vr.py):
  python3 scraper_vr.py --lijst               toon alle 25 veiligheidsregio's
  python3 scraper_vr.py --welke <gemeente>    welke VR hoort bij deze gemeente?
  python3 scraper_vr.py <slug>                download vergaderstukken

Provincies (scraper_provincie.py):
  python3 scraper_provincie.py --lijst         toon alle provincies en hun bron
  python3 scraper_provincie.py --lijst-ori     toon provincies in ORI API
  python3 scraper_provincie.py <slug>          download vergaderstukken

Typ 'python3 toolkit.py <commando> --help' voor meer informatie over een commando.
"""

HELP_PER_COMMANDO = {
    "verkennen": """
verkennen <gemeente>

  Toon welke provincie, veiligheidsregio, gemeenschappelijke regelingen en
  waterschap horen bij een gemeente — zonder iets te downloaden.

  Dit is altijd de eerste stap bij een nieuwe gemeente. Je ziet meteen
  wat er beschikbaar is en kunt daarna zelf beslissen wat je wilt ophalen.
  Alles wat hier verschijnt kun je later alsnog downloaden.

  Voorbeeld:
    python3 toolkit.py verkennen rotterdam
    python3 toolkit.py verkennen groningen
""",
    "onderzoek": """
onderzoek <gemeente>

  Bereid een Claude Code-sessie voor voor een gemeente.
  Vereist dat de scraper al gedraaid heeft voor dit orgaan.

  Stappen:
    1. Zoekindex bijwerken (nieuwe PDF's worden geïndexeerd)
    2. Gemeenschappelijke regelingen detecteren (eerste keer automatisch)
    3. Contextbriefing opslaan als context.md in de documentenmap

  Opties:
    --ververs-regelingen    detecteer GRs opnieuw, ook als regelingen.md al bestaat

  Voorbeelden:
    python3 toolkit.py onderzoek rotterdam
    python3 toolkit.py onderzoek rotterdam --ververs-regelingen
""",
    "scrape": """
scrape <orgaan>
scrape --alles

  Download nieuwe vergaderstukken via de Open Raadsinformatie API.
  Slaat bestanden op in ~/Documents/notulen/<orgaan>/.
  Documenten die al aanwezig zijn worden overgeslagen.

  Gebruik scraper.py direct voor tijdsbegrenzing:
    python3 scraper.py rotterdam --jaren 1
    python3 scraper.py rotterdam --vanaf 2024-01-01

  Voorbeelden:
    python3 toolkit.py scrape rotterdam
    python3 toolkit.py scrape --alles
""",
    "fix-cron": """
fix-cron

  Zoekt alle scraper-crontabregels die nog geen zoekindex-stap bevatten
  en voegt die stap automatisch toe.

  Gebruik dit eenmalig als je de toolkit al had draaien voordat de
  automatische indexering werd toegevoegd.
""",
    "nieuw-orgaan": """
nieuw-orgaan

  Interactieve wizard om een nieuw orgaan toe te voegen aan de toolkit.
  Ondersteunt gemeenten, waterschappen en gemeenschappelijke regelingen.
  Zoekt automatisch het ORI-index op via de API.
""",
    "nieuw-dossier": """
nieuw-dossier

  Interactieve wizard om een monitoringsdossier aan te maken.
  Stel trefwoorden in en kies een frequentie (wekelijks of maandelijks).
  Bij een match verschijnt een macOS-melding en wordt een alertrapport opgeslagen.
""",
    "status": """
status

  Toont een overzicht van alle actieve dossiers:
  trefwoorden, laatste run, aantal documenten, openstaande alerts.
""",
    "setup": """
setup

  Interactieve installatie van de toolkit. Controleert Python-versie,
  installeert pdfplumber als dat ontbreekt, test de API-verbinding
  en stelt de documentenmap in.

  Draaien na het klonen van de repository:
    git clone https://github.com/erwinboogert/lokaalbestuur-toolkit.git
    cd lokaalbestuur-toolkit
    python3 toolkit.py setup
""",
    "check": """
check

  Controleert of de benodigde Python-pakketten aanwezig zijn
  en of de mappen en configuratiebestanden correct staan.
""",
}


def main():
    args = sys.argv[1:]

    if not args:
        dashboard()
        return

    if args[0] in ("--help", "-h", "-?", "?", "help"):
        print(HELP_ALGEMEEN)
        return

    commando = args[0]
    rest = args[1:]

    if "--help" in rest or "-h" in rest:
        if commando in HELP_PER_COMMANDO:
            print(HELP_PER_COMMANDO[commando])
        else:
            print(HELP_ALGEMEEN)
        return

    if commando == "brondata-bijwerken":
        brondata_bijwerken()
    elif commando == "verkennen":
        verkennen(rest)
    elif commando == "nieuw-dossier":
        nieuw_dossier()
    elif commando in ("nieuw-orgaan", "nieuwe-gemeente"):
        nieuwe_gemeente()
    elif commando == "status":
        status()
    elif commando == "check":
        check()
    elif commando == "setup":
        setup()
    elif commando == "nieuw-alert":
        nieuw_alert(rest)
    elif commando == "nieuwe-regeling":
        nieuwe_regeling()
    elif commando == "scrape-regelingen":
        scrape_regelingen()
    elif commando == "nieuw-waterschap":
        nieuw_waterschap()
    elif commando == "scrape-waterschappen":
        scrape_waterschappen()
    elif commando == "nieuwe-provincie":
        nieuwe_provincie()
    elif commando == "scrape-provincies":
        scrape_provincies()
    elif commando == "onderzoek":
        onderzoek(rest)
    elif commando == "scrape":
        scrape(rest)
    elif commando == "ververs-notubiz-catalogus":
        ververs_notubiz_catalogus()
    elif commando == "fix-cron":
        fix_cron()
    else:
        print(f"\nOnbekend commando: '{commando}'")
        print(HELP_ALGEMEEN)
        sys.exit(1)


if __name__ == "__main__":
    main()
