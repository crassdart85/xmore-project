"""Storage layer for Event Intelligence and Sentiment."""

from __future__ import annotations

import json
import os
import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Iterator

from pydantic import BaseModel, ConfigDict, Field, HttpUrl

from xmore_event_intel import config


class ArticleRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str
    content: str
    published_at: datetime
    source: str
    url: HttpUrl | str
    detected_symbols: list[str] = Field(default_factory=list)
    raw_html: str = ""


class StructuredEventRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    article_id: int
    symbol: str
    event_type: str
    event_strength: float
    revenue_change_percent: float | None = None
    profit_change_percent: float | None = None
    earnings_surprise: float | None = None
    extracted_payload: dict[str, Any] = Field(default_factory=dict)


class SentimentScoreRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    article_id: int
    symbol: str
    event_type: str
    sentiment_score: float
    confidence: float = Field(ge=0.0, le=1.0)
    publish_time: datetime
    price_at_publish: float | None = None
    price_1d: float | None = None
    price_3d: float | None = None
    price_5d: float | None = None
    return_1d: float | None = None
    return_3d: float | None = None
    return_5d: float | None = None


@dataclass
class StorageConfig:
    sqlite_path: str = config.DEFAULT_SQLITE_DB_PATH
    database_url: str | None = os.getenv("DATABASE_URL")
    price_db_path: str = config.PRICE_DB_PATH


