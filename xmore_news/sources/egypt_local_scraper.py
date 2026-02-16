"""Egypt-local news collector for Xmore News Intelligence."""

from __future__ import annotations

import logging

from xmore_news import config
from xmore_news.sources.common import parse_article_page, parse_rss, scrape_listing_links

logger = logging.getLogger(__name__)


def fetch_egypt_news() -> list[dict]:
    """Fetch Enterprise, Daily News Egypt, Egypt Today, Mubasher, and Zawya."""
    articles: list[dict] = []

    for source in config.EGYPT_LOCAL_SOURCES:
        source_items: list[dict] = []

        for rss_url in source.rss_urls:
            try:
                source_items.extend(parse_rss(rss_url, source.name, source.region))
            except Exception as exc:
                logger.warning("RSS failed for %s (%s): %s", source.name, rss_url, exc)

        if not source_items:
            for listing_url in source.listing_urls:
                try:
                    links = scrape_listing_links(
                        listing_url,
                        selectors=(
                            "article a",
                            "h2 a",
                            "h3 a",
                            "a[href*='/business/']",
                            "a[href*='/markets/']",
                            "a[href*='/news/']",
                        ),
                        max_links=max(20, config.MAX_ARTICLES_PER_SOURCE // 2),
                    )
                    for link in links:
                        try:
                            parsed = parse_article_page(link, source.name, source.region)
                            if parsed:
                                source_items.append(parsed)
                        except Exception as exc:
                            logger.warning("Article parse failed (%s): %s", link, exc)
                except Exception as exc:
                    logger.warning("Listing scrape failed for %s (%s): %s", source.name, listing_url, exc)

        articles.extend(source_items[: config.MAX_ARTICLES_PER_SOURCE])

    deduped = _dedupe_by_url(articles)
    return deduped[: (config.MAX_ARTICLES_PER_SOURCE * max(1, len(config.EGYPT_LOCAL_SOURCES) // 2))]


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

