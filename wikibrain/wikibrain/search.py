"""Fase 4: Zoekindex — SQLite full-text search."""

import sqlite3
from pathlib import Path


def get_db(index_path: str) -> sqlite3.Connection:
    db = sqlite3.connect(index_path)
    db.execute("""
        CREATE VIRTUAL TABLE IF NOT EXISTS articles USING fts5(
            id,
            title,
            content,
            path,
            article_type,
            tokenize='unicode61'
        )
    """)
    db.commit()
    return db


def index_article(db: sqlite3.Connection, article_id: str, title: str, content: str, path: str, article_type: str = "concept"):
    """Voeg een artikel toe aan de index of update het."""
    db.execute("DELETE FROM articles WHERE id = ?", (article_id,))
    db.execute(
        "INSERT INTO articles (id, title, content, path, article_type) VALUES (?, ?, ?, ?, ?)",
        (article_id, title, content, path, article_type)
    )
    db.commit()


def search(db: sqlite3.Connection, term: str, top_k: int = 10, article_type: str | None = None) -> list[dict]:
    """Zoek artikelen op relevantie."""
    if article_type:
        rows = db.execute(
            "SELECT id, title, path, article_type, snippet(articles, 2, '...', '...', '...', 20) "
            "FROM articles WHERE articles MATCH ? AND article_type = ? "
            "ORDER BY rank LIMIT ?",
            (term, article_type, top_k)
        ).fetchall()
    else:
        rows = db.execute(
            "SELECT id, title, path, article_type, snippet(articles, 2, '...', '...', '...', 20) "
            "FROM articles WHERE articles MATCH ? "
            "ORDER BY rank LIMIT ?",
            (term, top_k)
        ).fetchall()

    return [
        {"id": r[0], "title": r[1], "path": r[2], "type": r[3], "snippet": r[4]}
        for r in rows
    ]


def run_search(cfg: dict, term: str, top_k: int = 10, search_in: str | None = None, result_type: str | None = None):
    index_path = cfg["search"]["index_path"]
    if not Path(index_path).exists():
        print("Zoekindex nog niet aangemaakt. Voer eerst `wikibrain compile` uit.")
        return

    db = get_db(index_path)
    results = search(db, term, top_k=top_k, article_type=result_type)

    if not results:
        print(f"Geen resultaten voor '{term}'.")
        return

    print(f"{len(results)} resultaten voor '{term}':\n")
    for i, r in enumerate(results, 1):
        print(f"{i}. {r['path']}  [{r['type']}]")
        print(f"   \"{r['snippet']}\"")
        print()
