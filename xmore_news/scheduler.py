"""Scheduler and orchestration for Xmore news ingestion."""

from __future__ import annotations

import logging
from collections.abc import Sequence
from typing import Any

from xmore_news import config
from xmore_news.parser import normalize_article
from xmore_news.sentiment_preprocessor import prepare_for_sentiment
from xmore_news.sources.alarabiya_scraper import fetch_alarabiya_news
from xmore_news.sources.egypt_local_scraper import fetch_egypt_news
from xmore_news.sources.reuters_scraper import fetch_reuters_news
from xmore_news.storage import SQLiteNewsStorage, get_default_storage

logger = logging.getLogger(__name__)


def collect_and_store_once(
    *,
    db_path: str | None = None,
    translate_ar: bool = False,
    keyword_filter: Sequence[str] | None = None,
) -> dict[str, Any]:
    """
    Execute one collection cycle across all configured sources.
    """
    storage = get_default_storage(db_path=db_path)
    all_raw: list[dict] = []
    source_stats = {"reuters": 0, "alarabiya": 0, "egypt": 0}

    for key, fetcher in (
        ("reuters", fetch_reuters_news),
        ("alarabiya", fetch_alarabiya_news),
        ("egypt", fetch_egypt_news),
    ):
        try:
            items = fetcher()
            source_stats[key] = len(items)
            all_raw.extend(items)
        except Exception as exc:
            logger.exception("Source fetch failed (%s): %s", key, exc)

    normalized: list[dict] = []
    for raw in all_raw:
        try:
            article = normalize_article(raw)
            if not article.get("url_hash"):
                continue
            if storage.has_url_hash(article["url_hash"]):
                continue

            if keyword_filter and not _matches_keywords(article, keyword_filter):
                continue

            prepped = prepare_for_sentiment(article, translate_ar=translate_ar)
            # Keep persisted schema compact while preserving core sentiment-prep fields.
            article["language"] = prepped.get("language", article.get("language", "EN"))
            article["processed_flag"] = 0
            normalized.append(article)
        except Exception as exc:
            logger.warning("Normalization failed for URL=%s: %s", raw.get("url"), exc)

    db_result = storage.save_articles_to_db(normalized)
    summary = {
        "fetched": source_stats,
        "total_raw": len(all_raw),
        "normalized": len(normalized),
        "inserted": db_result["inserted"],
        "duplicates": db_result["duplicates"],
    }
    logger.info("Collection summary: %s", summary)
    return summary


def start_scheduler(
    *,
    db_path: str | None = None,
    interval_minutes: int | None = None,
    translate_ar: bool = False,
    keyword_filter: Sequence[str] | None = None,
) -> Any:
    """Start APScheduler loop for periodic ingestion."""
    try:
        from apscheduler.schedulers.background import BackgroundScheduler
        from apscheduler.triggers.interval import IntervalTrigger
    except Exception as exc:
        raise RuntimeError(
            "APScheduler is required for scheduler mode. Install with: pip install APScheduler"
        ) from exc

    interval = interval_minutes or config.SCHEDULER_INTERVAL_MINUTES
    scheduler = BackgroundScheduler(timezone="UTC")
    scheduler.add_job(
        collect_and_store_once,
        trigger=IntervalTrigger(minutes=interval),
        kwargs={"db_path": db_path, "translate_ar": translate_ar, "keyword_filter": keyword_filter},
        id="xmore_news_ingestion",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )
    scheduler.start()
    logger.info("Xmore news scheduler started (every %s minutes).", interval)
    return scheduler


def _matches_keywords(article: dict[str, Any], keywords: Sequence[str]) -> bool:
    haystack = f"{article.get('title', '')} {article.get('content', '')}".lower()
    return any(k.lower() in haystack for k in keywords if k.strip())
