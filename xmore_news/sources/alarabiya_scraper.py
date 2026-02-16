"""Al Arabiya Business scraper (RSS-first with static fallback)."""

from __future__ import annotations

import logging

from xmore_news import config
from xmore_news.sources.common import parse_article_page, parse_rss, scrape_listing_links

logger = logging.getLogger(__name__)


def fetch_alarabiya_news() -> list[dict]:
    """Fetch Al Arabiya business/markets content."""
    collected: list[dict] = []

    for rss_url in config.ALARABIYA_SOURCE.rss_urls:
        try:
            collected.extend(parse_rss(rss_url, config.ALARABIYA_SOURCE.name, config.ALARABIYA_SOURCE.region))
        except Exception as exc:
            logger.warning("Al Arabiya RSS failed for %s: %s", rss_url, exc)

    if not collected:
        for listing in config.ALARABIYA_SOURCE.listing_urls:
            try:
                links = scrape_listing_links(
                    listing,
                    selectors=(
                        "a[href*='/business/']",
                        "a[href*='/aswaq/']",
                        "h2 a",
                        "h3 a",
                    ),
                    max_links=config.MAX_ARTICLES_PER_SOURCE,
                )
                for link in links:
                    try:
                        article = parse_article_page(link, config.ALARABIYA_SOURCE.name, config.ALARABIYA_SOURCE.region)
                        if article:
                            collected.append(article)
                    except Exception as exc:
                        logger.warning("Al Arabiya article parse failed: %s (%s)", link, exc)
            except Exception as exc:
                logger.warning("Al Arabiya listing scrape failed for %s: %s", listing, exc)

    deduped = _dedupe_by_url(collected)
    return deduped[: config.MAX_ARTICLES_PER_SOURCE]


def _dedupe_by_url(items: list[dict]) -> list[dict]:
    seen: set[str] = set()
    out: list[dict] = []
    for item in items:
        url = str(item.get("url", "")).strip()
        if not url or url in seen:
            continue
        seen.add(url)
        out.append(item)
    return out

