"""
Bronnenboek — lokale webserver

Gebruik:
    python3 server.py

Opent op http://localhost:5000

Vereisten:
    pip install flask
"""

import json
import queue
import re
import sqlite3
import subprocess
import sys
import threading
import time
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from flask import Flask, Response, jsonify, request, send_from_directory

# ── Configuratie ──────────────────────────────────────────────────────────────

TOOLKIT_MAP = Path(__file__).parent
PYTHON = sys.executable
WEB_MAP = TOOLKIT_MAP / "web"

_config_pad = TOOLKIT_MAP / "config.local.json"
_data_map: Optional[Path] = None
if _config_pad.exists():
    try:
        _cfg = json.loads(_config_pad.read_text(encoding="utf-8"))
        if "data_map" in _cfg:
            _data_map = Path(_cfg["data_map"]).expanduser()
    except Exception:
        pass

OUTPUT_BASIS    = _data_map if _data_map else (Path.home() / "Documents" / "notulen")
DOSSIERS_MAP    = (_data_map / "dossiers") if _data_map else (TOOLKIT_MAP / "dossiers")
ORGANEN_MAP     = (_data_map / "organen")  if _data_map else (TOOLKIT_MAP / "organen")
BRONNEN_MAP     = TOOLKIT_MAP / "bronnen"

# ── Flask ─────────────────────────────────────────────────────────────────────

app = Flask(__name__, static_folder=str(WEB_MAP), static_url_path="")
app.config["SEND_FILE_MAX_AGE_DEFAULT"] = 0


# ── Job-beheer voor scraper-streams ──────────────────────────────────────────

_jobs       = {}   # type: dict[str, queue.Queue]
_job_status = {}   # type: dict[str, dict]


def _run_job(job_id: str, cmd: list[str]):
    """Draai een subprocess en stream de uitvoer naar de job-queue."""
    q = _jobs[job_id]
    _job_status[job_id] = {"status": "running", "gestart": datetime.now().isoformat()}
    try:
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )
        for line in proc.stdout:
            q.put({"type": "log", "text": line.rstrip()})
        proc.wait()
        _job_status[job_id]["status"] = "done" if proc.returncode == 0 else "error"
        _job_status[job_id]["returncode"] = proc.returncode
    except Exception as e:
        q.put({"type": "error", "text": str(e)})
        _job_status[job_id]["status"] = "error"
    finally:
        q.put(None)  # sentinel: stream beëindigd


def _start_job(cmd: list[str]) -> str:
    """Start een job in een achtergrondthread en geef het job-id terug."""
    job_id = str(uuid.uuid4())[:8]
    _jobs[job_id] = queue.Queue()
    threading.Thread(target=_run_job, args=(job_id, cmd), daemon=True).start()
    return job_id


# ── Hulpfuncties ──────────────────────────────────────────────────────────────

def tel_pdfs(pad: Path) -> int:
    if not pad.exists():
        return 0
    return sum(1 for _ in pad.rglob("*.pdf"))


def lees_dossiers() -> list[dict]:
    if not DOSSIERS_MAP.exists():
        return []
    dossiers = []
    for pad in sorted(DOSSIERS_MAP.glob("*.json")):
        try:
            d = json.loads(pad.read_text(encoding="utf-8"))
            d["_naam"] = pad.stem
            dossiers.append(d)
        except Exception:
            pass
    return dossiers


def lees_organen() -> list[dict]:
    if not ORGANEN_MAP.exists():
        return []
    organen = []
    for pad in sorted(ORGANEN_MAP.glob("*.json")):
        try:
            o = json.loads(pad.read_text(encoding="utf-8"))
            o["_slug"] = pad.stem
            organen.append(o)
        except Exception:
            pass
    return organen


def laatste_run_ts(orgaan: str, dossier_naam: str) -> Optional[str]:
    voor_dossier = OUTPUT_BASIS / orgaan / "logs" / f"analyse-staat-{dossier_naam}.json"
    algemeen     = OUTPUT_BASIS / orgaan / "logs" / "analyse-staat.json"
    pad = voor_dossier if voor_dossier.exists() else (algemeen if algemeen.exists() else None)
    if not pad:
        return None
    try:
        return json.loads(pad.read_text(encoding="utf-8")).get("laatste_run")
    except Exception:
        return None


