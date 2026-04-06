"""Fase 1: Ingest & Parse — verwerk bronbestanden naar markdown."""

import hashlib
import json
import logging
import shutil
from datetime import datetime
from pathlib import Path

from wikibrain.llm import ask_claude_json

logger = logging.getLogger(__name__)

SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".xlsx", ".pptx", ".html", ".md", ".png", ".jpg", ".jpeg"}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return f"sha256:{h.hexdigest()}"


def load_index(raw_dir: Path) -> dict:
    index_path = raw_dir / "index.json"
    if index_path.exists() and index_path.stat().st_size > 2:
        with open(index_path) as f:
            return json.load(f)
    return {}


def save_index(raw_dir: Path, index: dict):
    with open(raw_dir / "index.json", "w") as f:
        json.dump(index, f, indent=2, ensure_ascii=False)


def load_queue(raw_dir: Path) -> list:
    queue_path = raw_dir / "queue.json"
    if queue_path.exists() and queue_path.stat().st_size > 2:
        with open(queue_path) as f:
            return json.load(f)
    return []


def save_queue(raw_dir: Path, queue: list):
    with open(raw_dir / "queue.json", "w") as f:
        json.dump(queue, f, indent=2, ensure_ascii=False)


def log_error(raw_dir: Path, file_id: str, reason: str):
    with open(raw_dir / "errors.log", "a") as f:
        timestamp = datetime.now().isoformat()
        f.write(f"{timestamp} | {file_id} | {reason}\n")


def convert_file(path: Path, cfg: dict, raw_dir: Path) -> str | None:
    """Probeer bestand te converteren naar markdown. Geeft markdown-tekst terug of None."""
    converters = cfg["ingest"]["converters"]

    # Primaire converter: MarkItDown
    try:
        from markitdown import MarkItDown
        md = MarkItDown()
        result = md.convert(str(path))
        if result and result.text_content and result.text_content.strip():
            return result.text_content
    except Exception as e:
        logger.warning(f"MarkItDown mislukt voor {path.name}: {e}")

    # Fallback: PyMuPDF4LLM (alleen voor PDF)
    if path.suffix.lower() == ".pdf":
        try:
            import pymupdf4llm
            text = pymupdf4llm.to_markdown(str(path))
            if text and text.strip():
                return text
        except Exception as e:
            logger.warning(f"PyMuPDF4LLM mislukt voor {path.name}: {e}")

    # Fallback 2: Marker (alleen als ingeschakeld)
    if converters.get("use_marker", False):
        try:
            from marker.convert import convert_single_pdf
            from marker.models import load_all_models
            models = load_all_models()
            full_text, _, _ = convert_single_pdf(str(path), models)
            if full_text and full_text.strip():
                return full_text
        except Exception as e:
            logger.warning(f"Marker mislukt voor {path.name}: {e}")

    return None


def summarize_with_claude(text: str, cfg: dict, prompts_dir: Path) -> dict:
    """Laat Claude een samenvatting + tags schrijven."""
    prompt_path = prompts_dir / "ingest_summary.txt"
    template = prompt_path.read_text()
    max_sentences = cfg["ingest"]["summary_max_sentences"]

    # Beperk tekst tot eerste ~3000 woorden voor samenvatting
    truncated = " ".join(text.split()[:3000])
    prompt = template.replace("{text}", truncated).replace("{max_sentences}", str(max_sentences))
    system = (prompts_dir / "system_base.txt").read_text()

    try:
        return ask_claude_json(prompt, system=system, max_tokens=cfg["llm"]["max_tokens"]["summary"])
    except Exception:
        return {"summary": text[:200], "tags": []}


def run_ingest(cfg: dict, force: bool = False, dry_run: bool = False):
    sources_dir = Path(cfg["paths"]["sources"])
    raw_dir = Path(cfg["paths"]["raw"])
    prompts_dir = Path(cfg["paths"]["prompts"])
    batch_size = cfg["ingest"]["batch_size"]
    supported = set(cfg["ingest"]["supported_extensions"])

    if not sources_dir.exists():
        print(f"Bronmap niet gevonden: {sources_dir}")
        print("Pas 'paths.sources' aan in config.yaml.")
        return

    index = load_index(raw_dir)
    queue = load_queue(raw_dir)
    queued_ids = {item["id"] for item in queue}

    # Scan bronmap
    all_files = [p for p in sources_dir.rglob("*") if p.is_file() and p.suffix.lower() in supported]
    print(f"Gevonden: {len(all_files)} bronbestanden")

    to_process = []
    for path in all_files:
        file_id = path.stem + "-" + sha256(path)[7:15]
        current_hash = sha256(path)
        existing = index.get(str(path.relative_to(sources_dir)))

        if not force and existing and existing.get("hash") == current_hash:
            continue  # ongewijzigd

        to_process.append((path, file_id, current_hash))

    print(f"Te verwerken: {len(to_process)} bestanden ({'alle' if force else 'nieuw/gewijzigd'})")

    if dry_run:
        for path, file_id, _ in to_process[:20]:
            print(f"  {path.name}")
        if len(to_process) > 20:
            print(f"  ... en {len(to_process) - 20} meer")
        return

    processed = 0
    for i in range(0, len(to_process), batch_size):
        batch = to_process[i:i + batch_size]
        for path, file_id, current_hash in batch:
            print(f"Verwerk: {path.name}")

            # Converteer
            text = convert_file(path, cfg, raw_dir)
            if not text:
                log_error(raw_dir, file_id, f"Alle converters mislukt voor {path.name}")
                print(f"  FOUT: conversie mislukt, zie errors.log")
                continue

            # Normaliseer en sla op
            out_path = raw_dir / "sources" / f"{file_id}.md"
            out_path.write_text(text, encoding="utf-8")

            # Samenvatting via Claude
            try:
                meta = summarize_with_claude(text, cfg, prompts_dir)
            except Exception as e:
                logger.warning(f"Samenvatting mislukt: {e}")
                meta = {"summary": "", "tags": []}

            # Update index
            rel_path = str(path.relative_to(sources_dir))
            index[rel_path] = {
                "id": file_id,
                "original_path": str(path),
                "converted_path": str(out_path),
                "hash": current_hash,
                "converter_used": "unknown",
                "file_type": path.suffix.lower().lstrip("."),
                "size_bytes": path.stat().st_size,
                "last_modified": datetime.fromtimestamp(path.stat().st_mtime).date().isoformat(),
                "processed_at": datetime.now().isoformat(),
                "summary": meta.get("summary", ""),
                "tags": meta.get("tags", []),
                "status": "queued",
                "compile_status": "pending",
                "error": None,
            }

            # Voeg toe aan wachtrij
            if file_id not in queued_ids:
                queue.append({"id": file_id, "path": str(out_path), "status": "pending"})
                queued_ids.add(file_id)

            processed += 1
            print(f"  OK: {meta.get('summary', '')[:80]}")

        # Tussentijds opslaan na elke batch
        save_index(raw_dir, index)
        save_queue(raw_dir, queue)

    print(f"\nKlaar. {processed} bestanden verwerkt, {len(queue)} in wachtrij.")
