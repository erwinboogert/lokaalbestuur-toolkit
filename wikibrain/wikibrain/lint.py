"""Fase 5: Lint & Health Checks — kwaliteitsbewaking van de wiki."""

import json
import re
from datetime import date, datetime
from pathlib import Path

from wikibrain.llm import ask_claude_json


def run_lint(cfg: dict, fix: bool = False, report: bool = False, check: str | None = None):
    wiki_dir = Path(cfg["paths"]["wiki"])
    prompts_dir = Path(cfg["paths"]["prompts"])

    concepts_path = wiki_dir / "_meta" / "concepts.json"
    if not concepts_path.exists():
        print("Geen concepts.json gevonden. Voer eerst `wikibrain compile` uit.")
        return

    with open(concepts_path) as f:
        concepts = json.load(f)

    articles = list((wiki_dir / "concepts").glob("*.md"))
    sources = list((wiki_dir / "sources").glob("*.md"))

    findings = {
        "contradictions": [],
        "duplicate_suspects": [],
        "orphan_articles": [],
        "missing_metadata": [],
        "article_candidates": [],
        "outdated_articles": [],
        "orphaned_sources": [],
        "alias_conflicts": [],
        "summary": "",
    }

    if not check or check == "metadata":
        _check_metadata(articles, findings)

    if not check or check == "orphans":
        _check_orphans(concepts, articles, wiki_dir, findings)

    if not check or check == "aliases":
        _check_alias_conflicts(concepts, findings)

    if not check or check == "outdated":
        _check_outdated(concepts, findings)

    if not check or check == "duplicates":
        _check_duplicates_with_claude(articles[:20], cfg, prompts_dir, findings)

    # Samenvatting
    total_issues = sum(len(v) for v in findings.values() if isinstance(v, list))
    findings["summary"] = f"{total_issues} bevindingen op {date.today().isoformat()}."

    # Output
    _print_findings(findings)

    if report:
        report_path = wiki_dir / "_meta" / "health_report.md"
        _write_report(report_path, findings)
        print(f"\nRapport opgeslagen: {report_path}")

    if fix:
        print("\nFix-modus: vraag Claude om oplossingen... (nog niet geïmplementeerd)")


def _check_metadata(articles: list[Path], findings: dict):
    required_fields = {"title", "tags"}
    for path in articles:
        content = path.read_text()
        fm_match = re.search(r"^---\n(.*?)\n---", content, re.DOTALL)
        if not fm_match:
            findings["missing_metadata"].append({"file": str(path), "issue": "geen frontmatter"})
            continue
        fm = fm_match.group(1)
        for field in required_fields:
            if field not in fm:
                findings["missing_metadata"].append({"file": str(path), "issue": f"ontbreekt: {field}"})


def _check_orphans(concepts: dict, articles: list[Path], wiki_dir: Path, findings: dict):
    for concept, meta in concepts.items():
        if meta.get("source_count", 0) == 0:
            findings["orphan_articles"].append(concept)

    all_article_names = {p.stem for p in articles}
    raw_source_names = {p.stem for p in (wiki_dir.parent / "raw" / "sources").glob("*.md")} if (wiki_dir.parent / "raw" / "sources").exists() else set()

    for name in raw_source_names:
        if name not in all_article_names and not any(name in str(m.get("source_ids", [])) for m in concepts.values()):
            findings["orphaned_sources"].append(name)


def _check_alias_conflicts(concepts: dict, findings: dict):
    seen: dict[str, str] = {}
    for canonical, meta in concepts.items():
        for alias in meta.get("aliases", []):
            key = alias.lower()
            if key in seen:
                findings["alias_conflicts"].append({
                    "alias": alias,
                    "concept_1": seen[key],
                    "concept_2": canonical,
                })
            else:
                seen[key] = canonical


def _check_outdated(concepts: dict, findings: dict):
    today = date.today()
    for concept, meta in concepts.items():
        last_updated = meta.get("last_updated")
        if last_updated:
            delta = (today - date.fromisoformat(last_updated)).days
            if delta > 90 and meta.get("source_count", 0) > 0:
                findings["outdated_articles"].append({
                    "concept": concept,
                    "last_updated": last_updated,
                    "days_ago": delta,
                })


def _check_duplicates_with_claude(articles: list[Path], cfg: dict, prompts_dir: Path, findings: dict):
    if not articles:
        return
    template = (prompts_dir / "lint.txt").read_text()
    system = (prompts_dir / "system_base.txt").read_text()
    articles_text = "\n\n".join(
        f"=== {p.name} ===\n{p.read_text()[:800]}" for p in articles
    )
    prompt = template.replace("{articles}", articles_text)

    try:
        result = ask_claude_json(prompt, system=system, max_tokens=1000)
        findings["duplicate_suspects"].extend(result.get("duplicate_suspects", []))
        findings["article_candidates"].extend(result.get("article_candidates", []))
    except Exception as e:
        print(f"  Claude lint mislukt: {e}")


def _print_findings(findings: dict):
    print("\n=== WikiBrain Health Report ===\n")
    labels = {
        "missing_metadata": "Ontbrekende metadata",
        "orphan_articles": "Wees-artikelen",
        "alias_conflicts": "Aliasconflicten",
        "outdated_articles": "Verouderde artikelen (>90 dagen)",
        "duplicate_suspects": "Mogelijke duplicaten",
        "article_candidates": "Nieuwe artikel-kandidaten",
        "orphaned_sources": "Verweesd bronmateriaal",
        "contradictions": "Tegenstrijdige feiten",
    }
    for key, label in labels.items():
        items = findings.get(key, [])
        if items:
            print(f"[{len(items)}] {label}:")
            for item in items[:5]:
                print(f"  - {item}")
            if len(items) > 5:
                print(f"  ... en {len(items) - 5} meer")
        else:
            print(f"[0] {label}: OK")
    print(f"\n{findings['summary']}")


def _write_report(path: Path, findings: dict):
    lines = [f"# WikiBrain Health Report — {date.today().isoformat()}\n"]
    for key, items in findings.items():
        if key == "summary" or not isinstance(items, list):
            continue
        lines.append(f"\n## {key}\n")
        if items:
            for item in items:
                lines.append(f"- {item}")
        else:
            lines.append("_Geen bevindingen._")
    lines.append(f"\n---\n_{findings['summary']}_")
    path.write_text("\n".join(lines), encoding="utf-8")
