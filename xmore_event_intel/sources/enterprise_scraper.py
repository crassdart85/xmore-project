"""Enterprise scraper."""

from __future__ import annotations

import logging

from xmore_event_intel import config
from xmore_event_intel.sources._shared import enrich_article_from_url, normalize_article, parse_rss, scrape_listing

logger = logging.getLogger(__name__)


def fetch_enterprise_news() -> list[dict]:
    source = config.ENTERPRISE_SOURCE
    items: list[dict] = []
    for rss_url in source.rss_urls:
        try:
            items.extend(parse_rss(rss_url, source.name))
        except Exception as exc:
            logger.warning("Enterprise RSS failed: %s", exc)

    if not items:
        for listing_url in source.listing_urls:
            try:
                items.extend(scrape_listing(listing_url, source.name))
            except Exception as exc:
                logger.warning("Enterprise listing scrape failed: %s", exc)

    out: list[dict] = []
    for item in items[: config.MAX_ARTICLES_PER_SOURCE]:
        out.append(normalize_article(enrich_article_from_url(item), source.name))
    return _dedupe_by_url(out)


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

