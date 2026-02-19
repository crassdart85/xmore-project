"""
storage.py — Xmore Reliable News Acquisition Layer
SQLite persistence layer for articles, ingestion logs, and source health.
Uses WAL mode for concurrent read safety. All writes are transactional.
"""

import hashlib
import json
import logging
import sqlite3
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from config import DB_PATH, HEALTH_DEGRADED_THRESHOLD, HEALTH_OFFLINE_HOURS

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Connection factory
# ---------------------------------------------------------------------------

def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH), detect_types=sqlite3.PARSE_DECLTYPES)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute("PRAGMA synchronous=NORMAL")
    return conn


# ---------------------------------------------------------------------------
# Schema bootstrap
# ---------------------------------------------------------------------------

_SCHEMA = """
CREATE TABLE IF NOT EXISTS articles (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    title            TEXT    NOT NULL,
    content          TEXT    NOT NULL,
    published_at     TEXT,
    source           TEXT    NOT NULL,
    ingestion_method TEXT    NOT NULL,
    detected_symbols TEXT    DEFAULT '[]',
    language         TEXT    DEFAULT 'en',
    processed_flag   INTEGER DEFAULT 0,
    content_hash     TEXT    UNIQUE NOT NULL,
    url              TEXT,
    created_at       TEXT    DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_articles_source      ON articles(source);
CREATE INDEX IF NOT EXISTS idx_articles_published   ON articles(published_at DESC);
CREATE INDEX IF NOT EXISTS idx_articles_processed   ON articles(processed_flag);
CREATE INDEX IF NOT EXISTS idx_articles_language    ON articles(language);

-- -------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS ingestion_logs (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    source           TEXT NOT NULL,
    ingestion_method TEXT NOT NULL,
    status           TEXT NOT NULL,           -- 'success' | 'failure'
    articles_fetched INTEGER DEFAULT 0,
    error_message    TEXT,
    timestamp        TEXT DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_logs_source    ON ingestion_logs(source);
CREATE INDEX IF NOT EXISTS idx_logs_timestamp ON ingestion_logs(timestamp DESC);

-- -------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS source_health (
    id                   INTEGER PRIMARY KEY AUTOINCREMENT,
    source_name          TEXT UNIQUE NOT NULL,
    last_success         TEXT,
    success_count        INTEGER DEFAULT 0,
    failure_count        INTEGER DEFAULT 0,
    consecutive_failures INTEGER DEFAULT 0,
    success_rate         REAL    DEFAULT 0.0,
    status               TEXT    DEFAULT 'active',   -- active | degraded | offline
    updated_at           TEXT    DEFAULT (datetime('now'))
);

-- -------------------------------------------------------------------------
-- Tracks page content hashes for PDF monitor change detection
CREATE TABLE IF NOT EXISTS pdf_page_hashes (
    source_name  TEXT PRIMARY KEY,
    page_hash    TEXT NOT NULL,
    known_urls   TEXT DEFAULT '[]',          -- JSON list of already-seen PDF URLs
    last_checked TEXT DEFAULT (datetime('now'))
);
"""


def initialize_db() -> None:
    """Create all tables and indexes. Safe to call multiple times (idempotent)."""
    with _connect() as conn:
        conn.executescript(_SCHEMA)
    logger.info("Database ready at %s", DB_PATH)


# ---------------------------------------------------------------------------
# Article helpers
# ---------------------------------------------------------------------------

def compute_content_hash(title: str, content: str, source: str) -> str:
    """Stable dedup key: first 500 chars of content + title + source."""
    raw = f"{source}|{title}|{content[:500]}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def save_article(article: Dict[str, Any]) -> bool:
    """
    Persist a normalised article dict.
    Returns True if saved (new), False if duplicate (skipped).
    """
    content_hash = compute_content_hash(
        article.get("title", ""),
        article.get("content", ""),
        article.get("source", ""),
    )
    try:
        with _connect() as conn:
            conn.execute(
                """
                INSERT INTO articles
                    (title, content, published_at, source, ingestion_method,
                     detected_symbols, language, processed_flag, content_hash, url)
                VALUES (?, ?, ?, ?, ?, ?, ?, 0, ?, ?)
                """,
                (
                    article.get("title", "").strip(),
                    article.get("content", ""),
                    article.get("published_at"),
                    article.get("source", ""),
                    article.get("ingestion_method", "unknown"),
                    json.dumps(article.get("detected_symbols", [])),
                    article.get("language", "en"),
                    content_hash,
                    article.get("url"),
                ),
            )
        logger.debug("Saved: [%s] %s", article.get("source"), article.get("title", "")[:70])
        return True
    except sqlite3.IntegrityError:
        logger.debug("Duplicate skipped: %s", article.get("title", "")[:70])
        return False


def get_articles(
    source: Optional[str] = None,
    limit: int = 50,
    unprocessed_only: bool = False,
    language: Optional[str] = None,
) -> List[Dict[str, Any]]:
    conditions: List[str] = []
    params: List[Any] = []

    if source:
        conditions.append("source = ?")
        params.append(source)
    if unprocessed_only:
        conditions.append("processed_flag = 0")
    if language:
        conditions.append("language = ?")
        params.append(language)

    where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    params.append(limit)

    with _connect() as conn:
        rows = conn.execute(
            f"SELECT * FROM articles {where} ORDER BY published_at DESC LIMIT ?",
            params,
        ).fetchall()
    return [dict(r) for r in rows]


