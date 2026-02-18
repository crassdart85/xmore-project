"""EGX official disclosures scraper."""

from __future__ import annotations

import logging
from datetime import datetime
from urllib.parse import urlparse

from bs4 import BeautifulSoup

from xmore_event_intel import config
from xmore_event_intel.sources._shared import can_fetch, detect_symbols, fetch_url

logger = logging.getLogger(__name__)


def fetch_egx_disclosures() -> list[dict]:
    """Fetch Egyptian Exchange disclosures in structured format."""
    source = config.EGX_DISCLOSURES_SOURCE
    rows: list[dict] = []
    for page_url in source.listing_urls:
        if not can_fetch(page_url):
            logger.warning("EGX disclosures blocked by robots: %s", page_url)
            continue
        try:
            html = fetch_url(page_url)
            rows.extend(_parse_disclosure_page(page_url, html))
        except Exception as exc:
            logger.warning("EGX disclosures fetch failed for %s: %s", page_url, exc)
    return _dedupe_by_url(rows)


def _parse_disclosure_page(base_url: str, html: str) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    parsed_base = urlparse(base_url)
    out: list[dict] = []

    for row in soup.select("table tr"):
        cols = row.find_all(["td", "th"])
        if len(cols) < 2:
            continue

        company = cols[0].get_text(" ", strip=True)
        disclosure_type = cols[1].get_text(" ", strip=True)
        ts_text = cols[2].get_text(" ", strip=True) if len(cols) >= 3 else ""

        link_tag = row.find("a", href=True)
        if not link_tag:
            continue
        href = str(link_tag["href"]).strip()
        if href.startswith("/"):
            href = f"{parsed_base.scheme}://{parsed_base.netloc}{href}"
        if not href.startswith("http"):
            continue

        published_at = ts_text or datetime.utcnow().isoformat()
        content = f"{company} | {disclosure_type}"
        out.append(
            {
                "title": f"{company} - {disclosure_type}",
                "content": content,
                "published_at": published_at,
                "source": source_name(),
                "url": href,
                "detected_symbols": detect_symbols(content),
                "raw_html": html,
                "company": company,
                "disclosure_type": disclosure_type,
                "timestamp": published_at,
            }
        )

    for item in out:
        if not item.get("detected_symbols"):
            item["detected_symbols"] = detect_symbols(item.get("title", ""))
    return out


def source_name() -> str:
    return config.EGX_DISCLOSURES_SOURCE.name


def _dedupe_by_url(items: list[dict]) -> list[dict]:
    seen: set[str] = set()
    out: list[dict] = []
    for item in items:
        url = item.get("url", "")
        if not url or url in seen:
            continue
        seen.add(url)
        out.append(item)
    return out

