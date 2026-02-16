"""Reuters scraper (RSS-first with static fallback)."""

from __future__ import annotations

import logging

from xmore_news import config
from xmore_news.sources.common import parse_article_page, parse_rss, scrape_listing_links

logger = logging.getLogger(__name__)


def fetch_reuters_news() -> list[dict]:
    """Fetch Reuters Business/Markets content."""
    collected: list[dict] = []

    for rss_url in config.REUTERS_SOURCE.rss_urls:
        try:
            collected.extend(parse_rss(rss_url, config.REUTERS_SOURCE.name, config.REUTERS_SOURCE.region))
        except Exception as exc:
            logger.warning("Reuters RSS failed for %s: %s", rss_url, exc)

    # Fallback: scrape listing links and parse article pages.
    if not collected:
        for listing in config.REUTERS_SOURCE.listing_urls:
            try:
                links = scrape_listing_links(
                    listing,
                    selectors=(
                        "a[data-testid='Heading']",
                        "a[href*='/world/']",
                        "a[href*='/business/']",
                        "a[href*='/markets/']",
                    ),
                    max_links=config.MAX_ARTICLES_PER_SOURCE,
                )
                for link in links:
                    try:
                        article = parse_article_page(link, config.REUTERS_SOURCE.name, config.REUTERS_SOURCE.region)
                        if article:
                            collected.append(article)
                    except Exception as exc:
                        logger.warning("Reuters article parse failed: %s (%s)", link, exc)
            except Exception as exc:
                logger.warning("Reuters listing scrape failed for %s: %s", listing, exc)

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

