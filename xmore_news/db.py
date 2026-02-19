"""
db.py — Xmore News Ingestion Layer
SQLite persistence for the RSS / Google News / PDF / page-monitor ingestion layer.

Tables managed here are ADDITIVE to the existing news_articles table in storage.py.
Uses the same DB_PATH so everything lives in one database file.
"""

import json
import logging
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from config import DB_PATH, MAX_RETRIES
from models import Article, IngestionAttempt, SourceHealth

logger = logging.getLogger(__name__)

# Health thresholds (independent of config to avoid import cycles)
_DEGRADED_THRESHOLD = 3
_OFFLINE_HOURS = 24

_SCHEMA = """
-- Articles ingested by the new layer (RSS, GNews, PDF, page-monitor)
CREATE TABLE IF NOT EXISTS xmore_articles (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    title            TEXT    NOT NULL,
    content          TEXT    NOT NULL,
    published_at     TEXT,
    source           TEXT    NOT NULL,
    ingestion_method TEXT    NOT NULL,
    language         TEXT    DEFAULT 'en',
    processed_flag   INTEGER DEFAULT 0,
    url              TEXT,
    content_hash     TEXT    UNIQUE NOT NULL,
    created_at       TEXT    DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_xa_source   ON xmore_articles(source);
CREATE INDEX IF NOT EXISTS idx_xa_pub      ON xmore_articles(published_at DESC);
CREATE INDEX IF NOT EXISTS idx_xa_method   ON xmore_articles(ingestion_method);
CREATE INDEX IF NOT EXISTS idx_xa_lang     ON xmore_articles(language);

-- Per-attempt structured ingestion log
CREATE TABLE IF NOT EXISTS xmore_ingestion_logs (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    source         TEXT    NOT NULL,
    method         TEXT    NOT NULL,
    success        INTEGER NOT NULL,
    articles_count INTEGER DEFAULT 0,
    error_message  TEXT,
    duration_ms    INTEGER DEFAULT 0,
    timestamp      TEXT    DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_xl_source ON xmore_ingestion_logs(source);
CREATE INDEX IF NOT EXISTS idx_xl_ts     ON xmore_ingestion_logs(timestamp DESC);

-- Aggregated health per source key
CREATE TABLE IF NOT EXISTS xmore_source_health (
    source_name          TEXT UNIQUE NOT NULL,
    success_count        INTEGER DEFAULT 0,
    failure_count        INTEGER DEFAULT 0,
    consecutive_failures INTEGER DEFAULT 0,
    last_success         TEXT,
    status               TEXT    DEFAULT 'active',
    success_rate         REAL    DEFAULT 0.0,
    updated_at           TEXT    DEFAULT (datetime('now'))
);

-- SHA-256 hash of monitored page HTML (for change detection)
CREATE TABLE IF NOT EXISTS xmore_page_hashes (
    source_name  TEXT PRIMARY KEY,
    url          TEXT NOT NULL,
    last_hash    TEXT NOT NULL,
    last_checked TEXT DEFAULT (datetime('now'))
);

-- Known PDF URLs per page source (to identify new ones)
CREATE TABLE IF NOT EXISTS xmore_known_pdf_urls (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    source_name TEXT NOT NULL,
    url         TEXT NOT NULL,
    discovered  TEXT DEFAULT (datetime('now')),
    UNIQUE(source_name, url)
);
"""


# ---------------------------------------------------------------------------
# Connection
# ---------------------------------------------------------------------------

def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH), detect_types=sqlite3.PARSE_DECLTYPES)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    return conn


def init_db() -> None:
    """Create all tables if they don't exist. Safe to call repeatedly."""
    with _connect() as conn:
        conn.executescript(_SCHEMA)
    logger.info("xmore_news DB ready: %s", DB_PATH)


# ---------------------------------------------------------------------------
# Articles
# ---------------------------------------------------------------------------

