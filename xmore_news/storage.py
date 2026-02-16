"""Storage layer for normalized news articles."""

from __future__ import annotations

import json
import logging
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

from xmore_news import config

logger = logging.getLogger(__name__)


class SQLiteNewsStorage:
    """SQLite-backed store for ingested articles."""

    def __init__(self, db_path: str | Path | None = None) -> None:
        self.db_path = Path(db_path or config.DB_PATH)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize_schema()

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def _initialize_schema(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS news_articles (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    content TEXT,
                    published_at TEXT NOT NULL,
                    source TEXT NOT NULL,
                    url TEXT NOT NULL UNIQUE,
                    url_hash TEXT NOT NULL UNIQUE,
                    mentioned_symbols TEXT NOT NULL DEFAULT '[]',
                    sentiment_score REAL NULL,
                    processed_flag INTEGER NOT NULL DEFAULT 0,
                    region TEXT NOT NULL DEFAULT 'global',
                    language TEXT NULL,
                    sector_keywords TEXT NOT NULL DEFAULT '[]',
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_news_articles_published_at ON news_articles(published_at DESC)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_news_articles_source ON news_articles(source)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_news_articles_processed ON news_articles(processed_flag)")

    def save_articles_to_db(self, articles: list[dict[str, Any]]) -> dict[str, int]:
        """Insert articles; duplicate URLs/hashes are ignored."""
        inserted = 0
        duplicates = 0
        with self._connect() as conn:
            for article in articles:
                try:
                    conn.execute(
                        """
                        INSERT INTO news_articles (
                            title, content, published_at, source, url, url_hash,
                            mentioned_symbols, sentiment_score, processed_flag, region,
                            language, sector_keywords
                        )
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            str(article.get("title", "")),
                            str(article.get("content", "")),
                            str(article.get("published_at", datetime.now(timezone.utc).isoformat())),
                            str(article.get("source", "")),
                            str(article.get("url", "")),
                            str(article.get("url_hash", "")),
                            json.dumps(article.get("mentioned_symbols", []), ensure_ascii=False),
                            article.get("sentiment_score"),
                            int(article.get("processed_flag", 0)),
                            str(article.get("region", "global")),
                            str(article.get("language", "")) or None,
                            json.dumps(article.get("sector_keywords", []), ensure_ascii=False),
                        ),
                    )
                    inserted += 1
                except sqlite3.IntegrityError:
                    duplicates += 1
                except Exception as exc:
                    logger.error("Failed inserting article URL=%s: %s", article.get("url"), exc)
        return {"inserted": inserted, "duplicates": duplicates}

    def has_url_hash(self, url_hash: str) -> bool:
        with self._connect() as conn:
            row = conn.execute("SELECT 1 FROM news_articles WHERE url_hash = ? LIMIT 1", (url_hash,)).fetchone()
            return row is not None


_DEFAULT_STORAGE: SQLiteNewsStorage | None = None


def get_default_storage(db_path: str | Path | None = None) -> SQLiteNewsStorage:
    global _DEFAULT_STORAGE
    if _DEFAULT_STORAGE is None or (db_path and Path(db_path) != _DEFAULT_STORAGE.db_path):
        _DEFAULT_STORAGE = SQLiteNewsStorage(db_path=db_path)
    return _DEFAULT_STORAGE


def save_articles_to_db(articles: list[dict[str, Any]], db_path: str | Path | None = None) -> dict[str, int]:
    """
    Functional API required by specification.
    """
    return get_default_storage(db_path=db_path).save_articles_to_db(articles)