def format_relatief(ts: Optional[str]) -> str:
    if not ts:
        return "nooit"
    try:
        dt = datetime.fromisoformat(ts)
        minuten = int((datetime.now() - dt).total_seconds() / 60)
        if minuten < 2:   return "zojuist"
        if minuten < 60:  return f"{minuten} min geleden"
        uren = minuten // 60
        if uren < 24:     return f"{uren} uur geleden"
        dagen = uren // 24
        return f"{dagen} {'dag' if dagen == 1 else 'dagen'} geleden"
    except Exception:
        return ts[:16]


def dossier_status(orgaan: str, naam: str) -> str:
    if not laatste_run_ts(orgaan, naam):
        return "wacht"
    log = OUTPUT_BASIS / orgaan / "logs" / f"analyse-{naam}.log"
    if log.exists() and ("FOUT" in log.read_text(encoding="utf-8")[-3000:]):
        return "fout"
    return "actief"


def _datum_display(dt: datetime) -> str:
    maanden = ["jan","feb","mrt","apr","mei","jun","jul","aug","sep","okt","nov","dec"]
    delta = (datetime.now().date() - dt.date()).days
    if delta == 0:
        uur = dt.strftime("%H:%M") if dt.hour else "—"
        return f"vandaag, {uur}"
    if delta == 1:
        return "gisteren"
    return f"{dt.day} {maanden[dt.month - 1]}"


def lees_alerts() -> list[dict]:
    alerts = []
    basissen = [OUTPUT_BASIS] + [
        OUTPUT_BASIS / s
        for s in ("regelingen", "waterschappen", "veiligheidsregios", "provincies")
    ]
    for basis in basissen:
        if not basis.exists():
            continue
        for alerts_map in basis.rglob("alerts"):
            if not alerts_map.is_dir():
                continue
            orgaan = alerts_map.parent.name
            for pad in sorted(alerts_map.glob("alert-*.md"), reverse=True):
                try:
                    tekst = pad.read_text(encoding="utf-8")
                    dossier, docs = "", 0
                    for regel in tekst.splitlines()[:8]:
                        if "**Dossier:**" in regel:
                            dossier = regel.split("**Dossier:**", 1)[1].strip()
                        m = re.search(r"(\d+) document", regel)
                        if m:
                            docs = int(m.group(1))
                    m_d = re.search(r"alert-(\d{4}-\d{2}-\d{2})", pad.name)
                    datum_str = m_d.group(1) if m_d else pad.stem
                    try:
                        dt = datetime.strptime(datum_str, "%Y-%m-%d")
                        nieuw = (datetime.now() - dt) < timedelta(hours=48)
                        display = _datum_display(dt)
                    except ValueError:
                        nieuw, display = False, datum_str
                    alerts.append({
                        "id":      pad.stem,
                        "pad":     str(pad),
                        "dossier": dossier or pad.stem,
                        "orgaan":  orgaan,
                        "datum":   datum_str,
                        "datum_display": display,
                        "docs":    docs,
                        "nieuw":   nieuw,
                    })
                except Exception:
                    pass
    return sorted(alerts, key=lambda a: a["datum"], reverse=True)


# ── Gemeenten-cache (ORI) ─────────────────────────────────────────────────────

_gem_cache: list[str] = []
_gem_cache_ts: float  = 0.0