class EventIntelStorage:
    """SQLite/PostgreSQL storage with auditable event history."""

    def __init__(self, cfg: StorageConfig | None = None) -> None:
        self.cfg = cfg or StorageConfig()
        self.is_postgres = bool(self.cfg.database_url)
        self.sqlite_path = Path(self.cfg.sqlite_path)
        self.sqlite_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    @contextmanager
    def _connect(self) -> Iterator[Any]:
        if self.is_postgres:
            import psycopg2

            conn = psycopg2.connect(self.cfg.database_url)  # type: ignore[arg-type]
            try:
                yield conn
                conn.commit()
            finally:
                conn.close()
            return

        conn = sqlite3.connect(self.sqlite_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def _init_schema(self) -> None:
        with self._connect() as conn:
            cur = conn.cursor()
            auto_id = "SERIAL PRIMARY KEY" if self.is_postgres else "INTEGER PRIMARY KEY AUTOINCREMENT"
            bool_type = "BOOLEAN" if self.is_postgres else "INTEGER"
            json_type = "JSONB" if self.is_postgres else "TEXT"
            ts_default = "NOW()" if self.is_postgres else "CURRENT_TIMESTAMP"
            metadata_default = "'{}'::jsonb" if self.is_postgres else "'{}'"

            cur.execute(
                f"""
                CREATE TABLE IF NOT EXISTS articles (
                    id {auto_id},
                    title TEXT NOT NULL,
                    content TEXT NOT NULL,
                    published_at TIMESTAMP NOT NULL,
                    source TEXT NOT NULL,
                    url TEXT NOT NULL UNIQUE,
                    detected_symbols {json_type} NOT NULL,
                    raw_html TEXT,
                    created_at TIMESTAMP NOT NULL DEFAULT {ts_default}
                )
                """
            )
            cur.execute("CREATE INDEX IF NOT EXISTS idx_articles_published_at ON articles(published_at DESC)")

            cur.execute(
                f"""
                CREATE TABLE IF NOT EXISTS structured_events (
                    id {auto_id},
                    article_id INTEGER NOT NULL REFERENCES articles(id),
                    symbol TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    event_strength REAL NOT NULL,
                    revenue_change_percent REAL,
                    profit_change_percent REAL,
                    earnings_surprise REAL,
                    extracted_payload {json_type} NOT NULL,
                    created_at TIMESTAMP NOT NULL DEFAULT {ts_default}
                )
                """
            )
            cur.execute("CREATE INDEX IF NOT EXISTS idx_structured_events_symbol ON structured_events(symbol)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_structured_events_event_type ON structured_events(event_type)")

            cur.execute(
                f"""
                CREATE TABLE IF NOT EXISTS sentiment_scores (
                    id {auto_id},
                    article_id INTEGER NOT NULL REFERENCES articles(id),
                    symbol TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    sentiment_score REAL NOT NULL,
                    confidence REAL NOT NULL,
                    publish_time TIMESTAMP NOT NULL,
                    price_at_publish REAL,
                    price_1d REAL,
                    price_3d REAL,
                    price_5d REAL,
                    return_1d REAL,
                    return_3d REAL,
                    return_5d REAL,
                    created_at TIMESTAMP NOT NULL DEFAULT {ts_default}
                )
                """
            )
            cur.execute("CREATE INDEX IF NOT EXISTS idx_sentiment_symbol_time ON sentiment_scores(symbol, publish_time DESC)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_sentiment_event_type ON sentiment_scores(event_type)")

            cur.execute(
                f"""
                CREATE TABLE IF NOT EXISTS performance_metrics (
                    id {auto_id},
                    metric_date TIMESTAMP NOT NULL,
                    metric_name TEXT NOT NULL,
                    metric_value REAL,
                    event_type TEXT,
                    metadata_json {json_type} NOT NULL DEFAULT {metadata_default},
                    created_at TIMESTAMP NOT NULL DEFAULT {ts_default}
                )
                """
            )

            cur.execute(
                f"""
                CREATE TABLE IF NOT EXISTS event_type_weights (
                    event_type TEXT PRIMARY KEY,
                    weight REAL NOT NULL,
                    updated_at TIMESTAMP NOT NULL DEFAULT {ts_default}
                )
                """
            )

    def upsert_article(self, article: ArticleRecord) -> int:
        payload = json.dumps(article.detected_symbols, ensure_ascii=False)
        with self._connect() as conn:
            cur = conn.cursor()
            if self.is_postgres:
                cur.execute(
                    """
                    INSERT INTO articles (title, content, published_at, source, url, detected_symbols, raw_html)
                    VALUES (%s, %s, %s, %s, %s, %s::jsonb, %s)
                    ON CONFLICT (url) DO UPDATE SET
                        title = EXCLUDED.title,
                        content = EXCLUDED.content,
                        source = EXCLUDED.source,
                        detected_symbols = EXCLUDED.detected_symbols,
                        raw_html = EXCLUDED.raw_html
                    RETURNING id
                    """,
                    (
                        article.title,
                        article.content,
                        article.published_at,
                        article.source,
                        str(article.url),
                        payload,
                        article.raw_html,
                    ),
                )
                row = cur.fetchone()
                return int(row[0])

            cur.execute(
                """
                INSERT INTO articles (title, content, published_at, source, url, detected_symbols, raw_html)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(url) DO UPDATE SET
                    title = excluded.title,
                    content = excluded.content,
                    source = excluded.source,
                    detected_symbols = excluded.detected_symbols,
                    raw_html = excluded.raw_html
                """,
                (
                    article.title,
                    article.content,
                    article.published_at.isoformat(),
                    article.source,
                    str(article.url),
                    payload,
                    article.raw_html,
                ),
            )
            cur.execute("SELECT id FROM articles WHERE url = ?", (str(article.url),))
            row = cur.fetchone()
            return int(row["id"])

    def save_structured_event(self, event: StructuredEventRecord) -> int:
        payload_json = json.dumps(event.extracted_payload, ensure_ascii=False)
        with self._connect() as conn:
            cur = conn.cursor()
            params = (
                event.article_id,
                event.symbol,
                event.event_type,
                event.event_strength,
                event.revenue_change_percent,
                event.profit_change_percent,
                event.earnings_surprise,
                payload_json,
            )
            if self.is_postgres:
                cur.execute(
                    """
                    INSERT INTO structured_events (
                        article_id, symbol, event_type, event_strength, revenue_change_percent,
                        profit_change_percent, earnings_surprise, extracted_payload
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s::jsonb)
                    RETURNING id
                    """,
                    params,
                )
                row = cur.fetchone()
                return int(row[0])

            cur.execute(
                """
                INSERT INTO structured_events (
                    article_id, symbol, event_type, event_strength, revenue_change_percent,
                    profit_change_percent, earnings_surprise, extracted_payload
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                params,
            )
            return int(cur.lastrowid)

    def save_sentiment_score(self, row: SentimentScoreRecord) -> int:
        with self._connect() as conn:
            cur = conn.cursor()
            params = (
                row.article_id,
                row.symbol,
                row.event_type,
                row.sentiment_score,
                row.confidence,
                row.publish_time if self.is_postgres else row.publish_time.isoformat(),
                row.price_at_publish,
                row.price_1d,
                row.price_3d,
                row.price_5d,
                row.return_1d,
                row.return_3d,
                row.return_5d,
            )
            if self.is_postgres:
                cur.execute(
                    """
                    INSERT INTO sentiment_scores (
                        article_id, symbol, event_type, sentiment_score, confidence, publish_time,
                        price_at_publish, price_1d, price_3d, price_5d, return_1d, return_3d, return_5d
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING id
                    """,
                    params,
                )
                row_id = cur.fetchone()
                return int(row_id[0])

            cur.execute(
                """
                INSERT INTO sentiment_scores (
                    article_id, symbol, event_type, sentiment_score, confidence, publish_time,
                    price_at_publish, price_1d, price_3d, price_5d, return_1d, return_3d, return_5d
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                params,
            )
            return int(cur.lastrowid)

    def save_metric(
        self,
        metric_name: str,
        metric_value: float | None,
        *,
        event_type: str | None = None,
        metadata: dict[str, Any] | None = None,
        metric_date: datetime | None = None,
    ) -> None:
        with self._connect() as conn:
            cur = conn.cursor()
            payload = json.dumps(metadata or {}, ensure_ascii=False)
            dt = metric_date or datetime.utcnow()
            params = (
                dt if self.is_postgres else dt.isoformat(),
                metric_name,
                metric_value,
                event_type,
                payload,
            )
            if self.is_postgres:
                cur.execute(
                    """
                    INSERT INTO performance_metrics (metric_date, metric_name, metric_value, event_type, metadata_json)
                    VALUES (%s, %s, %s, %s, %s::jsonb)
                    """,
                    params,
                )
            else:
                cur.execute(
                    """
                    INSERT INTO performance_metrics (metric_date, metric_name, metric_value, event_type, metadata_json)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    params,
                )

    def get_event_weights(self) -> dict[str, float]:
        with self._connect() as conn:
            cur = conn.cursor()
            cur.execute("SELECT event_type, weight FROM event_type_weights")
            rows = cur.fetchall()
            out: dict[str, float] = {}
            for r in rows:
                if self.is_postgres:
                    out[str(r[0])] = float(r[1])
                else:
                    out[str(r["event_type"])] = float(r["weight"])
            return out

    def upsert_event_weight(self, event_type: str, weight: float) -> None:
        with self._connect() as conn:
            cur = conn.cursor()
            if self.is_postgres:
                cur.execute(
                    """
                    INSERT INTO event_type_weights (event_type, weight, updated_at)
                    VALUES (%s, %s, NOW())
                    ON CONFLICT (event_type) DO UPDATE SET
                        weight = EXCLUDED.weight,
                        updated_at = NOW()
                    """,
                    (event_type, weight),
                )
            else:
                cur.execute(
                    """
                    INSERT INTO event_type_weights (event_type, weight, updated_at)
                    VALUES (?, ?, CURRENT_TIMESTAMP)
                    ON CONFLICT(event_type) DO UPDATE SET
                        weight = excluded.weight,
                        updated_at = CURRENT_TIMESTAMP
                    """,
                    (event_type, weight),
                )

    def fetch_scoring_history(self, limit: int = 500) -> list[dict]:
        with self._connect() as conn:
            cur = conn.cursor()
            if self.is_postgres:
                cur.execute(
                    """
                    SELECT event_type, sentiment_score, return_1d, return_3d, return_5d
                    FROM sentiment_scores
                    ORDER BY id DESC
                    LIMIT %s
                    """,
                    (limit,),
                )
                rows = cur.fetchall()
                return [
                    {
                        "event_type": r[0],
                        "sentiment_score": float(r[1]),
                        "return_1d": r[2],
                        "return_3d": r[3],
                        "return_5d": r[4],
                    }
                    for r in rows
                ]

            cur.execute(
                """
                SELECT event_type, sentiment_score, return_1d, return_3d, return_5d
                FROM sentiment_scores
                ORDER BY id DESC
                LIMIT ?
                """,
                (limit,),
            )
            return [dict(r) for r in cur.fetchall()]

    def enrich_forward_prices(self, symbol: str, publish_time: datetime) -> dict[str, float | None]:
        ticker = symbol.replace(".CA", "").upper()
        price_db = Path(self.cfg.price_db_path)
        if not price_db.exists():
            return {
                "price_at_publish": None,
                "price_1d": None,
                "price_3d": None,
                "price_5d": None,
                "return_1d": None,
                "return_3d": None,
                "return_5d": None,
            }

        conn = sqlite3.connect(price_db)
        conn.row_factory = sqlite3.Row
        try:
            base_date = publish_time.date()
            p0 = _fetch_close_near(conn, ticker, base_date, 2)
            p1 = _fetch_close_near(conn, ticker, base_date + timedelta(days=1), 3)
            p3 = _fetch_close_near(conn, ticker, base_date + timedelta(days=3), 3)
            p5 = _fetch_close_near(conn, ticker, base_date + timedelta(days=5), 3)
        finally:
            conn.close()

        return {
            "price_at_publish": p0,
            "price_1d": p1,
            "price_3d": p3,
            "price_5d": p5,
            "return_1d": _safe_return(p0, p1),
            "return_3d": _safe_return(p0, p3),
            "return_5d": _safe_return(p0, p5),
        }


def _fetch_close_near(conn: sqlite3.Connection, symbol: str, start_day, max_days: int) -> float | None:
    row = conn.execute(
        """
        SELECT close
        FROM prices
        WHERE symbol IN (?, ?)
          AND date >= ?
          AND date <= date(?, '+' || ? || ' day')
        ORDER BY date ASC
        LIMIT 1
        """,
        (symbol, f"{symbol}.CA", start_day.isoformat(), start_day.isoformat(), max_days),
    ).fetchone()
    return float(row["close"]) if row else None


def _safe_return(p0: float | None, p1: float | None) -> float | None:
    if p0 in (None, 0) or p1 is None:
        return None
    return (p1 - p0) / p0