def save_article(article: Article) -> bool:
    """
    Persist an Article. Returns True if new, False if duplicate.
    Dedup is based on content_hash (SHA-256 of source|title|content[:500]).
    """
    h = article.content_hash()
    try:
        with _connect() as conn:
            conn.execute(
                """
                INSERT INTO xmore_articles
                    (title, content, published_at, source, ingestion_method,
                     language, processed_flag, url, content_hash)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    article.title.strip(),
                    article.content,
                    article.published_at,
                    article.source,
                    article.ingestion_method,
                    article.language,
                    article.processed_flag,
                    article.url,
                    h,
                ),
            )
        logger.debug("Saved [%s][%s]: %s", article.source, article.ingestion_method, article.title[:60])
        return True
    except sqlite3.IntegrityError:
        logger.debug("Duplicate skipped: %s", article.title[:60])
        return False


def get_articles(
    source: Optional[str] = None,
    method: Optional[str] = None,
    language: Optional[str] = None,
    limit: int = 50,
) -> List[Article]:
    conditions: List[str] = []
    params: List[Any] = []
    if source:
        conditions.append("source = ?")
        params.append(source)
    if method:
        conditions.append("ingestion_method = ?")
        params.append(method)
    if language:
        conditions.append("language = ?")
        params.append(language)
    where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    params.append(limit)
    with _connect() as conn:
        rows = conn.execute(
            f"SELECT * FROM xmore_articles {where} ORDER BY published_at DESC LIMIT ?",
            params,
        ).fetchall()
    return [Article.from_row(dict(r)) for r in rows]


# ---------------------------------------------------------------------------
# Ingestion logs
# ---------------------------------------------------------------------------

def record_ingestion(attempt: IngestionAttempt) -> None:
    with _connect() as conn:
        conn.execute(
            """
            INSERT INTO xmore_ingestion_logs
                (source, method, success, articles_count, error_message, duration_ms)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                attempt.source,
                attempt.method,
                1 if attempt.success else 0,
                attempt.articles_count,
                attempt.error,
                attempt.duration_ms,
            ),
        )


# ---------------------------------------------------------------------------
# Source health
# ---------------------------------------------------------------------------

def _compute_status(consecutive: int, last_success: Optional[str]) -> str:
    now = datetime.now(tz=timezone.utc)
    if consecutive >= _DEGRADED_THRESHOLD:
        return "degraded"
    if last_success:
        try:
            last = datetime.fromisoformat(last_success)
            if last.tzinfo is None:
                last = last.replace(tzinfo=timezone.utc)
            if (now - last).total_seconds() / 3600 >= _OFFLINE_HOURS:
                return "offline"
        except ValueError:
            pass
    elif consecutive > 0:
        return "degraded"
    return "active"