def haal_gemeenten_ori() -> list[str]:
    global _gem_cache, _gem_cache_ts
    if _gem_cache and (time.time() - _gem_cache_ts) < 86400:
        return _gem_cache
    try:
        import urllib.request
        req = urllib.request.Request(
            "https://api.openraadsinformatie.nl/v1/elastic/_cat/indices?h=index&format=json",
            headers={"Accept": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=10) as r:
            indices = json.loads(r.read())
        gemeenten = sorted(set(
            i["index"].replace("ori_", "").rsplit("_", 2)[0].replace("_", "-")
            for i in indices if i["index"].startswith("ori_")
        ))
        _gem_cache, _gem_cache_ts = gemeenten, time.time()
        return gemeenten
    except Exception:
        return _gem_cache


# ── Routes ────────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return send_from_directory(str(WEB_MAP), "index.html")


@app.route("/api/status")
def api_status():
    dossiers_raw = lees_dossiers()
    alerts       = lees_alerts()[:30]
    organen      = lees_organen()

    dossiers = [
        {
            "naam":        d["_naam"],
            "label":       d.get("label", d["_naam"]),
            "orgaan":      d.get("orgaan") or d.get("gemeente", ""),
            "trefwoorden": d.get("trefwoorden", [])[:3],
            "laatste_run": format_relatief(laatste_run_ts(
                d.get("orgaan") or d.get("gemeente", ""), d["_naam"]
            )),
            "status": dossier_status(
                d.get("orgaan") or d.get("gemeente", ""), d["_naam"]
            ),
        }
        for d in dossiers_raw
    ]

    # ── Gemeenten-detail ─────────────────────────────────────────────────────
    gem_organen = []
    for o in organen:
        if o.get("type", "gemeente") == "gemeente":
            slug = o["_slug"]
            docs = tel_pdfs(OUTPUT_BASIS / slug)
            gem_organen.append({"naam": o.get("naam", slug), "slug": slug, "docs": docs})
    gem_organen.sort(key=lambda x: x["docs"], reverse=True)
    gem_docs = sum(o["docs"] for o in gem_organen)

    # ── Overige bronnen-detail ────────────────────────────────────────────────
    def _bronnen_detail(pad: Path, submap: str) -> dict:
        """Geef geconfigureerd-telling, totaal docs en per-orgaan detail."""
        try:
            cfg = {k: v for k, v in json.loads(pad.read_text(encoding="utf-8")).items()
                   if not k.startswith("_")}
        except Exception:
            return {"geconfigureerd": 0, "docs": 0, "organen": []}
        org_lijst = []
        for slug, info in cfg.items():
            naam = info.get("naam", slug) if isinstance(info, dict) else slug
            org_docs = tel_pdfs(OUTPUT_BASIS / submap / slug)
            org_lijst.append({"naam": naam, "slug": slug, "docs": org_docs})
        org_lijst.sort(key=lambda x: x["docs"], reverse=True)
        return {
            "geconfigureerd": len(org_lijst),
            "docs":    sum(o["docs"] for o in org_lijst),
            "organen": org_lijst,
        }

    gr_detail   = _bronnen_detail(BRONNEN_MAP / "regelingen.json",      "regelingen")
    ws_detail   = _bronnen_detail(BRONNEN_MAP / "waterschappen.json",    "waterschappen")
    vr_detail   = _bronnen_detail(BRONNEN_MAP / "veiligheidsregios.json","veiligheidsregios")
    prov_detail = _bronnen_detail(BRONNEN_MAP / "provincies.json",       "provincies")

    totaal = (gem_docs + gr_detail["docs"] + ws_detail["docs"]
              + vr_detail["docs"] + prov_detail["docs"])

    return jsonify({
        "alerts":     alerts,
        "dossiers":   dossiers,
        "output_pad": str(OUTPUT_BASIS),
        "bronnen": {
            "gemeenten": {
                "geconfigureerd": len(gem_organen),
                "docs":    gem_docs,
                "organen": gem_organen,
            },
            "grs":               gr_detail,
            "waterschappen":     ws_detail,
            "veiligheidsregios": vr_detail,
            "provincies":        prov_detail,
        },
        "stats": {
            "totaal_docs":      totaal,
            "actieve_dossiers": len(dossiers),
            "nieuw_alerts":     sum(1 for a in alerts if a["nieuw"]),
        },
    })


@app.route("/api/organen")
def api_organen():
    return jsonify(lees_organen())


@app.route("/api/gemeenten")
def api_gemeenten():
    # Start ophalen op de achtergrond als de cache leeg is
    if not _gem_cache:
        threading.Thread(target=haal_gemeenten_ori, daemon=True).start()
        # Geef geconfigureerde gemeenten terug als snelle fallback
        organen = lees_organen()
        return jsonify([o["_slug"] for o in organen if o.get("type", "gemeente") == "gemeente"])
    return jsonify(haal_gemeenten_ori())


@app.route("/api/scrapen/start", methods=["POST"])
def api_scrapen_start():
    data      = request.json or {}
    org_type  = data.get("type", "gemeente")
    orgaan    = data.get("orgaan", "").lower().strip()
    periode   = int(data.get("periode", 24))   # in maanden
    simuleer  = bool(data.get("simuleer", False))

    if not orgaan:
        return jsonify({"fout": "Geen orgaan opgegeven"}), 400

    scrapers = {
        "gemeente":         TOOLKIT_MAP / "scraper.py",
        "gr":               TOOLKIT_MAP / "scraper_gr.py",
        "waterschap":       TOOLKIT_MAP / "scraper_waterschap.py",
        "veiligheidsregio": TOOLKIT_MAP / "scraper_vr.py",
        "provincie":        TOOLKIT_MAP / "scraper_provincie.py",
    }
    scraper = scrapers.get(org_type)
    if not scraper:
        return jsonify({"fout": f"Onbekend type: {org_type}"}), 400

    jaren = max(1, (periode + 11) // 12)
    cmd   = [PYTHON, str(scraper), orgaan, "--jaren", str(jaren)]
    if simuleer:
        cmd.append("--droog")

    return jsonify({"job_id": _start_job(cmd), "orgaan": orgaan})


@app.route("/api/scrapen/stream/<job_id>")
def api_scrapen_stream(job_id: str):
    if job_id not in _jobs:
        return jsonify({"fout": "Job niet gevonden"}), 404

    def generate():
        q = _jobs[job_id]
        while True:
            try:
                item = q.get(timeout=25)
            except queue.Empty:
                yield ": keepalive\n\n"
                continue
            if item is None:
                status = _job_status.get(job_id, {})
                yield f"data: {json.dumps({'type': 'done', 'status': status})}\n\n"
                break
            yield f"data: {json.dumps(item)}\n\n"

    return Response(
        generate(),
        mimetype="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.route("/api/index/bijwerken", methods=["POST"])
def api_index_bijwerken():
    data   = request.json or {}
    orgaan = data.get("orgaan", "").lower().strip()
    if not orgaan:
        return jsonify({"fout": "Geen orgaan opgegeven"}), 400
    cmd = [PYTHON, str(TOOLKIT_MAP / "index.py"), orgaan]
    return jsonify({"job_id": _start_job(cmd)})


@app.route("/api/zoeken")
def api_zoeken():
    orgaan = request.args.get("orgaan", "").lower().strip()
    query  = request.args.get("q", "").strip()

    if not orgaan or not query:
        return jsonify({"hits": [], "totaal": 0, "fout": None})

    # Zoek de juiste docs-map
    docs_map = OUTPUT_BASIS / orgaan
    if not docs_map.exists():
        for sub in ("regelingen", "waterschappen", "veiligheidsregios", "provincies"):
            k = OUTPUT_BASIS / sub / orgaan
            if k.exists():
                docs_map = k
                break
        else:
            return jsonify({"hits": [], "totaal": 0,
                            "fout": f"Orgaan '{orgaan}' niet gevonden"})

    db_pad = docs_map / "index.db"
    if not db_pad.exists():
        return jsonify({"hits": [], "totaal": 0,
                        "fout": "Geen zoekindex — klik eerst op 'Doorzoekbaar maken'"})

    t0 = time.time()
    try:
        con  = sqlite3.connect(str(db_pad))
        rows = con.execute(
            """SELECT pad, datum, vergadertype, bestandsnaam,
                      snippet(tekst_fts, 4, '**', '**', '…', 40)
               FROM tekst_fts WHERE tekst MATCH ?
               ORDER BY rank LIMIT 200""",
            (query,)
        ).fetchall()
        con.close()
    except sqlite3.OperationalError as e:
        return jsonify({"hits": [], "totaal": 0, "fout": str(e)})

    hits = [
        {"pad": r[0], "datum": r[1], "vergadertype": r[2],
         "bestandsnaam": r[3], "snippet": r[4]}
        for r in rows
    ]
    return jsonify({
        "hits":   hits,
        "totaal": len(hits),
        "tijd":   round(time.time() - t0, 3),
        "fout":   None,
    })


@app.route("/api/alerts")
def api_alerts():
    return jsonify(lees_alerts())


@app.route("/api/alerts/<alert_id>")
def api_alert_detail(alert_id: str):
    basissen = [OUTPUT_BASIS] + [
        OUTPUT_BASIS / s
        for s in ("regelingen", "waterschappen", "veiligheidsregios", "provincies")
    ]
    for basis in basissen:
        for pad in basis.rglob(f"{alert_id}.md"):
            try:
                return jsonify({"id": alert_id, "inhoud": pad.read_text(encoding="utf-8"),
                                "pad": str(pad)})
            except Exception as e:
                return jsonify({"fout": str(e)}), 500
    return jsonify({"fout": "Alert niet gevonden"}), 404


@app.route("/api/analyse/draaien", methods=["POST"])
def api_analyse_draaien():
    data    = request.json or {}
    dossier = data.get("dossier", "").strip()
    if not dossier:
        return jsonify({"fout": "Geen dossier opgegeven"}), 400
    cmd = [PYTHON, str(TOOLKIT_MAP / "analyse.py"), "--dossier", dossier]
    return jsonify({"job_id": _start_job(cmd)})


@app.route("/api/verkennen")
def api_verkennen():
    gemeente = request.args.get("gemeente", "").lower().strip()
    if not gemeente:
        return jsonify({"fout": "Geen gemeente opgegeven"}), 400

    # Veiligheidsregio
    veiligheidsregio = None
    vr_pad = BRONNEN_MAP / "veiligheidsregios.json"
    if vr_pad.exists():
        try:
            vr_cfg = {k: v for k, v in json.loads(vr_pad.read_text(encoding="utf-8")).items()
                      if not k.startswith("_")}
            for slug, info in vr_cfg.items():
                if gemeente in info.get("gemeenten", []):
                    veiligheidsregio = info.get("naam", slug)
                    break
        except Exception:
            pass

    # Provincie
    provincie = None
    prov_pad = BRONNEN_MAP / "provincies.json"
    if prov_pad.exists():
        try:
            prov_cfg = {k: v for k, v in json.loads(prov_pad.read_text(encoding="utf-8")).items()
                        if not k.startswith("_")}
            for slug, info in prov_cfg.items():
                if gemeente in info.get("gemeenten", []):
                    provincie = info.get("naam", slug)
                    break
        except Exception:
            pass

    # Waterschappen
    waterschappen = []
    ws_pad = BRONNEN_MAP / "waterschappen.json"
    if ws_pad.exists():
        try:
            for slug, info in json.loads(ws_pad.read_text(encoding="utf-8")).items():
                if slug.startswith("_"):
                    continue
                if gemeente in info.get("gemeenten", []):
                    waterschappen.append(info.get("naam", slug))
        except Exception:
            pass

    # Gemeenschappelijke regelingen
    regelingen_lijst = []
    reg_pad = BRONNEN_MAP / "regelingen.json"
    if reg_pad.exists():
        try:
            for slug, info in json.loads(reg_pad.read_text(encoding="utf-8")).items():
                if slug.startswith("_"):
                    continue
                if isinstance(info, dict) and gemeente in info.get("gemeenten", []):
                    regelingen_lijst.append(info.get("naam", slug))
        except Exception:
            pass

    if not provincie and not veiligheidsregio and not waterschappen and not regelingen_lijst:
        return jsonify({"fout": f"Gemeente '{gemeente}' niet gevonden in catalogus"}), 404

    return jsonify({
        "gemeente":        gemeente,
        "provincie":       provincie,
        "veiligheidsregio": veiligheidsregio,
        "waterschappen":   waterschappen,
        "regelingen":      regelingen_lijst,
    })


@app.route("/api/document/open", methods=["POST"])
def api_document_open():
    data = request.json or {}
    pad  = data.get("pad", "").strip()
    if not pad or not Path(pad).exists():
        return jsonify({"fout": "Bestand niet gevonden"}), 404
    subprocess.Popen(["open", pad])
    return jsonify({"ok": True})


@app.route("/api/instellingen", methods=["GET"])
def api_instellingen_get():
    config = {}
    if _config_pad.exists():
        try:
            config = json.loads(_config_pad.read_text(encoding="utf-8"))
        except Exception:
            pass
    return jsonify({"output_pad": str(OUTPUT_BASIS), "config": config})


@app.route("/api/instellingen", methods=["POST"])
def api_instellingen_post():
    data = request.json or {}
    nieuw_pad_str = data.get("output_pad", "").strip()
    if not nieuw_pad_str:
        return jsonify({"fout": "Geen pad opgegeven"}), 400
    try:
        nieuw_pad = Path(nieuw_pad_str).expanduser().resolve()
    except Exception as e:
        return jsonify({"fout": str(e)}), 400

    # Lees bestaande config en update
    config = {}
    if _config_pad.exists():
        try:
            config = json.loads(_config_pad.read_text(encoding="utf-8"))
        except Exception:
            pass
    config["data_map"] = str(nieuw_pad)
    try:
        _config_pad.write_text(
            json.dumps(config, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
    except Exception as e:
        return jsonify({"fout": f"Kan config niet schrijven: {e}"}), 500

    return jsonify({"ok": True, "nieuw_pad": str(nieuw_pad), "herstart": True})


# ── Start ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    # Alvast gemeenten ophalen op de achtergrond
    threading.Thread(target=haal_gemeenten_ori, daemon=True).start()

    print()
    print("  Bronnenboek")
    print("  ───────────────────────────────────")
    print(f"  Documenten : {OUTPUT_BASIS}")
    print(f"  Dossiers   : {DOSSIERS_MAP}")
    print()
    print("  → http://localhost:5000")
    print()
    print("  Ctrl+C om te stoppen.")
    print()
    app.run(debug=False, port=5000, threaded=True)
