"""
router.py — Xmore Reliable News Acquisition Layer

Central orchestrator implementing the failover / redundancy logic:

  For every source:
    [1] Email ingestion (primary — most reliable, push-based)
    [2] Google News RSS (fallback — always runs in parallel)
    [3] PDF monitor    (additive — for official bodies only)

Articles from all paths are deduplicated at the storage layer (content hash).
Health records are updated after every ingestion attempt regardless of outcome.
"""

import logging
from typing import Any, Dict, List, Optional

import storage
from config import EMAIL_SOURCES, PDF_SOURCES, RSS_SOURCES
from email_ingestion.email_parser import EmailParser
from email_ingestion.gmail_client import GmailClient
from pdf_monitoring.pdf_downloader import PDFDownloader
from pdf_monitoring.pdf_parser import PDFParser
from pdf_monitoring.page_watcher import PageWatcher
from rss_ingestion.google_news_client import GoogleNewsClient
from rss_ingestion.rss_parser import RSSParser

logger = logging.getLogger(__name__)

# Mapping: logical source name → PDF source key
_PDF_SOURCE_MAP: Dict[str, str] = {
    "EGX": "EGX_disclosure",
    "CBE": "CBE_publications",
    "FRA": "FRA_decisions",
    "Ministry_Finance": "Ministry_Finance_reports",
}


