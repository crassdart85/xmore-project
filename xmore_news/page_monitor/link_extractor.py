"""
page_monitor/link_extractor.py — Xmore News Ingestion Layer

Extracts PDF (and other document) links from raw HTML pages.

Heuristics used:
  - href ending with .pdf (case-insensitive)
  - href containing /pdf/, /download/, /publication/
  - <a> tags with text content matching document keywords
  - Relative URLs resolved against a configurable base URL
"""

from __future__ import annotations

import logging
import re
from typing import List, NamedTuple, Optional
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

# Patterns that suggest a link points to a PDF document
_PDF_PATH_RE = re.compile(
    r"(\.pdf$|/pdf/|/download/|/publications?/|/reports?/|/documents?/|"
    r"/files?/|/uploads?/|\.ashx\?|getfile|downloadfile)",
    re.IGNORECASE,
)

# Text inside <a> tags that suggest document links
_PDF_TEXT_RE = re.compile(
    r"\b(download|pdf|report|publication|circular|decree|decision|statement|"
    r"press.?release|white.?paper|annual|quarterly|monthly|bulletin|gazette)\b",
    re.IGNORECASE,
)

# Definitely NOT a PDF: JS, mailto, anchor-only, common non-doc extensions
_SKIP_RE = re.compile(
    r"^(javascript:|mailto:|tel:|#|data:)|"
    r"\.(js|css|png|jpe?g|gif|svg|ico|mp4|mp3|zip|rar|exe|msi)(\?|$)",
    re.IGNORECASE,
)


class ExtractedLink(NamedTuple):
    url: str            # absolute URL
    text: str           # anchor text
    is_pdf_heuristic: bool   # True if we're confident it's a PDF


def extract_links(
    html: str,
    base_url: str,
    pdf_only: bool = True,
) -> List[ExtractedLink]:
    """
    Parse HTML and return document links.

    Args:
        html      : raw HTML string
        base_url  : page URL used to resolve relative hrefs
        pdf_only  : if True, only return links that match PDF heuristics.
                    if False, return all non-trivially-skippable links.

    Returns list of ExtractedLink (deduplicated by URL).
    """
    try:
        soup = BeautifulSoup(html, "lxml")
    except Exception:
        soup = BeautifulSoup(html, "html.parser")

    seen: set[str] = set()
    results: List[ExtractedLink] = []

    for tag in soup.find_all("a", href=True):
        href: str = (tag.get("href") or "").strip()
        if not href:
            continue
        if _SKIP_RE.search(href):
            continue

        abs_url = urljoin(base_url, href)

        # Only keep http(s) links
        parsed = urlparse(abs_url)
        if parsed.scheme not in ("http", "https"):
            continue

        if abs_url in seen:
            continue
        seen.add(abs_url)

        anchor_text = tag.get_text(separator=" ", strip=True)
        is_pdf = _PDF_PATH_RE.search(abs_url) is not None
        text_match = _PDF_TEXT_RE.search(anchor_text) is not None

        if pdf_only and not (is_pdf or text_match):
            continue

        results.append(ExtractedLink(
            url=abs_url,
            text=anchor_text[:200],
            is_pdf_heuristic=is_pdf,
        ))

    logger.debug(
        "[LinkExtractor] base=%s  found=%d links (%s mode)",
        base_url, len(results), "pdf-only" if pdf_only else "all",
    )
    return results


def filter_new_links(
    links: List[ExtractedLink],
    known_urls: set[str],
) -> List[ExtractedLink]:
    """Return only links whose URLs are not in known_urls."""
    return [lk for lk in links if lk.url not in known_urls]
