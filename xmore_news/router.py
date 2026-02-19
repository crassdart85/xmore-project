"""
router.py — Xmore News Ingestion Layer

Orchestrates all ingestion sub-systems with additive failover:

  Tier 1 — Official RSS (IMF, Fed, World Bank, Daily News Egypt)
  Tier 2 — Google News RSS (all sources, supplementary / fallback)
  Tier 3 — Page Monitor (CBE, EGX, FRA, OPEC, Mubasher) + PDF engine

All tiers run additively — articles from any tier are deduplicated at the
storage layer (xmore_articles.content_hash UNIQUE constraint in db.py).

Usage::

    from router import NewsRouter
    router = NewsRouter()
    summary = router.run_all()
"""

from __future__ import annotations

import logging
import time
from typing import Dict, List

import db
from google_news.google_news_client import (
    fetch_google_news_all,
    reset_seen_hashes as gnews_reset,
)
from models import Article
from page_monitor.page_watcher import PAGE_SOURCES, watch_all_pages
from pdf_engine.pdf_downloader import download_pdf
from pdf_engine.pdf_parser import parse_pdf
from rss.rss_client import fetch_rss_all
from rss.rss_registry import RSS_SOURCES

logger = logging.getLogger(__name__)


class NewsRouter:
    """
    High-level orchestrator.

    run_all()        — run all tiers
    run_rss()        — official RSS only
    run_google()     — Google News only
    run_pages()      — page monitor + PDF engine
    """

    # ------------------------------------------------------------------
    # Tier 1: Official RSS
    # ------------------------------------------------------------------

    def run_rss(self) -> Dict[str, List[Article]]:
        logger.info("[Router] === Tier 1: Official RSS ===")
        results = fetch_rss_all()
        total = sum(len(v) for v in results.values())
        logger.info("[Router] RSS done — %d new article(s) across %d source(s)", total, len(results))
        return results

    # ------------------------------------------------------------------
    # Tier 2: Google News RSS
    # ------------------------------------------------------------------

    def run_google(self) -> Dict[str, List[Article]]:
        logger.info("[Router] === Tier 2: Google News RSS ===")
        gnews_reset()
        results = fetch_google_news_all()
        total = sum(len(v) for v in results.values())
        logger.info("[Router] Google News done — %d new article(s) across %d source(s)", total, len(results))
        return results

    # ------------------------------------------------------------------
    # Tier 3: Page Monitor + PDF Engine
    # ------------------------------------------------------------------

    def run_pages(self) -> Dict[str, int]:
        """
        Watch all monitored pages, download new PDFs, and persist extracted text.
        Returns {source_key: count_of_new_pdf_articles}.
        """
        logger.info("[Router] === Tier 3: Page Monitor + PDF Engine ===")
        page_results = watch_all_pages()

        pdf_counts: Dict[str, int] = {}
        for source_key, urls in page_results.items():
            if not urls:
                pdf_counts[source_key] = 0
                continue

            src_def = PAGE_SOURCES[source_key]
            saved = 0

            for url in urls:
                local_path = download_pdf(url)
                if local_path is None:
                    continue

                parsed = parse_pdf(
                    path=local_path,
                    source_name=src_def.source_name,
                    url=url,
                )
                if parsed is None:
                    continue

                article = Article(
                    title=parsed["title"],
                    content=parsed["content"],
                    source=parsed["source"],
                    ingestion_method="pdf",
                    url=parsed["url"],
                    language=parsed["language"],
                )
                if db.save_article(article):
                    saved += 1
                    logger.info(
                        "[Router][PDF][%s] Saved: %s", source_key, article.title[:60]
                    )

            pdf_counts[source_key] = saved

        total = sum(pdf_counts.values())
        logger.info("[Router] Pages done — %d new PDF article(s)", total)
        return pdf_counts

    # ------------------------------------------------------------------
    # Run all tiers
    # ------------------------------------------------------------------

    def run_all(self) -> dict:
        """
        Run Tier 1 → Tier 2 → Tier 3 in sequence.
        Returns a summary dict with counts per tier.
        """
        start = time.monotonic()
        db.init()

        # Tier 1
        rss_results = self.run_rss()
        rss_total = sum(len(v) for v in rss_results.values())

        # Tier 2
        gnews_results = self.run_google()
        gnews_total = sum(len(v) for v in gnews_results.values())

        # Tier 3
        page_results = self.run_pages()
        pdf_total = sum(page_results.values())

        elapsed = time.monotonic() - start
        grand_total = rss_total + gnews_total + pdf_total

        summary = {
            "rss_articles": rss_total,
            "google_news_articles": gnews_total,
            "pdf_articles": pdf_total,
            "total_new_articles": grand_total,
            "elapsed_seconds": round(elapsed, 1),
        }

        logger.info(
            "[Router] run_all complete in %.1fs — RSS=%d  GNews=%d  PDF=%d  TOTAL=%d",
            elapsed, rss_total, gnews_total, pdf_total, grand_total,
        )
        return summary