class NewsRouter:
    """
    Orchestrates ingestion across all three paths with automatic failover.
    Instantiate once per run; GmailClient is lazy-initialised on first use.
    """

    def __init__(self) -> None:
        self._email_parser = EmailParser()
        self._rss_client = GoogleNewsClient()
        self._rss_parser = RSSParser()
        self._page_watcher = PageWatcher()
        self._pdf_downloader = PDFDownloader()
        self._pdf_parser = PDFParser()
        self._gmail: Optional[GmailClient] = None

    # ------------------------------------------------------------------
    # Gmail lazy-init (avoids OAuth popup when email is not needed)
    # ------------------------------------------------------------------

    def _get_gmail(self) -> Optional[GmailClient]:
        if self._gmail is not None:
            return self._gmail
        try:
            self._gmail = GmailClient()
        except FileNotFoundError as exc:
            logger.warning("Gmail credentials unavailable: %s", exc)
        except Exception as exc:
            logger.warning("Gmail client init failed: %s", exc)
        return self._gmail

    # ------------------------------------------------------------------
    # Path 1: Email ingestion
    # ------------------------------------------------------------------

    def _ingest_email(self, source_name: str) -> List[Dict[str, Any]]:
        if source_name not in EMAIL_SOURCES:
            return []

        gmail = self._get_gmail()
        if gmail is None:
            return []

        cfg = EMAIL_SOURCES[source_name]
        articles: List[Dict[str, Any]] = []
        health_key = f"{source_name}_email"

        try:
            messages = gmail.fetch_unread_by_label(cfg.label)
            saved_count = 0

            for msg in messages:
                text_body, html_body = gmail.get_body(msg)
                article = self._email_parser.parse(msg, source_name, text_body, html_body)

                if storage.save_article(article):
                    saved_count += 1
                    articles.append(article)
                    # Mark processed only after successful storage
                    gmail.mark_as_processed(msg["id"])

            storage.log_ingestion(source_name, "email", "success", saved_count)
            storage.update_source_health(health_key, True)
            logger.info("[%s] Email: %d new article(s) from %d message(s)",
                        source_name, saved_count, len(messages))

        except Exception as exc:
            logger.error("[%s] Email ingestion error: %s", source_name, exc)
            storage.log_ingestion(source_name, "email", "failure", error=str(exc))
            storage.update_source_health(health_key, False)

        return articles

    # ------------------------------------------------------------------
    # Path 2: RSS ingestion
    # ------------------------------------------------------------------

    def _ingest_rss(self, source_name: str) -> List[Dict[str, Any]]:
        if source_name not in RSS_SOURCES:
            return []

        cfg = RSS_SOURCES[source_name]
        articles: List[Dict[str, Any]] = []
        health_key = f"{source_name}_rss"

        try:
            raw_entries = self._rss_client.fetch_multi(
                cfg.queries,
                max_results_each=cfg.max_results,
            )
            parsed = self._rss_parser.parse(raw_entries, source_name)
            saved_count = 0

            for article in parsed:
                if storage.save_article(article):
                    saved_count += 1
                    articles.append(article)

            storage.log_ingestion(source_name, "rss", "success", saved_count)
            storage.update_source_health(health_key, True)
            logger.info("[%s] RSS: %d new article(s) from %d entry/entries",
                        source_name, saved_count, len(raw_entries))

        except Exception as exc:
            logger.error("[%s] RSS ingestion error: %s", source_name, exc)
            storage.log_ingestion(source_name, "rss", "failure", error=str(exc))
            storage.update_source_health(health_key, False)

        return articles

    # ------------------------------------------------------------------
    # Path 3: PDF monitor
    # ------------------------------------------------------------------

    def _ingest_pdf(self, pdf_source_key: str) -> List[Dict[str, Any]]:
        if pdf_source_key not in PDF_SOURCES:
            return []

        cfg = PDF_SOURCES[pdf_source_key]
        articles: List[Dict[str, Any]] = []
        health_key = f"{pdf_source_key}_pdf"

        try:
            new_urls = self._page_watcher.check_for_new_pdfs(
                pdf_source_key, cfg.page_url, cfg.base_url
            )
            saved_count = 0

            for url in new_urls:
                path = self._pdf_downloader.download(url)
                if path is None:
                    continue

                article = self._pdf_parser.parse(path, pdf_source_key, url)
                if article and storage.save_article(article):
                    saved_count += 1
                    articles.append(article)

            storage.log_ingestion(pdf_source_key, "pdf_monitor", "success", saved_count)
            storage.update_source_health(health_key, True)
            logger.info("[%s] PDF: %d new article(s) from %d URL(s)",
                        pdf_source_key, saved_count, len(new_urls))

        except Exception as exc:
            logger.error("[%s] PDF ingestion error: %s", pdf_source_key, exc)
            storage.log_ingestion(pdf_source_key, "pdf_monitor", "failure", error=str(exc))
            storage.update_source_health(health_key, False)

        return articles

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def get_news_for_source(self, source_name: str) -> List[Dict[str, Any]]:
        """
        Failover logic for a single named source:

          [1] Email  — always attempted if source has an email config
          [2] RSS    — always run (confirms / supplements email coverage)
          [3] PDF    — run for official regulatory / exchange bodies

        All three paths are additive: results are merged and deduplicated
        via content hash at the storage layer.

        Returns:
            List of newly saved article dicts for this run.
        """
        all_articles: List[Dict[str, Any]] = []

        # Path 1: Email (primary)
        email_articles = self._ingest_email(source_name)
        all_articles.extend(email_articles)

        # Path 2: RSS (redundancy layer — always runs)
        rss_articles = self._ingest_rss(source_name)
        all_articles.extend(rss_articles)

        # Path 3: PDF monitor (official sources only)
        if source_name in _PDF_SOURCE_MAP:
            pdf_key = _PDF_SOURCE_MAP[source_name]
            pdf_articles = self._ingest_pdf(pdf_key)
            all_articles.extend(pdf_articles)

        logger.info(
            "[%s] Total new articles this run: %d (email=%d, rss=%d)",
            source_name,
            len(all_articles),
            len(email_articles),
            len(rss_articles),
        )
        return all_articles

    def run_all(self) -> Dict[str, List[Dict[str, Any]]]:
        """
        Run ingestion for every configured source.
        Also runs standalone PDF monitors for sources that have no RSS
        equivalent (e.g., Ministry_Finance_reports).

        Returns:
            Dict mapping source_name → list of newly saved articles.
        """
        results: Dict[str, List[Dict[str, Any]]] = {}

        # All logical sources (union of email + RSS configs)
        all_sources = sorted(set(list(EMAIL_SOURCES) + list(RSS_SOURCES)))
        for source in all_sources:
            results[source] = self.get_news_for_source(source)

        # Standalone PDF sources not already handled via get_news_for_source
        handled_pdf_keys = set(_PDF_SOURCE_MAP.values())
        for pdf_key in PDF_SOURCES:
            if pdf_key not in handled_pdf_keys:
                results[pdf_key] = self._ingest_pdf(pdf_key)

        total = sum(len(v) for v in results.values())
        logger.info("run_all complete — %d new articles across %d sources",
                    total, len(results))
        return results
