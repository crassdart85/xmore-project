"""
rss/rss_client.py — Xmore News Ingestion Layer

Official RSS feed ingestion with:
  - requests-based fetching (controls timeout properly)
  - feedparser for parsing
  - 3-attempt exponential-backoff retry
  - In-process dedup via SHA-256(title + published)
  - Last-fetch timestamp filtering
  - Structured health + ingestion logging
"""

from __future__ import annotations

import hashlib
import logging
import time
from datetime import datetime, timezone
from typing import Dict, List, Optional

import feedparser
import requests

import db
from config import MAX_RETRIES, REQUEST_DELAY_SECONDS, REQUEST_TIMEOUT_SECONDS, USER_AGENT
from models import Article, IngestionAttempt
from rss.rss_registry import RSS_SOURCES, RSSSourceDef
from utils import clean_text, detect_language, parse_date, retry, strip_html

logger = logging.getLogger(__name__)

# Module-level state
_last_fetch_ts: Dict[str, float] = {}     # source_key -> monotonic timestamp
_seen_hashes: set[str] = set()            # dedup within a process run


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _entry_hash(title: str, published: str) -> str:
    return hashlib.sha256(f"{title}|{published}".encode("utf-8")).hexdigest()


@retry(
    max_attempts=MAX_RETRIES,
    delay=2.0,
    backoff=2.0,
    exceptions=(requests.RequestException, OSError),
)
def _fetch_feed_text(url: str) -> str:
    """Fetch RSS feed as raw text using requests (for proper timeout control)."""
    resp = requests.get(
        url,
        headers={"User-Agent": USER_AGENT},
        timeout=REQUEST_TIMEOUT_SECONDS,
    )
    resp.raise_for_status()
    return resp.text


def _parse_entry(entry: object, source_def: RSSSourceDef) -> Optional[Article]:
    title = (getattr(entry, "title", None) or "").strip()
    if not title:
        return None

    link = getattr(entry, "link", "") or ""
    published_raw = (
        getattr(entry, "published", None)
        or getattr(entry, "updated", None)
        or ""
    )
    published_at = parse_date(published_raw)

    # Content: prefer summary/content, fallback to title
    raw = (
        getattr(entry, "summary", None)
        or (getattr(entry, "content", [{}])[0].get("value", "") if hasattr(entry, "content") else "")
        or ""
    )
    content = strip_html(raw) if raw and "<" in raw else clean_text(raw or title)
    if len(content) > 6_000:
        content = content[:6_000] + " [...]"

    full_text = f"{title} {content}"
    return Article(
        title=title,
        content=content,
        source=source_def.name,
        ingestion_method="rss",
        published_at=published_at,
        url=link,
        language=detect_language(full_text),
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def fetch_rss(source_key: str) -> List[Article]:
    """
    Fetch, parse, deduplicate, and persist articles from the official RSS feed
    for source_key.

    Returns list of newly saved Article objects.
    Never raises — all errors are caught, logged, and counted in health records.
    """
    if source_key not in RSS_SOURCES:
        logger.warning("[RSS] Unknown source key: %s", source_key)
        return []

    source_def = RSS_SOURCES[source_key]

    if not source_def.rss_url:
        logger.debug("[RSS][%s] No RSS URL — skipping (use Google News)", source_key)
        return []

    # Rate limiting
    elapsed = time.monotonic() - _last_fetch_ts.get(source_key, 0.0)
    if elapsed < REQUEST_DELAY_SECONDS:
        time.sleep(REQUEST_DELAY_SECONDS - elapsed)
    _last_fetch_ts[source_key] = time.monotonic()

    start = time.monotonic()
    articles: List[Article] = []
    error: Optional[str] = None
    success = False

    try:
        logger.info("[RSS][%s] Fetching: %s", source_key, source_def.rss_url)
        raw_text = _fetch_feed_text(source_def.rss_url)
        feed = feedparser.parse(raw_text)

        if feed.get("bozo") and not feed.entries:
            raise ValueError(
                f"Feed parse error: {feed.get('bozo_exception', 'unknown')}"
            )

        new_count = 0
        for entry in feed.entries:
            title = (getattr(entry, "title", None) or "").strip()
            published_raw = (
                getattr(entry, "published", None)
                or getattr(entry, "updated", None)
                or ""
            )
            h = _entry_hash(title, published_raw)
            if h in _seen_hashes:
                continue
            _seen_hashes.add(h)

            article = _parse_entry(entry, source_def)
            if article and db.save_article(article):
                articles.append(article)
                new_count += 1

        success = True
        logger.info("[RSS][%s] %d new article(s) from %d entry/entries",
                    source_key, new_count, len(feed.entries))

    except Exception as exc:
        error = str(exc)
        logger.error("[RSS][%s] Failed: %s", source_key, exc)

    duration_ms = int((time.monotonic() - start) * 1000)
    db.record_ingestion(IngestionAttempt(
        source=source_def.name,
        method="rss",
        success=success,
        articles_count=len(articles),
        error=error,
        duration_ms=duration_ms,
    ))
    db.update_health(f"{source_key}_rss", success)

    return articles


def fetch_rss_all() -> Dict[str, List[Article]]:
    """Run fetch_rss for every source that has an rss_url configured."""
    return {key: fetch_rss(key) for key in RSS_SOURCES if RSS_SOURCES[key].rss_url}
