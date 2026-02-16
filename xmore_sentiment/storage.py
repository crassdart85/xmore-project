"""Persistence layer for sentiment pipeline (SQLite/PostgreSQL)."""

from __future__ import annotations

import hashlib
import json
import os
import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Iterator

from xmore_sentiment.schemas import ArticleInput, ExtractedFacts, SentimentResult, ValidationMetrics


def _to_iso(dt: datetime) -> str:
    return dt.isoformat()


@dataclass
class StorageConfig:
    sqlite_path: str = os.getenv("XMORE_SENTIMENT_DB_PATH", "xmore_sentiment.db")
    database_url: str | None = os.getenv("DATABASE_URL")
    price_db_path: str = os.getenv("XMORE_PRICES_DB_PATH", "stocks.db")


class SentimentStorage:
    """Unified storage over SQLite/PostgreSQL with auditable tables."""

    def __init__(self, config: StorageConfig | None = None) -> None:
        self.config = config or StorageConfig()
        self.is_postgres = bool(self.config.database_url)
        self._sqlite_path = Path(self.config.sqlite_path)
        self._sqlite_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    @contextmanager
    def _connect(self) -> Iterator[Any]:
        if self.is_postgres:
            import psycopg2

            conn = psycopg2.connect(self.config.database_url)  # type: ignore[arg-type]
            try:
                yield conn
                conn.commit()
            finally:
                conn.close()
        else:
            conn = sqlite3.connect(self._sqlite_path)
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

            cur.execute(
                f"""
                CREATE TABLE IF NOT EXISTS articles (
                    id {auto_id},
                    title TEXT NOT NULL,
                    content TEXT NOT NULL,
                    published_at TIMESTAMP NOT NULL,
                    source TEXT NOT NULL,
                    url TEXT NOT NULL,
                    url_hash TEXT NOT NULL UNIQUE,
                    mentioned_symbols {json_type} NOT NULL,
                    processed_flag {bool_type} NOT NULL DEFAULT 0,
                    region TEXT NOT NULL DEFAULT 'global',
                    created_at TIMESTAMP NOT NULL DEFAULT {ts_default}
                )
                """
            )
            cur.execute("CREATE INDEX IF NOT EXISTS idx_articles_processed ON articles(processed_flag)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_articles_published_at ON articles(published_at DESC)")

            cur.execute(
                f"""
                CREATE TABLE IF NOT EXISTS extracted_facts (
                    id {auto_id},
                    article_id INTEGER NOT NULL REFERENCES articles(id),
                    facts_json {json_type} NOT NULL,
                    certainty REAL NOT NULL,
                    created_at TIMESTAMP NOT NULL DEFAULT {ts_default},
                    UNIQUE(article_id)
                )
                """
            )

            cur.execute(
                f"""
                CREATE TABLE IF NOT EXISTS sentiment_scores (
                    id {auto_id},
                    article_id INTEGER NOT NULL REFERENCES articles(id),
                    symbol TEXT NOT NULL,
                    raw_score REAL NOT NULL,
                    sentiment_score REAL NOT NULL,
                    confidence REAL NOT NULL,
                    keyword_polarity REAL NOT NULL,
                    disagreement REAL NOT NULL,
                    uncertain {bool_type} NOT NULL DEFAULT 0,
                    publish_date TIMESTAMP NOT NULL,
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
            cur.execute("CREATE INDEX IF NOT EXISTS idx_sentiment_symbol_date ON sentiment_scores(symbol, publish_date DESC)")

            cur.execute(
                f"""
                CREATE TABLE IF NOT EXISTS validation_metrics (
                    id {auto_id},
                    sample_size INTEGER NOT NULL,
                    corr_1d REAL,
                    corr_3d REAL,
                    corr_5d REAL,
                    accuracy_1d REAL,
                    accuracy_3d REAL,
                    accuracy_5d REAL,
                    weight_multiplier REAL NOT NULL,
                    created_at TIMESTAMP NOT NULL DEFAULT {ts_default}
                )
                """
            )

    def upsert_article(self, article: ArticleInput) -> int | None:
        with self._connect() as conn:
            cur = conn.cursor()
            mentioned_json = json.dumps(article.mentioned_symbols, ensure_ascii=False)

            if self.is_postgres:
                cur.execute(
                    """
                    INSERT INTO articles (title, content, published_at, source, url, url_hash, mentioned_symbols, processed_flag, region)
                    VALUES (%s, %s, %s, %s, %s, %s, %s::jsonb, %s, %s)
                    ON CONFLICT (url_hash) DO UPDATE SET
                        title = EXCLUDED.title,
                        content = EXCLUDED.content,
                        source = EXCLUDED.source
                    RETURNING id
                    """,
                    (
                        article.title,
                        article.content,
                        article.published_at,
                        article.source,
                        str(article.url),
                        article.url_hash,
                        mentioned_json,
                        int(article.processed_flag),
                        article.region,
                    ),
                )
                row = cur.fetchone()
                return int(row[0]) if row else None

            cur.execute(
                """
                INSERT INTO articles (title, content, published_at, source, url, url_hash, mentioned_symbols, processed_flag, region)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(url_hash) DO UPDATE SET
                    title = excluded.title,
                    content = excluded.content,
                    source = excluded.source
                """,
                (
                    article.title,
                    article.content,
                    _to_iso(article.published_at),
                    article.source,
                    str(article.url),
                    article.url_hash,
                    mentioned_json,
                    int(article.processed_flag),
                    article.region,
                ),
            )
            cur.execute("SELECT id FROM articles WHERE url_hash = ?", (article.url_hash,))
            row = cur.fetchone()
            return int(row[0]) if row else None

    def save_facts(self, article_id: int, facts: ExtractedFacts) -> None:
        payload = facts.model_dump_json()
        with self._connect() as conn:
            cur = conn.cursor()
            if self.is_postgres:
                cur.execute(
                    """
                    INSERT INTO extracted_facts (article_id, facts_json, certainty)
                    VALUES (%s, %s::jsonb, %s)
                    ON CONFLICT (article_id) DO UPDATE SET
                        facts_json = EXCLUDED.facts_json,
                        certainty = EXCLUDED.certainty
                    """,
                    (article_id, payload, facts.certainty),
                )
            else:
                cur.execute(
                    """
                    INSERT INTO extracted_facts (article_id, facts_json, certainty)
                    VALUES (?, ?, ?)
                    ON CONFLICT(article_id) DO UPDATE SET
                        facts_json = excluded.facts_json,
                        certainty = excluded.certainty
                    """,
                    (article_id, payload, facts.certainty),
                )

    def save_sentiment_result(self, result: SentimentResult) -> None:
        with self._connect() as conn:
            cur = conn.cursor()
            params = (
                result.article_id,
                result.symbol,
                result.raw_score,
                result.final_sentiment,
                result.confidence,
                result.keyword_polarity,
                result.disagreement,
                int(result.uncertain),
                result.publish_date if self.is_postgres else _to_iso(result.publish_date),
                result.price_at_publish,
                result.price_1d,
                result.price_3d,
                result.price_5d,
                result.return_1d,
                result.return_3d,
                result.return_5d,
            )

            if self.is_postgres:
                cur.execute(
                    """
                    INSERT INTO sentiment_scores (
                        article_id, symbol, raw_score, sentiment_score, confidence, keyword_polarity,
                        disagreement, uncertain, publish_date, price_at_publish, price_1d, price_3d, price_5d,
                        return_1d, return_3d, return_5d
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    params,
                )
            else:
                cur.execute(
                    """
                    INSERT INTO sentiment_scores (
                        article_id, symbol, raw_score, sentiment_score, confidence, keyword_polarity,
                        disagreement, uncertain, publish_date, price_at_publish, price_1d, price_3d, price_5d,
                        return_1d, return_3d, return_5d
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    params,
                )

    def save_validation_metrics(self, metrics: ValidationMetrics) -> None:
        with self._connect() as conn:
            cur = conn.cursor()
            values = (
                metrics.sample_size,
                metrics.corr_1d,
                metrics.corr_3d,
                metrics.corr_5d,
                metrics.accuracy_1d,
                metrics.accuracy_3d,
                metrics.accuracy_5d,
                metrics.weight_multiplier,
            )
            if self.is_postgres:
                cur.execute(
                    """
                    INSERT INTO validation_metrics (
                        sample_size, corr_1d, corr_3d, corr_5d, accuracy_1d, accuracy_3d, accuracy_5d, weight_multiplier
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    values,
                )
            else:
                cur.execute(
                    """
                    INSERT INTO validation_metrics (
                        sample_size, corr_1d, corr_3d, corr_5d, accuracy_1d, accuracy_3d, accuracy_5d, weight_multiplier
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    values,
                )

    def get_current_weight_multiplier(self) -> float:
        with self._connect() as conn:
            cur = conn.cursor()
            cur.execute("SELECT weight_multiplier FROM validation_metrics ORDER BY id DESC LIMIT 1")
            row = cur.fetchone()
            if not row:
                return 1.0
            return float(row[0] if self.is_postgres else row["weight_multiplier"])

    def fetch_sentiment_history(self, limit: int = 500) -> list[dict]:
        with self._connect() as conn:
            cur = conn.cursor()
            if self.is_postgres:
                cur.execute(
                    """
                    SELECT sentiment_score, return_1d, return_3d, return_5d
                    FROM sentiment_scores
                    ORDER BY id DESC
                    LIMIT %s
                    """,
                    (limit,),
                )
                rows = cur.fetchall()
                return [
                    {
                        "sentiment_score": r[0],
                        "return_1d": r[1],
                        "return_3d": r[2],
                        "return_5d": r[3],
                    }
                    for r in rows
                ]
            cur.execute(
                """
                SELECT sentiment_score, return_1d, return_3d, return_5d
                FROM sentiment_scores
                ORDER BY id DESC
                LIMIT ?
                """,
                (limit,),
            )
            rows = cur.fetchall()
            return [dict(r) for r in rows]

    def fetch_unprocessed_articles(self, limit: int = 100) -> list[ArticleInput]:
        with self._connect() as conn:
            cur = conn.cursor()
            if self.is_postgres:
                cur.execute(
                    """
                    SELECT id, title, content, published_at, source, url, url_hash, mentioned_symbols, processed_flag, region
                    FROM articles
                    WHERE processed_flag = FALSE
                    ORDER BY published_at DESC
                    LIMIT %s
                    """,
                    (limit,),
                )
                rows = cur.fetchall()
                out: list[ArticleInput] = []
                for row in rows:
                    symbols = row[7] if isinstance(row[7], list) else json.loads(row[7] or "[]")
                    out.append(
                        ArticleInput(
                            id=row[0],
                            title=row[1],
                            content=row[2],
                            published_at=row[3],
                            source=row[4],
                            url=row[5],
                            url_hash=row[6],
                            mentioned_symbols=symbols,
                            processed_flag=bool(row[8]),
                            region=row[9],
                        )
                    )
                return out

            cur.execute(
                """
                SELECT id, title, content, published_at, source, url, url_hash, mentioned_symbols, processed_flag, region
                FROM articles
                WHERE processed_flag = 0
                ORDER BY published_at DESC
                LIMIT ?
                """,
                (limit,),
            )
            rows = cur.fetchall()
            return [
                ArticleInput(
                    id=r["id"],
                    title=r["title"],
                    content=r["content"],
                    published_at=datetime.fromisoformat(r["published_at"]),
                    source=r["source"],
                    url=r["url"],
                    url_hash=r["url_hash"],
                    mentioned_symbols=json.loads(r["mentioned_symbols"] or "[]"),
                    processed_flag=bool(r["processed_flag"]),
                    region=r["region"],
                )
                for r in rows
            ]

    def mark_article_processed(self, article_id: int) -> None:
        with self._connect() as conn:
            cur = conn.cursor()
            if self.is_postgres:
                cur.execute("UPDATE articles SET processed_flag = TRUE WHERE id = %s", (article_id,))
            else:
                cur.execute("UPDATE articles SET processed_flag = 1 WHERE id = ?", (article_id,))

    def import_articles_from_news_db(self, news_db_path: str) -> int:
        """
        Import rows from xmore_news.news_articles into sentiment articles table.
        """
        src = sqlite3.connect(news_db_path)
        src.row_factory = sqlite3.Row
        try:
            rows = src.execute(
                """
                SELECT title, content, published_at, source, url, mentioned_symbols, region
                FROM news_articles
                ORDER BY published_at DESC
                """
            ).fetchall()
        finally:
            src.close()

        inserted = 0
        for row in rows:
            url = str(row["url"])
            url_hash = hashlib.sha256(url.encode("utf-8")).hexdigest()
            article = ArticleInput(
                title=row["title"],
                content=row["content"] or "",
                published_at=_parse_datetime(row["published_at"]),
                source=row["source"],
                url=url,
                url_hash=url_hash,
                region=(row["region"] or "global"),
                mentioned_symbols=json.loads(row["mentioned_symbols"] or "[]"),
            )
            article_id = self.upsert_article(article)
            if article_id:
                inserted += 1
        return inserted

    def enrich_with_prices(self, result: SentimentResult) -> SentimentResult:
        """
        Populate publish and forward prices from local `prices` table.
        """
        symbol = result.symbol.replace(".CA", "")
        if symbol == "MARKET":
            return result

        prices_db = Path(self.config.price_db_path)
        if not prices_db.exists():
            return result

        conn = sqlite3.connect(prices_db)
        conn.row_factory = sqlite3.Row
        try:
            pub_day = result.publish_date.date().isoformat()
            p0 = _fetch_close_at_or_after(conn, symbol, pub_day, max_days_ahead=2)
            p1 = _fetch_close_at_or_after(conn, symbol, (result.publish_date.date() + timedelta(days=1)).isoformat(), max_days_ahead=2)
            p3 = _fetch_close_at_or_after(conn, symbol, (result.publish_date.date() + timedelta(days=3)).isoformat(), max_days_ahead=3)
            p5 = _fetch_close_at_or_after(conn, symbol, (result.publish_date.date() + timedelta(days=5)).isoformat(), max_days_ahead=3)
        finally:
            conn.close()

        result.price_at_publish = p0
        result.price_1d = p1
        result.price_3d = p3
        result.price_5d = p5
        result.return_1d = _pct_return(p0, p1)
        result.return_3d = _pct_return(p0, p3)
        result.return_5d = _pct_return(p0, p5)
        return result


def _fetch_close_at_or_after(conn: sqlite3.Connection, symbol: str, day_iso: str, max_days_ahead: int) -> float | None:
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
        (symbol, f"{symbol}.CA", day_iso, day_iso, max_days_ahead),
    ).fetchone()
    return float(row["close"]) if row else None


def _pct_return(p0: float | None, p1: float | None) -> float | None:
    if p0 is None or p1 is None or abs(p0) < 1e-12:
        return None
    return (p1 - p0) / p0


def _parse_datetime(value: object) -> datetime:
    text = str(value or "").strip()
    if not text:
        return datetime.utcnow()
    for candidate in (text.replace("Z", "+00:00"), text):
        try:
            return datetime.fromisoformat(candidate)
        except ValueError:
            continue
    try:
        return datetime.strptime(text[:19], "%Y-%m-%d %H:%M:%S")
    except ValueError:
        return datetime.utcnow()
