"""
rss_ingestion/google_news_client.py — Xmore Reliable News Acquisition Layer

Fetches Google News RSS feeds for arbitrary search queries.
Handles:
  - URL construction for Google News RSS (English)
  - In-process duplicate suppression (title + date hash)
  - Rate limiting between successive calls
  - Graceful degradation on feedparser warnings / network errors
"""

import hashlib
import logging
import time
from datetime import datetime, timezone
from typing import Dict, List, Optional
from urllib.parse import quote_plus

import feedparser

from config import RSS_RATE_LIMIT_SECONDS

logger = logging.getLogger(__name__)

# Google News RSS endpoint template (returns Atom/RSS for a keyword search)
_GN_TEMPLATE = (
    "https://news.google.com/rss/search"
    "?q={query}&hl=en-US&gl=US&ceid=US:en"
)

# ---------------------------------------------------------------------------
# In-process deduplication
# ---------------------------------------------------------------------------
# Stores hashes across the lifetime of the process so that running multiple
# queries for the same source does not yield the same article twice.
_seen_hashes: set[str] = set()


def _entry_hash(title: str, published: str) -> str:
    return hashlib.md5(f"{title}|{published}".encode("utf-8")).hexdigest()


def reset_seen_hashes() -> None:
    """Call at the start of a scheduled run to allow re-fetching after 24 h."""
    _seen_hashes.clear()


# ---------------------------------------------------------------------------
# Rate limiter (module-level state — one limiter shared across all instances)
# ---------------------------------------------------------------------------
_last_call_ts: float = 0.0


def _wait_for_rate_limit() -> None:
    global _last_call_ts
    elapsed = time.monotonic() - _last_call_ts
    if elapsed < RSS_RATE_LIMIT_SECONDS:
        wait = RSS_RATE_LIMIT_SECONDS - elapsed
        logger.debug("RSS rate-limit: sleeping %.1f s", wait)
        time.sleep(wait)
    _last_call_ts = time.monotonic()


# ---------------------------------------------------------------------------
# Normalised entry dict schema (pre-RSSParser):
#
#   title        str
#   summary      str   (may contain inline HTML from Google News)
#   link         str
#   published    str   (RFC 2822 or raw string from feed)
#   source_tag   str   (publisher name from <source> element)
# ---------------------------------------------------------------------------

class GoogleNewsClient:
    """
    Stateless RSS client.  Each call to `fetch()` respects the global rate
    limit and deduplicates against all titles seen since process start.
    """

    def fetch(self, query: str, max_results: int = 20) -> List[Dict[str, str]]:
        """
        Fetch up to *max_results* entries for *query* from Google News RSS.
        Returns list of normalised entry dicts.  Never raises — logs errors
        and returns [] on any failure.
        """
        _wait_for_rate_limit()

        url = _GN_TEMPLATE.format(query=quote_plus(query))
        logger.info("RSS fetch: %s", query)
        logger.debug("URL: %s", url)

        try:
            feed = feedparser.parse(url)
        except Exception as exc:
            logger.error("feedparser raised on query '%s': %s", query, exc)
            return []

        # feedparser sets bozo=True on non-fatal parse issues — log but continue
        if feed.get("bozo") and feed.get("bozo_exception"):
            logger.warning(
                "RSS bozo warning for '%s': %s",
                query,
                feed["bozo_exception"],
            )

        if not feed.entries:
            logger.info("No entries returned for query: %s", query)
            return []

        results: List[Dict[str, str]] = []
        for entry in feed.entries[:max_results]:
            title: str = entry.get("title", "").strip()
            published: str = entry.get("published", "") or entry.get("updated", "")
            link: str = entry.get("link", "")
            summary: str = entry.get("summary", "")
            source_tag: str = ""
            if hasattr(entry, "source") and entry.source:
                source_tag = getattr(entry.source, "title", "")

            # Deduplicate within this process run
            h = _entry_hash(title, published)
            if h in _seen_hashes:
                logger.debug("Duplicate RSS entry skipped: %s", title[:60])
                continue
            _seen_hashes.add(h)

            results.append({
                "title": title,
                "summary": summary,
                "link": link,
                "published": published,
                "source_tag": source_tag or "Google News",
            })

        logger.info("RSS '%s' -> %d new entries", query, len(results))
        return results

    def fetch_multi(
        self,
        queries: List[str],
        max_results_each: int = 15,
    ) -> List[Dict[str, str]]:
        """
        Fetch multiple queries, respecting rate limits between each call.
        Returns the merged, deduplicated list.
        """
        combined: List[Dict[str, str]] = []
        for query in queries:
            entries = self.fetch(query, max_results=max_results_each)
            combined.extend(entries)
        return combined
