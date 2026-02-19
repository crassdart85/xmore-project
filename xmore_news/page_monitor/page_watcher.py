"""
page_monitor/page_watcher.py — Xmore News Ingestion Layer

SHA-256 page-hash monitoring for EGX, CBE, FRA, OPEC, Mubasher and other
sources that publish PDFs/news without RSS feeds.

Flow per source:
  1. Fetch page HTML (with retry)
  2. Compute SHA-256 of normalised body text
  3. Compare with stored hash — skip if unchanged
  4. Store new hash
  5. Extract PDF/document links from changed page
  6. Filter out previously known URLs
  7. Store new URLs in xmore_known_pdf_urls
  8. Return list of new URLs for downstream PDF engine

Includes CBE publications and news pages as additional monitored sources.
"""

from __future__ import annotations

import hashlib
import logging
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional

import requests
from bs4 import BeautifulSoup

import db
from config import MAX_RETRIES, REQUEST_DELAY_SECONDS, REQUEST_TIMEOUT_SECONDS, USER_AGENT
from models import IngestionAttempt
from page_monitor.link_extractor import ExtractedLink, extract_links, filter_new_links
from utils import retry

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Source registry
# ---------------------------------------------------------------------------

@dataclass
class PageSourceDef:
    source_name: str          # human-readable label (used in Article.source)
    url: str                  # page to monitor
    base_url: str             # for resolving relative hrefs
    pdf_only: bool = True     # pass to link_extractor
    extra_queries: List[str] = field(default_factory=list)  # optional GNews queries


PAGE_SOURCES: Dict[str, PageSourceDef] = {
    # ------------------------------------------------------------------
    # Central Bank of Egypt — main monetary policy page
    # ------------------------------------------------------------------
    "cbe_monetary": PageSourceDef(
        source_name="CBE",
        url="https://www.cbe.org.eg/en/monetary-policy",
        base_url="https://www.cbe.org.eg",
    ),
    # CBE publications library
    "cbe_publications": PageSourceDef(
        source_name="CBE",
        url="https://www.cbe.org.eg/en/news-publications/publications",
        base_url="https://www.cbe.org.eg",
    ),
    # CBE news & press releases
    "cbe_news": PageSourceDef(
        source_name="CBE",
        url="https://www.cbe.org.eg/en/news-publications/news",
        base_url="https://www.cbe.org.eg",
        pdf_only=False,   # news page links to HTML articles too
    ),
    # ------------------------------------------------------------------
    # Egyptian Exchange
    # ------------------------------------------------------------------
    "egx_disclosures": PageSourceDef(
        source_name="EGX",
        url="https://www.egx.com.eg/en/EGXDocuments.aspx",
        base_url="https://www.egx.com.eg",
    ),
    # ------------------------------------------------------------------
    # Financial Regulatory Authority (Egypt)
    # ------------------------------------------------------------------
    "fra": PageSourceDef(
        source_name="FRA",
        url="https://www.fra.gov.eg/en/news-and-publications/",
        base_url="https://www.fra.gov.eg",
    ),
    # ------------------------------------------------------------------
    # OPEC
    # ------------------------------------------------------------------
    "opec": PageSourceDef(
        source_name="OPEC",
        url="https://www.opec.org/opec_web/en/press_room/press_releases.htm",
        base_url="https://www.opec.org",
    ),
    # ------------------------------------------------------------------
    # Mubasher (Egyptian financial portal)
    # ------------------------------------------------------------------
    "mubasher": PageSourceDef(
        source_name="Mubasher",
        url="https://mubasher.info/news",
        base_url="https://mubasher.info",
        pdf_only=False,
    ),
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_last_fetch_ts: Dict[str, float] = {}


def _page_hash(html: str) -> str:
    """SHA-256 of normalised page text (strips markup)."""
    try:
        soup = BeautifulSoup(html, "lxml")
    except Exception:
        soup = BeautifulSoup(html, "html.parser")
    text = soup.get_text(separator=" ", strip=True)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


@retry(
    max_attempts=MAX_RETRIES,
    delay=2.0,
    backoff=2.0,
    exceptions=(requests.RequestException, OSError),
)
def _fetch_html(url: str) -> str:
    resp = requests.get(
        url,
        headers={"User-Agent": USER_AGENT},
        timeout=REQUEST_TIMEOUT_SECONDS,
    )
    resp.raise_for_status()
    return resp.text


def _rate_limit(source_key: str) -> None:
    elapsed = time.monotonic() - _last_fetch_ts.get(source_key, 0.0)
    if elapsed < REQUEST_DELAY_SECONDS:
        time.sleep(REQUEST_DELAY_SECONDS - elapsed)
    _last_fetch_ts[source_key] = time.monotonic()


# ---------------------------------------------------------------------------
# Core watcher
# ---------------------------------------------------------------------------

def watch_page(source_key: str) -> List[str]:
    """
    Check a single monitored page for changes and return new document URLs.

    Returns a (possibly empty) list of new absolute URLs.
    Never raises.
    """
    if source_key not in PAGE_SOURCES:
        logger.warning("[PageWatcher] Unknown source key: %s", source_key)
        return []

    src = PAGE_SOURCES[source_key]
    _rate_limit(source_key)

    start = time.monotonic()
    new_urls: List[str] = []
    error: Optional[str] = None
    success = False

    try:
        logger.info("[PageWatcher][%s] Fetching: %s", source_key, src.url)
        html = _fetch_html(src.url)

        new_hash = _page_hash(html)
        old_hash = db.get_page_hash(source_key)

        if old_hash == new_hash:
            logger.info("[PageWatcher][%s] No change detected.", source_key)
            success = True
            # Still record a healthy attempt
        else:
            logger.info(
                "[PageWatcher][%s] Change detected (hash %s -> %s)",
                source_key, (old_hash or "none")[:8], new_hash[:8],
            )
            db.set_page_hash(source_key, src.url, new_hash)

            # Extract links from the changed page
            links: List[ExtractedLink] = extract_links(
                html=html,
                base_url=src.base_url,
                pdf_only=src.pdf_only,
            )

            # Filter already-known URLs
            known = set(db.get_known_pdf_urls(source_key))
            new_links = filter_new_links(links, known)

            for lk in new_links:
                db.add_known_pdf_url(source_key, lk.url)
                new_urls.append(lk.url)

            logger.info(
                "[PageWatcher][%s] %d new URL(s) from %d extracted",
                source_key, len(new_urls), len(links),
            )

        success = True

    except Exception as exc:
        error = str(exc)
        logger.error("[PageWatcher][%s] Failed: %s", source_key, exc)

    duration_ms = int((time.monotonic() - start) * 1000)
    db.record_ingestion(IngestionAttempt(
        source=src.source_name,
        method="page_monitor",
        success=success,
        articles_count=len(new_urls),
        error=error,
        duration_ms=duration_ms,
    ))
    db.update_health(f"{source_key}_page", success)

    return new_urls


def watch_all_pages() -> Dict[str, List[str]]:
    """Run watch_page for every registered source. Returns {source_key: [urls]}."""
    results: Dict[str, List[str]] = {}
    for key in PAGE_SOURCES:
        results[key] = watch_page(key)
    return results