def update_health(source_name: str, success: bool) -> None:
    now = datetime.now(tz=timezone.utc).isoformat()
    with _connect() as conn:
        row = conn.execute(
            "SELECT * FROM xmore_source_health WHERE source_name = ?", (source_name,)
        ).fetchone()

        if row is None:
            sc = 1 if success else 0
            fc = 0 if success else 1
            consec = 0 if success else 1
            ls = now if success else None
            total = sc + fc
            rate = sc / total
            status = _compute_status(consec, ls)
            conn.execute(
                """
                INSERT INTO xmore_source_health
                    (source_name, success_count, failure_count, consecutive_failures,
                     last_success, status, success_rate, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (source_name, sc, fc, consec, ls, status, rate, now),
            )
        else:
            sc = row["success_count"] + (1 if success else 0)
            fc = row["failure_count"] + (0 if success else 1)
            consec = 0 if success else row["consecutive_failures"] + 1
            ls = now if success else row["last_success"]
            total = sc + fc
            rate = sc / total if total > 0 else 0.0
            status = _compute_status(consec, ls)
            conn.execute(
                """
                UPDATE xmore_source_health
                SET success_count = ?, failure_count = ?, consecutive_failures = ?,
                    last_success = ?, status = ?, success_rate = ?, updated_at = ?
                WHERE source_name = ?
                """,
                (sc, fc, consec, ls, status, rate, now, source_name),
            )


def get_all_health() -> List[SourceHealth]:
    with _connect() as conn:
        rows = conn.execute(
            "SELECT * FROM xmore_source_health ORDER BY source_name"
        ).fetchall()
    return [
        SourceHealth(
            source_name=r["source_name"],
            success_count=r["success_count"],
            failure_count=r["failure_count"],
            consecutive_failures=r["consecutive_failures"],
            last_success=r["last_success"],
            status=r["status"],
            success_rate=r["success_rate"],
            updated_at=r["updated_at"],
        )
        for r in rows
    ]


# ---------------------------------------------------------------------------
# Page hashes (page-monitor change detection)
# ---------------------------------------------------------------------------

def get_page_hash(source_name: str) -> Optional[str]:
    with _connect() as conn:
        row = conn.execute(
            "SELECT last_hash FROM xmore_page_hashes WHERE source_name = ?",
            (source_name,),
        ).fetchone()
    return row["last_hash"] if row else None


def set_page_hash(source_name: str, url: str, page_hash: str) -> None:
    with _connect() as conn:
        conn.execute(
            """
            INSERT INTO xmore_page_hashes (source_name, url, last_hash, last_checked)
            VALUES (?, ?, ?, datetime('now'))
            ON CONFLICT(source_name) DO UPDATE
            SET url = excluded.url,
                last_hash = excluded.last_hash,
                last_checked = excluded.last_checked
            """,
            (source_name, url, page_hash),
        )


# ---------------------------------------------------------------------------
# Known PDF URLs
# ---------------------------------------------------------------------------

def get_known_pdf_urls(source_name: str) -> List[str]:
    with _connect() as conn:
        rows = conn.execute(
            "SELECT url FROM xmore_known_pdf_urls WHERE source_name = ?",
            (source_name,),
        ).fetchall()
    return [r["url"] for r in rows]


def add_known_pdf_url(source_name: str, url: str) -> None:
    try:
        with _connect() as conn:
            conn.execute(
                "INSERT OR IGNORE INTO xmore_known_pdf_urls (source_name, url) VALUES (?, ?)",
                (source_name, url),
            )
    except Exception as exc:
        logger.warning("Could not store known PDF URL: %s", exc)


# ---------------------------------------------------------------------------
# Convenience aliases & reporting helpers
# ---------------------------------------------------------------------------

def init() -> None:
    """Alias for init_db() — ensures all tables exist."""
    init_db()


def get_recent_articles(limit: int = 20) -> List[Article]:
    """Return the most recently ingested articles."""
    with _connect() as conn:
        rows = conn.execute(
            "SELECT * FROM xmore_articles ORDER BY created_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
    articles = []
    for r in rows:
        row_dict = dict(r)
        art = Article.from_row(row_dict)
        # Expose created_at as ingested_at for display purposes
        art.__dict__["ingested_at"] = row_dict.get("created_at", "")
        articles.append(art)
    return articles


def get_stats() -> Dict[str, Any]:
    """Return aggregate statistics about the xmore_news database."""
    with _connect() as conn:
        total = conn.execute("SELECT COUNT(*) FROM xmore_articles").fetchone()[0]
        by_method = conn.execute(
            "SELECT ingestion_method, COUNT(*) cnt FROM xmore_articles GROUP BY ingestion_method"
        ).fetchall()
        by_source = conn.execute(
            "SELECT source, COUNT(*) cnt FROM xmore_articles GROUP BY source "
            "ORDER BY cnt DESC LIMIT 10"
        ).fetchall()
        by_lang = conn.execute(
            "SELECT language, COUNT(*) cnt FROM xmore_articles GROUP BY language ORDER BY cnt DESC"
        ).fetchall()
        health_counts = conn.execute(
            "SELECT status, COUNT(*) cnt FROM xmore_source_health GROUP BY status"
        ).fetchall()
        known_pdfs = conn.execute("SELECT COUNT(*) FROM xmore_known_pdf_urls").fetchone()[0]
        logs_total = conn.execute("SELECT COUNT(*) FROM xmore_ingestion_logs").fetchone()[0]

    stats: Dict[str, Any] = {"total_articles": total}
    for r in by_method:
        stats[f"method_{r[0]}"] = r[1]
    for r in by_lang:
        stats[f"lang_{r[0]}"] = r[1]
    stats["known_pdf_urls"] = known_pdfs
    stats["ingestion_log_entries"] = logs_total
    for r in health_counts:
        stats[f"health_{r[0]}"] = r[1]
    stats["top_sources"] = {r[0]: r[1] for r in by_source}
    return stats