def mark_article_processed(article_id: int) -> None:
    with _connect() as conn:
        conn.execute(
            "UPDATE articles SET processed_flag = 1 WHERE id = ?",
            (article_id,),
        )


# ---------------------------------------------------------------------------
# Ingestion log
# ---------------------------------------------------------------------------

def log_ingestion(
    source: str,
    method: str,
    status: str,
    articles_fetched: int = 0,
    error: Optional[str] = None,
) -> None:
    with _connect() as conn:
        conn.execute(
            """
            INSERT INTO ingestion_logs
                (source, ingestion_method, status, articles_fetched, error_message)
            VALUES (?, ?, ?, ?, ?)
            """,
            (source, method, status, articles_fetched, error),
        )


def get_ingestion_logs(source: Optional[str] = None, limit: int = 100) -> List[Dict[str, Any]]:
    params: List[Any] = []
    where = ""
    if source:
        where = "WHERE source = ?"
        params.append(source)
    params.append(limit)
    with _connect() as conn:
        rows = conn.execute(
            f"SELECT * FROM ingestion_logs {where} ORDER BY timestamp DESC LIMIT ?",
            params,
        ).fetchall()
    return [dict(r) for r in rows]


# ---------------------------------------------------------------------------
# Source health
# ---------------------------------------------------------------------------

def _compute_status(consecutive_failures: int, last_success: Optional[str]) -> str:
    now = datetime.now(tz=timezone.utc)
    if consecutive_failures >= HEALTH_DEGRADED_THRESHOLD:
        return "degraded"
    if last_success:
        try:
            last_dt = datetime.fromisoformat(last_success)
            if last_dt.tzinfo is None:
                last_dt = last_dt.replace(tzinfo=timezone.utc)
            hours_since = (now - last_dt).total_seconds() / 3600
            if hours_since >= HEALTH_OFFLINE_HOURS:
                return "offline"
        except ValueError:
            pass
    elif consecutive_failures > 0:
        # Never had a success
        return "degraded"
    return "active"


def update_source_health(source_name: str, success: bool) -> None:
    now = datetime.now(tz=timezone.utc).isoformat()
    with _connect() as conn:
        row = conn.execute(
            "SELECT * FROM source_health WHERE source_name = ?", (source_name,)
        ).fetchone()

        if row is None:
            success_count = 1 if success else 0
            failure_count = 0 if success else 1
            consecutive = 0 if success else 1
            last_success = now if success else None
            total = success_count + failure_count
            rate = success_count / total
            status = _compute_status(consecutive, last_success)
            conn.execute(
                """
                INSERT INTO source_health
                    (source_name, last_success, success_count, failure_count,
                     consecutive_failures, success_rate, status, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (source_name, last_success, success_count, failure_count,
                 consecutive, rate, status, now),
            )
        else:
            success_count = row["success_count"] + (1 if success else 0)
            failure_count = row["failure_count"] + (0 if success else 1)
            consecutive = 0 if success else row["consecutive_failures"] + 1
            last_success = now if success else row["last_success"]
            total = success_count + failure_count
            rate = success_count / total if total > 0 else 0.0
            status = _compute_status(consecutive, last_success)
            conn.execute(
                """
                UPDATE source_health
                SET last_success = ?, success_count = ?, failure_count = ?,
                    consecutive_failures = ?, success_rate = ?, status = ?, updated_at = ?
                WHERE source_name = ?
                """,
                (last_success, success_count, failure_count,
                 consecutive, rate, status, now, source_name),
            )


def get_source_health(source_name: Optional[str] = None) -> List[Dict[str, Any]]:
    with _connect() as conn:
        if source_name:
            rows = conn.execute(
                "SELECT * FROM source_health WHERE source_name = ?", (source_name,)
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM source_health ORDER BY source_name"
            ).fetchall()
    return [dict(r) for r in rows]


# ---------------------------------------------------------------------------
# PDF page-hash store
# ---------------------------------------------------------------------------

def get_page_hash(source_name: str) -> Optional[str]:
    with _connect() as conn:
        row = conn.execute(
            "SELECT page_hash FROM pdf_page_hashes WHERE source_name = ?", (source_name,)
        ).fetchone()
    return row["page_hash"] if row else None


def get_known_pdf_urls(source_name: str) -> List[str]:
    with _connect() as conn:
        row = conn.execute(
            "SELECT known_urls FROM pdf_page_hashes WHERE source_name = ?", (source_name,)
        ).fetchone()
    return json.loads(row["known_urls"]) if row and row["known_urls"] else []


def set_page_state(source_name: str, page_hash: str, known_urls: List[str]) -> None:
    with _connect() as conn:
        conn.execute(
            """
            INSERT INTO pdf_page_hashes (source_name, page_hash, known_urls, last_checked)
            VALUES (?, ?, ?, datetime('now'))
            ON CONFLICT(source_name) DO UPDATE
            SET page_hash = excluded.page_hash,
                known_urls = excluded.known_urls,
                last_checked = excluded.last_checked
            """,
            (source_name, page_hash, json.dumps(known_urls)),
        )
