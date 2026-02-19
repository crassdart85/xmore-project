"""
pdf_monitoring/page_watcher.py — Xmore Reliable News Acquisition Layer

Monitors official government / exchange pages for new PDF links.
Strategy:
  1. Fetch page HTML
  2. Compute SHA-256 hash of the raw HTML
  3. Compare with stored hash from previous run
  4. If changed → extract all PDF hrefs → return only *new* ones
     (those not seen in previous runs, tracked via stored URL list)
  5. Update stored hash + known URL list

This approach avoids scraping deep page structure — only reacts to link-level
changes, which is both robust and resilient to layout updates.
"""

import hashlib
import logging
import re
from typing import List, Optional
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

import storage
from config import HTTP_TIMEOUT

logger = logging.getLogger(__name__)

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/121.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9,ar;q=0.8",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _is_pdf_url(href: str) -> bool:
    """Heuristic: ends with .pdf OR contains 'pdf' in the path segment."""
    lower = href.lower()
    parsed = urlparse(lower)
    return parsed.path.endswith(".pdf") or "pdf" in parsed.path


def _extract_pdf_links(html: str, base_url: str) -> List[str]:
    """
    Return absolute URLs of all PDF-like hrefs found on the page.
    Filters to http/https only; deduplicates.
    """
    soup = BeautifulSoup(html, "lxml")
    found: set[str] = set()

    for tag in soup.find_all("a", href=True):
        href: str = tag["href"].strip()
        if not href or href.startswith("#") or href.startswith("javascript:"):
            continue

        full = urljoin(base_url, href)
        parsed = urlparse(full)

        if parsed.scheme not in ("http", "https"):
            continue
        if _is_pdf_url(full):
            found.add(full)

    return sorted(found)


# ---------------------------------------------------------------------------
# Public watcher
# ---------------------------------------------------------------------------

class PageWatcher:
    """
    Detects new PDFs on official pages by tracking HTML hash changes
    and maintaining a set of already-seen PDF URLs per source.
    """

    def __init__(self, timeout: int = HTTP_TIMEOUT) -> None:
        self.session = requests.Session()
        self.session.headers.update(_HEADERS)
        self.timeout = timeout

    def _fetch_html(self, url: str) -> Optional[str]:
        try:
            resp = self.session.get(url, timeout=self.timeout)
            resp.raise_for_status()
            return resp.text
        except requests.exceptions.Timeout:
            logger.error("Timeout fetching: %s", url)
        except requests.exceptions.HTTPError as exc:
            logger.error("HTTP %s fetching: %s", exc.response.status_code, url)
        except Exception as exc:
            logger.error("Error fetching %s: %s", url, exc)
        return None

    def check_for_new_pdfs(
        self,
        source_name: str,
        page_url: str,
        base_url: str,
    ) -> List[str]:
        """
        Fetch *page_url*, detect change, extract new PDF URLs.

        Returns:
            List of new (not previously seen) absolute PDF URLs.
            Empty list if no change or no new PDFs.
        """
        html = self._fetch_html(page_url)
        if html is None:
            logger.warning("[%s] Page fetch failed — skipping PDF check", source_name)
            return []

        new_hash = _sha256(html)
        old_hash = storage.get_page_hash(source_name)
        known_urls = storage.get_known_pdf_urls(source_name)

        # Always update the hash so we don't re-alert on the same change
        all_pdf_urls = _extract_pdf_links(html, base_url)

        if new_hash == old_hash and old_hash is not None:
            logger.info("[%s] Page unchanged — no new PDFs", source_name)
            # Still check for any URLs missed on first pass
            new_urls = [u for u in all_pdf_urls if u not in known_urls]
            if new_urls:
                logger.info("[%s] Found %d previously-unseen PDF(s) on unchanged page",
                            source_name, len(new_urls))
                storage.set_page_state(source_name, new_hash, known_urls + new_urls)
            return new_urls

        logger.info("[%s] Page changed — scanning for new PDFs", source_name)
        logger.debug("[%s] Found %d total PDF link(s)", source_name, len(all_pdf_urls))

        new_urls = [u for u in all_pdf_urls if u not in known_urls]
        updated_known = list(set(known_urls + all_pdf_urls))
        storage.set_page_state(source_name, new_hash, updated_known)

        logger.info("[%s] %d new PDF URL(s) detected", source_name, len(new_urls))
        return new_urls
