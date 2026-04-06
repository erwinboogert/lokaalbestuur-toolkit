"""Fase 2: Wiki Compiler — bouw en onderhoud de wiki incrementeel."""

import json
import re
from datetime import date, datetime
from pathlib import Path

from wikibrain.llm import ask_claude, ask_claude_json


def load_json(path: Path) -> dict | list:
    if path.exists() and path.stat().st_size > 2:
        with open(path) as f:
            return json.load(f)
    return {} if path.name.endswith("concepts.json") else []


def save_json(path: Path, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def prefilter_score(summary: str, concepts: dict) -> dict[str, float]:
    """Eenvoudige keyword match tussen samenvatting en concept names/aliases."""
    words = set(re.sub(r"[^\w\s]", "", summary.lower()).split())
    scores = {}
    for canonical, meta in concepts.items():
        candidates = [canonical.lower()] + [a.lower() for a in meta.get("aliases", [])]
        matched = sum(1 for c in candidates if c in words or any(w in c for w in words))
        scores[canonical] = min(matched / max(len(candidates), 1), 1.0)
    return scores


def discover_concepts_with_claude(summary: str, concepts: dict, cfg: dict, prompts_dir: Path) -> dict:
    template = (prompts_dir / "compile_discovery.txt").read_text()
    system = (prompts_dir / "system_base.txt").read_text()
    concept_list = "\n".join(f"- {k}" for k in concepts)
    prompt = template.replace("{domain}", cfg["project"]["domain"]) \
                     .replace("{summary}", summary) \
                     .replace("{concepts}", concept_list)

    try:
        return ask_claude_json(prompt, system=system, max_tokens=800)
    except Exception:
        return {"matched_existing": [], "new_concepts": [], "uncertain": [], "reasoning": ""}


def write_article(concept: str, aliases: list, sources: list[tuple[str, str]], cfg: dict, prompts_dir: Path) -> str:
    template = (prompts_dir / "compile_article.txt").read_text()
    system = (prompts_dir / "system_base.txt").read_text()
    sources_text = "\n\n".join(f"=== {path} ===\n{text[:2000]}" for path, text in sources)
    prompt = template.replace("{concept}", concept) \
                     .replace("{aliases}", ", ".join(aliases)) \
                     .replace("{max_words}", str(cfg["compile"]["max_article_length_words"])) \
                     .replace("{sources}", sources_text)

    return ask_claude(prompt, system=system, max_tokens=cfg["llm"]["max_tokens"]["article"])


def write_source_page(source_path: Path, cfg: dict, prompts_dir: Path) -> str:
    template = (prompts_dir / "compile_source.txt").read_text()
    system = (prompts_dir / "system_base.txt").read_text()
    text = source_path.read_text()[:4000]
    prompt = template.replace("{text}", text)

    return ask_claude(prompt, system=system, max_tokens=600)


def update_index_md(wiki_dir: Path, concept: str, blurb: str, source_count: int):
    index_path = wiki_dir / "_meta" / "INDEX.md"
    content = index_path.read_text()
    entry = f"- [[{concept}]] — {blurb}; {source_count} bron(nen)"

    if f"[[{concept}]]" in content:
        # Vervang bestaande regel
        content = re.sub(rf"- \[\[{re.escape(concept)}\]\].*", entry, content)
    else:
        # Voeg toe voor de laatste regel met _Automatisch_
        content = content.replace(
            "_Automatisch bijgehouden door WikiBrain. Niet handmatig bewerken._",
            f"{entry}\n\n---\n\n_Automatisch bijgehouden door WikiBrain. Niet handmatig bewerken._"
        )
        # Verwijder placeholder als die er nog in staat
        content = content.replace(
            "_Nog geen artikelen. Voer `wikibrain ingest` en `wikibrain compile` uit om te beginnen._\n\n",
            ""
        )

    index_path.write_text(content)


def run_compile(cfg: dict, dry_run: bool = False, force_concept: str | None = None, compile_all: bool = False, limit: int | None = None):
    raw_dir = Path(cfg["paths"]["raw"])
    wiki_dir = Path(cfg["paths"]["wiki"])
    prompts_dir = Path(cfg["paths"]["prompts"])
    index_path = cfg["search"]["index_path"]

    queue = load_json(raw_dir / "queue.json")
    concepts = load_json(wiki_dir / "_meta" / "concepts.json")
    raw_index = load_json(raw_dir / "index.json")

    if force_concept:
        print(f"Hercompileer concept: {force_concept}")
        # Markeer bronnen van dit concept als pending
        for item in queue:
            if force_concept in concepts and item["id"] in [
                Path(s).stem for s in concepts[force_concept].get("sources", [])
            ]:
                item["status"] = "pending"

    pending = [item for item in queue if item["status"] == "pending"] if not compile_all else queue
    if limit:
        pending = pending[:limit]

    if not pending:
        print("Geen items in wachtrij. Voer eerst `wikibrain ingest` uit.")
        return

    print(f"Wachtrij: {len(pending)} bronnen te verwerken")

    if dry_run:
        for item in pending[:10]:
            print(f"  {item['id']} — {item.get('path', '')}")
        return

    # Stap 2: aliasconflictencheck
    all_aliases: dict[str, str] = {}
    conflicts = []
    for canonical, meta in concepts.items():
        for alias in meta.get("aliases", []):
            if alias in all_aliases and all_aliases[alias] != canonical:
                conflicts.append((alias, all_aliases[alias], canonical))
            all_aliases[alias] = canonical

    if conflicts:
        print(f"Waarschuwing: {len(conflicts)} aliasconflict(en) gevonden:")
        for alias, c1, c2 in conflicts:
            print(f"  '{alias}' gebruikt door zowel '{c1}' als '{c2}'")

    new_articles = 0
    updated_articles = 0
    concept_sources: dict[str, list[str]] = {k: [] for k in concepts}

    batch_size = cfg["compile"]["batch_size"]
    threshold = cfg["compile"]["discovery"]["llm_threshold"]

    for i in range(0, len(pending), batch_size):
        batch = pending[i:i + batch_size]

        for item in batch:
            source_path = Path(item["path"])
            if not source_path.exists():
                print(f"  Bestand niet gevonden: {source_path}")
                item["status"] = "error"
                continue

            # Haal samenvatting op uit raw index
            summary = ""
            for rel_path, meta in raw_index.items():
                if meta.get("id") == item["id"]:
                    summary = meta.get("summary", "")
                    break

            if not summary:
                summary = source_path.read_text()[:500]

            print(f"Verwerk: {item['id']}")

            # Stap 3: pre-filter
            scores = prefilter_score(summary, concepts)
            matched = [c for c, s in scores.items() if s >= threshold]

            uncertain = [c for c, s in scores.items() if 0 < s < threshold]

            # Claude alleen voor onzekere gevallen en nieuwe concepten
            llm_result = {"matched_existing": [], "new_concepts": [], "uncertain": [], "reasoning": ""}
            if cfg["compile"]["discovery"]["use_prefilter"] is False or uncertain or not matched:
                try:
                    llm_result = discover_concepts_with_claude(summary, concepts, cfg, prompts_dir)
                except Exception as e:
                    print(f"  LLM discovery mislukt: {e}")

            all_matched = list(set(matched + llm_result.get("matched_existing", [])))

            # Koppel bron aan bestaande concepten
            for concept in all_matched:
                if concept in concepts:
                    if item["id"] not in concepts[concept].get("source_ids", []):
                        concepts[concept].setdefault("source_ids", []).append(item["id"])
                        concepts[concept].setdefault("sources", []).append(str(source_path))
                        concepts[concept]["source_count"] = len(concepts[concept]["source_ids"])
                        concepts[concept]["last_updated"] = date.today().isoformat()

            # Nieuwe concepten toevoegen aan registry
            for new_concept in llm_result.get("new_concepts", []):
                if new_concept not in concepts:
                    safe_name = re.sub(r"[^\w\s-]", "", new_concept).strip().replace(" ", "-")
                    concepts[new_concept] = {
                        "canonical": new_concept,
                        "aliases": [],
                        "article_path": f"wiki/concepts/{safe_name}.md",
                        "article_exists": False,
                        "source_count": 1,
                        "source_ids": [item["id"]],
                        "sources": [str(source_path)],
                        "last_updated": date.today().isoformat(),
                    }
                    print(f"  Nieuw concept: {new_concept}")

            item["status"] = "compiled"

        # Stap 4: schrijf/update artikelen
        for concept, meta in concepts.items():
            source_ids = meta.get("source_ids", [])
            if len(source_ids) < cfg["compile"]["min_sources_for_article"] and not meta.get("article_exists"):
                continue

            article_path = wiki_dir / "concepts" / (re.sub(r"[^\w\s-]", "", concept).strip().replace(" ", "-") + ".md")
            is_new = not article_path.exists()

            # Laad bronnen
            source_texts = []
            for s_path in meta.get("sources", [])[:5]:  # max 5 bronnen per artikel
                p = Path(s_path)
                if p.exists():
                    source_texts.append((s_path, p.read_text()))

            if not source_texts:
                continue

            try:
                article_md = write_article(concept, meta.get("aliases", []), source_texts, cfg, prompts_dir)
                article_path.write_text(article_md, encoding="utf-8")
                meta["article_exists"] = True
                meta["article_path"] = str(article_path)

                # Zoekindex bijwerken
                try:
                    from wikibrain.search import get_db, index_article
                    db = get_db(index_path)
                    index_article(db, concept, concept, article_md, str(article_path), "concept")
                except Exception as e:
                    print(f"  Zoekindex bijwerken mislukt: {e}")

                # INDEX.md bijwerken
                blurb = article_md.split("\n")[0].replace("# ", "")[:60]
                update_index_md(wiki_dir, concept, blurb, meta["source_count"])

                if is_new:
                    new_articles += 1
                    print(f"  Artikel aangemaakt: {concept}")
                else:
                    updated_articles += 1
                    print(f"  Artikel bijgewerkt: {concept}")

            except Exception as e:
                print(f"  Artikel schrijven mislukt voor '{concept}': {e}")

        # Stap 5: source pages
        for item in batch:
            if item["status"] != "compiled":
                continue
            source_path = Path(item["path"])
            source_page_path = wiki_dir / "sources" / (item["id"] + ".md")
            if not source_page_path.exists():
                try:
                    page = write_source_page(source_path, cfg, prompts_dir)
                    source_page_path.write_text(page, encoding="utf-8")
                except Exception as e:
                    print(f"  Bronpagina mislukt voor {item['id']}: {e}")

        # Opslaan
        save_json(wiki_dir / "_meta" / "concepts.json", concepts)
        save_json(raw_dir / "queue.json", queue)

    print(f"\nKlaar. {new_articles} nieuwe artikelen, {updated_articles} bijgewerkt.")

    # Git commit als ingeschakeld
    if cfg.get("git", {}).get("auto_commit") and "compile" in cfg["git"].get("commit_after", []):
        import subprocess
        msg = f"WikiBrain compile: {len(pending)} bronnen verwerkt, {new_articles} nieuwe artikelen, {updated_articles} bijgewerkt"
        subprocess.run(["git", "add", str(wiki_dir), str(raw_dir / "queue.json"), str(wiki_dir / "_meta" / "concepts.json")])
        subprocess.run(["git", "commit", "-m", msg])
