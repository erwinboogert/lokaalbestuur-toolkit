"""
Lokaalbestuur Toolkit — dashboard en interface

Gebruik:
    python3 toolkit.py                      toon dashboard (overzicht van actieve dossiers)
    python3 toolkit.py nieuw-dossier        stel een nieuw dossier in
    python3 toolkit.py nieuw-orgaan         voeg een orgaan toe (gemeente, waterschap of GR)
    python3 toolkit.py status               uitgebreid statusoverzicht
    python3 toolkit.py check                controleer installatie
    python3 toolkit.py wikibrain-ingest     verwerk nieuwe raadsstukken naar kennisbank
    python3 toolkit.py wikibrain-compile    update WikiBrain-artikelen
    python3 toolkit.py wikibrain-query      stel een vraag aan de kennisbank
    python3 toolkit.py financien <gemeente> haal iv3-financiëndata op uit CBS
    python3 toolkit.py nieuwe-regeling      voeg een GR toe aan de catalogus
    python3 toolkit.py scrape-regelingen    download stukken voor alle GRs
"""

import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

TOOLKIT_MAP = Path(__file__).parent
WIKIBRAIN_MAP = TOOLKIT_MAP / "wikibrain"
PYTHON = "/opt/homebrew/bin/python3"


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


def voeg_crontabregel_toe(commentaar: str, regel: str):
    """Voeg een regel toe aan de crontab na bevestiging."""
    print()
    print("  Voeg dit toe aan je crontab voor automatische wekelijkse uitvoering:")
    print()
    print(f"    # {commentaar}")
    print(f"    {regel}")
    print()
    keuze = input("  Automatisch toevoegen aan crontab? (j/n): ").strip().lower()
    if keuze == "j":
        result = subprocess.run(["crontab", "-l"], capture_output=True, text=True)
        bestaand = result.stdout if result.returncode == 0 else ""
        if regel in bestaand:
            print("  (regel stond al in crontab, niets gewijzigd)")
            return
        nieuw = bestaand.rstrip() + f"\n\n# {commentaar}\n{regel}\n"
        subprocess.run(["crontab", "-"], input=nieuw, text=True, check=True)
        print("  ✓ Crontabregel toegevoegd.")


# ── Commando's ────────────────────────────────────────────────────────────────

def wikibrain_status() -> dict:
    """Lees WikiBrain-statistieken uit wiki/_meta."""
    meta = WIKIBRAIN_MAP / "wiki" / "_meta"
    n_artikelen = len(list((meta / "..").glob("concepts/*.md"))) if (meta / "..").exists() else 0
    index_pad = meta / "INDEX.md"
    laatste_compile = "nog niet gedraaid"
    if index_pad.exists():
        ts = index_pad.stat().st_mtime
        laatste_compile = datetime.fromtimestamp(ts).strftime("%d %b %Y, %H:%M")
    queue_pad = WIKIBRAIN_MAP / "raw" / "queue.json"
    n_wachtrij = 0
    if queue_pad.exists():
        try:
            wachtrij = json.loads(queue_pad.read_text(encoding="utf-8"))
            if isinstance(wachtrij, list):
                n_wachtrij = sum(1 for item in wachtrij if item.get("status") != "compiled")
        except Exception:
            pass
    return {"artikelen": n_artikelen, "laatste_compile": laatste_compile, "wachtrij": n_wachtrij}


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

    # WikiBrain-status
    wb = wikibrain_status()
    print()
    print("WikiBrain kennisbank:")
    print(f"  artikelen: {wb['artikelen']}   wachtrij: {wb['wachtrij']}   laatste compile: {wb['laatste_compile']}")

    print()
    print("─" * 50)
    print()
    print("  python3 toolkit.py nieuw-dossier    → nieuw dossier aanmaken")
    print("  python3 toolkit.py nieuw-orgaan     → nieuw orgaan toevoegen")
    print("  python3 toolkit.py status           → uitgebreid overzicht")
    print("  python3 toolkit.py wikibrain-ingest → verwerk nieuwe raadsstukken")
    print("  python3 toolkit.py wikibrain-compile → update kennisbank")
    print("  python3 toolkit.py wikibrain-query  → stel een vraag aan de kennisbank")
    print()


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
    keuze_type = input("  Keuze [1]: ").strip() or "1"
    type_map = {"1": "gemeente", "2": "waterschap", "3": "gr"}
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

    print()
    keuze_droog = input("  Eerst droog uitvoeren (wat zou er gedownload worden)? (j/n): ").strip().lower()
    if keuze_droog == "j":
        subprocess.run([PYTHON, str(TOOLKIT_MAP / "scraper.py"), orgaan, "--droog"])
        print()
        keuze_dl = input("  Nu echt downloaden? (j/n): ").strip().lower()
        if keuze_dl != "j":
            print("  Gestopt na droog uitvoeren.")
            print(f"  Downloaden later: python3 scraper.py {orgaan}")
            print()
            return

    subprocess.run([PYTHON, str(TOOLKIT_MAP / "scraper.py"), orgaan])

    log_pad = OUTPUT_BASIS / orgaan / "logs" / "scraper.log"
    cron_scraper = f"0 9 * * 3 {PYTHON} {TOOLKIT_MAP / 'scraper.py'} {orgaan} >> {log_pad} 2>&1"
    voeg_crontabregel_toe(f"Scraper — {orgaan}", cron_scraper)

    log_pad_wb = OUTPUT_BASIS / orgaan / "logs" / "wikibrain.log"
    cron_wb_ingest = f"15 9 * * 3 cd {WIKIBRAIN_MAP} && {PYTHON} -m wikibrain.cli ingest >> {log_pad_wb} 2>&1"
    cron_wb_compile = f"45 9 * * 3 cd {WIKIBRAIN_MAP} && {PYTHON} -m wikibrain.cli compile >> {log_pad_wb} 2>&1"
    voeg_crontabregel_toe(f"WikiBrain ingest — {orgaan}", cron_wb_ingest)
    voeg_crontabregel_toe(f"WikiBrain compile — {orgaan}", cron_wb_compile)

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
    print(f"  Direct downloaden:")
    print(f"  python3 scraper_gr.py {slug}")
    print(f"  python3 scraper_gr.py {slug} --droog")
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


