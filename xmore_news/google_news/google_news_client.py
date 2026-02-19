"""
google_news/google_news_client.py — Xmore News Ingestion Layer

Google News RSS fallback / supplementary ingestion.

Constructs query-specific RSS URLs targeting Google News Egypt context:
  https://news.google.com/rss/search?q={query}&hl=en&gl=EG&ceid=EG:en

Handles:
  - Per-query rate limiting
  - Process-level deduplication
  - Retry with backoff
  - Structured health + ingestion logging
"""

from __future__ import annotations

import hashlib
import logging
import time
from typing import Dict, List, Optional
from urllib.parse import quote_plus

import feedparser
import requests

import db
from config import MAX_RETRIES, REQUEST_DELAY_SECONDS, REQUEST_TIMEOUT_SECONDS, USER_AGENT
from models import Article, IngestionAttempt
from rss.rss_registry import RSS_SOURCES
from utils import clean_text, detect_language, parse_date, retry, strip_html

logger = logging.getLogger(__name__)

# Google News RSS template — Egypt locale for more relevant results
_GN_TEMPLATE = (
    "https://news.google.com/rss/search"
    "?q={query}&hl=en-US&gl=EG&ceid=EG:en"
)

# Module-level state
_seen_hashes: set[str] = set()
_last_call_ts: float = 0.0


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _entry_hash(title: str, published: str) -> str:
    return hashlib.md5(f"{title}|{published}".encode("utf-8")).hexdigest()


def _rate_limit() -> None:
    global _last_call_ts
    elapsed = time.monotonic() - _last_call_ts
    if elapsed < REQUEST_DELAY_SECONDS:
        time.sleep(REQUEST_DELAY_SECONDS - elapsed)
    _last_call_ts = time.monotonic()


@retry(
    max_attempts=MAX_RETRIES,
    delay=2.0,
    backoff=2.0,
    exceptions=(requests.RequestException, OSError),
)
def _fetch_gnews_text(url: str) -> str:
    resp = requests.get(
        url,
        headers={"User-Agent": USER_AGENT},
        timeout=REQUEST_TIMEOUT_SECONDS,
    )
    resp.raise_for_status()
    return resp.text


def reset_seen_hashes() -> None:
    """Call at the start of each scheduled run to allow re-ingestion."""
    _seen_hashes.clear()


# ---------------------------------------------------------------------------
# Core fetch function
# ---------------------------------------------------------------------------

def fetch_google_news(
    query: str,
    source_label: str,
    max_results: int = 20,
) -> List[Article]:
    """
    Fetch up to max_results articles from Google News RSS for a query.

    Args:
        query        : search query string
        source_label : the Article.source value to assign
        max_results  : max entries to process per query

    Returns list of newly saved Articles. Never raises.
    """
    _rate_limit()
    url = _GN_TEMPLATE.format(query=quote_plus(query))
    logger.info("[GNews][%s] query: %s", source_label, query[:70])

    start = time.monotonic()
    articles: List[Article] = []
    error: Optional[str] = None
    success = False

    try:
        raw_text = _fetch_gnews_text(url)
        feed = feedparser.parse(raw_text)

        for entry in feed.entries[:max_results]:
            title = (getattr(entry, "title", None) or "").strip()
            if not title:
                continue

            published_raw = (
                getattr(entry, "published", None)
                or getattr(entry, "updated", None)
                or ""
            )
            h = _entry_hash(title, published_raw)
            if h in _seen_hashes:
                continue
            _seen_hashes.add(h)

            link = getattr(entry, "link", "") or ""
            summary = getattr(entry, "summary", "") or ""
            content = strip_html(summary) if summary and "<" in summary else clean_text(summary or title)
            if len(content) > 6_000:
                content = content[:6_000] + " [...]"

            published_at = parse_date(published_raw)
            full_text = f"{title} {content}"

            article = Article(
                title=title,
                content=content,
                source=source_label,
                ingestion_method="google_news",
                published_at=published_at,
                url=link,
                language=detect_language(full_text),
            )
            if db.save_article(article):
                articles.append(article)

        success = True
        logger.info("[GNews][%s] %d new article(s)", source_label, len(articles))

    except Exception as exc:
        error = str(exc)
        logger.error("[GNews][%s] Failed: %s", source_label, exc)

    duration_ms = int((time.monotonic() - start) * 1000)
    health_key = f"{source_label.lower().replace(' ', '_').replace('&', 'and')}_gnews"
    db.record_ingestion(IngestionAttempt(
        source=source_label,
        method="google_news",
        success=success,
        articles_count=len(articles),
        error=error,
        duration_ms=duration_ms,
    ))
    db.update_health(health_key, success)

    return articles


# ---------------------------------------------------------------------------
# Per-source convenience wrapper
# ---------------------------------------------------------------------------

def fetch_google_news_for_source(
    source_key: str,
    max_results_per_query: int = 15,
) -> List[Article]:
    """
    Run all configured Google News queries for a registry source key.
    Returns merged, deduplicated list of new Articles.
    """
    if source_key not in RSS_SOURCES:
        logger.warning("[GNews] Unknown source key: %s", source_key)
        return []

    source_def = RSS_SOURCES[source_key]
    all_articles: List[Article] = []

    for query in source_def.google_news_queries:
        articles = fetch_google_news(
            query=query,
            source_label=source_def.name,
            max_results=max_results_per_query,
        )
        all_articles.extend(articles)

    return all_articles


def fetch_google_news_all(max_results_per_query: int = 15) -> Dict[str, List[Article]]:
    """Run Google News for every source in the registry."""
    return {
        key: fetch_google_news_for_source(key, max_results_per_query)
        for key in RSS_SOURCES
    }
