"""Fase 3: Q&A — stel vragen aan de wiki."""

import json
import re
from datetime import date
from pathlib import Path

from wikibrain.llm import ask_claude


def run_query(cfg: dict, question: str, output_format: str = "markdown"):
    wiki_dir = Path(cfg["paths"]["wiki"])
    prompts_dir = Path(cfg["paths"]["prompts"])
    output_dir = Path(cfg["query"]["output_dir"])
    index_path = cfg["search"]["index_path"]
    max_articles = cfg["query"]["max_context_articles"]

    output_dir.mkdir(parents=True, exist_ok=True)

    # Stap 1: zoek in index
    from wikibrain.search import get_db, search as fts_search
    from pathlib import Path as P

    if not P(index_path).exists():
        print("Zoekindex niet gevonden. Voer `wikibrain compile` uit.")
        return

    db = get_db(index_path)
    search_term = " ".join(question.split()[:8])  # Eerste 8 woorden als zoekterm
    results = fts_search(db, search_term, top_k=cfg["search"]["top_k"])

    if not results:
        print("Geen relevante artikelen gevonden in de wiki.")
        return

    print(f"Gevonden: {len(results)} relevante artikelen")

    # Stap 2: leesplan — neem top N artikelen
    articles_to_read = results[:max_articles]

    # Stap 3: laad volledige artikelen
    article_texts = []
    for r in articles_to_read:
        path = Path(r["path"])
        if path.exists():
            article_texts.append(f"=== {r['title']} ===\n{path.read_text()}")
            print(f"  Lees: {r['title']}")

    if not article_texts:
        print("Kon geen artikelen laden.")
        return

    # Stap 4 & 5: Claude formuleert antwoord
    template = (prompts_dir / "query.txt").read_text()
    system = (prompts_dir / "system_base.txt").read_text()
    prompt = template.replace("{question}", question) \
                     .replace("{output_format}", output_format) \
                     .replace("{articles}", "\n\n".join(article_texts))

    answer = ask_claude(prompt, system=system, max_tokens=cfg["llm"]["max_tokens"]["query"])

    # Opslaan
    today = date.today().isoformat()
    safe_q = re.sub(r"[^\w\s-]", "", question[:40]).strip().replace(" ", "-").lower()
    ext = ".marp.md" if output_format == "slides" else ".md"
    output_file = output_dir / f"{today}-{safe_q}{ext}"

    if output_format == "image":
        # Voer matplotlib code uit in sandbox
        _execute_matplotlib(answer, output_dir, today, safe_q, cfg)
    else:
        output_file.write_text(answer, encoding="utf-8")
        print(f"\nOutput opgeslagen: {output_file}")
        print("\n" + "=" * 60)
        print(answer[:1000])
        if len(answer) > 1000:
            print(f"\n... (zie {output_file} voor volledig antwoord)")


def _execute_matplotlib(code: str, output_dir: Path, today: str, safe_q: str, cfg: dict):
    """Voer matplotlib code uit in een beperkte sandbox."""
    import subprocess
    import tempfile

    png_path = output_dir / f"{today}-{safe_q}.png"

    # Extraheer Python code uit markdown code block
    match = re.search(r"```python\n(.*?)```", code, re.DOTALL)
    if not match:
        print("Geen Python code gevonden in antwoord.")
        return

    py_code = match.group(1)
    py_code += f"\nplt.savefig('{png_path}', dpi=150, bbox_inches='tight')\n"

    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as tmp:
        tmp.write(py_code)
        tmp_path = tmp.name

    result = subprocess.run(
        ["python3", tmp_path],
        timeout=30,
        capture_output=True,
        text=True,
    )

    if result.returncode == 0:
        print(f"Afbeelding opgeslagen: {png_path}")
    else:
        print(f"Matplotlib uitvoering mislukt:\n{result.stderr}")