def financien(args: list):
    """Haal iv3-financiëndata op uit CBS voor een gemeente."""
    if not args:
        print("\nGebruik: python3 toolkit.py financien <gemeente> [jaar] [--droog]")
        print("Voorbeeld: python3 toolkit.py financien rotterdam")
        print("           python3 toolkit.py financien rotterdam 2022\n")
        return
    subprocess.run([PYTHON, str(TOOLKIT_MAP / "scraper_cbs.py")] + args)


def wikibrain_ingest():
    """Verwerk nieuwe en gewijzigde raadsstukken naar WikiBrain."""
    subprocess.run([PYTHON, "-m", "wikibrain.cli", "ingest"], cwd=WIKIBRAIN_MAP)


def wikibrain_compile():
    """Update de kennisbank op basis van verwerkte bronnen."""
    subprocess.run([PYTHON, "-m", "wikibrain.cli", "compile"], cwd=WIKIBRAIN_MAP)


def wikibrain_query(args: list):
    """Stel een vraag aan de kennisbank."""
    if not args:
        print("\nGebruik: python3 toolkit.py wikibrain-query \"jouw vraag\"\n")
        return
    vraag_tekst = " ".join(args)
    subprocess.run([PYTHON, "-m", "wikibrain.cli", "query", vraag_tekst], cwd=WIKIBRAIN_MAP)


def check():
    """Controleer of de toolkit correct is geïnstalleerd en klaar voor gebruik."""
    import urllib.request

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

    # WikiBrain
    wb_config = WIKIBRAIN_MAP / "config.yaml"
    if wb_config.exists():
        print("  ✓ WikiBrain aanwezig en geconfigureerd")
    else:
        print("  ✗ WikiBrain config.yaml niet gevonden — check wikibrain/ map")
        fouten += 1

    try:
        import importlib.util
        spec = importlib.util.find_spec("markitdown")
        if spec:
            print("  ✓ markitdown geïnstalleerd")
        else:
            print("  ! markitdown niet gevonden — installeer met: pip install markitdown[all]")
    except Exception:
        pass

    # Crontab
    result = subprocess.run(["crontab", "-l"], capture_output=True, text=True)
    crontab = result.stdout
    if "scraper.py" in crontab:
        print("  ✓ Crontab scraper aanwezig")
    else:
        print("  ! Geen scraper-crontab — gebruik: python3 toolkit.py nieuw-orgaan")
    if "wikibrain" in crontab:
        print("  ✓ Crontab WikiBrain aanwezig")
    else:
        print("  ! Geen WikiBrain-crontab — voeg toe via: python3 toolkit.py nieuw-orgaan")
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


# ── Hoofdprogramma ────────────────────────────────────────────────────────────

def main():
    args = sys.argv[1:]

    if not args:
        dashboard()
    elif args[0] == "nieuw-dossier":
        nieuw_dossier()
    elif args[0] in ("nieuw-orgaan", "nieuwe-gemeente"):
        nieuwe_gemeente()
    elif args[0] == "status":
        status()
    elif args[0] == "check":
        check()
    elif args[0] == "nieuw-alert":
        nieuw_alert(args[1:])
    elif args[0] == "nieuwe-regeling":
        nieuwe_regeling()
    elif args[0] == "scrape-regelingen":
        scrape_regelingen()
    elif args[0] == "financien":
        financien(args[1:])
    elif args[0] == "wikibrain-ingest":
        wikibrain_ingest()
    elif args[0] == "wikibrain-compile":
        wikibrain_compile()
    elif args[0] == "wikibrain-query":
        wikibrain_query(args[1:])
    else:
        print(f"\nOnbekend commando: '{args[0]}'")
        print("Gebruik: python3 toolkit.py [nieuw-dossier | nieuw-orgaan | status | check |")
        print("                             wikibrain-ingest | wikibrain-compile | wikibrain-query |")
        print("                             financien <gemeente> | nieuwe-regeling | scrape-regelingen]\n")
        sys.exit(1)


if __name__ == "__main__":
    main()
