"""
ingest.py — Xmore News Ingestion Layer (multi-tier CLI)

Provides a CLI for the new ingestion system (RSS + Google News + page monitor + PDF).
The existing main.py continues to serve the legacy scheduler-based pipeline.

Usage (from inside xmore_news/ directory):
    python ingest.py --run-all             # all tiers
    python ingest.py --run-rss             # official RSS only
    python ingest.py --run-google          # Google News RSS only
    python ingest.py --run-pages           # page monitor + PDF only
    python ingest.py --health              # source health report
    python ingest.py --list-articles [N]   # last N articles (default 20)
    python ingest.py --stats               # database statistics
    python ingest.py -v                    # verbose / debug logging
"""

from __future__ import annotations

import argparse
import io
import logging
import sys
from datetime import datetime, timezone

# ---- UTF-8 stdout (Windows cp1252 fix) ------------------------------------
if sys.stdout and hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
if sys.stderr and hasattr(sys.stderr, "buffer"):
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")
# ---------------------------------------------------------------------------

import db
from health import HealthMonitor
from router import NewsRouter


def _setup_logging(verbose: bool = False) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(level)
    fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s", "%H:%M:%S")
    handler.setFormatter(fmt)
    root = logging.getLogger()
    root.setLevel(level)
    root.handlers.clear()
    root.addHandler(handler)


# ---------------------------------------------------------------------------
# Display helpers
# ---------------------------------------------------------------------------

def _print_summary(summary: dict) -> None:
    sep = "=" * 60
    print(f"\n{sep}")
    print("  XMORE NEWS -- INGESTION SUMMARY")
    print(f"  {datetime.now(tz=timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    print(sep)
    print(f"  Official RSS     : {summary.get('rss_articles', 0):>6} new article(s)")
    print(f"  Google News RSS  : {summary.get('google_news_articles', 0):>6} new article(s)")
    print(f"  PDF (page watch) : {summary.get('pdf_articles', 0):>6} new article(s)")
    print(f"  {'-'*50}")
    print(f"  TOTAL            : {summary.get('total_new_articles', 0):>6} new article(s)")
    print(f"  Elapsed          : {summary.get('elapsed_seconds', 0):.1f}s")
    print(f"{sep}\n")


# ---------------------------------------------------------------------------
# Sub-commands
# ---------------------------------------------------------------------------

def _cmd_run_all(router: NewsRouter) -> None:
    summary = router.run_all()
    _print_summary(summary)


def _cmd_run_rss(router: NewsRouter) -> None:
    results = router.run_rss()
    total = sum(len(v) for v in results.values())
    print(f"\nRSS ingestion complete -- {total} new article(s) from {len(results)} source(s).\n")
    for key, arts in sorted(results.items()):
        if arts:
            print(f"  {key:<25} {len(arts)} article(s)")
    print()


def _cmd_run_google(router: NewsRouter) -> None:
    results = router.run_google()
    total = sum(len(v) for v in results.values())
    print(f"\nGoogle News ingestion complete -- {total} new article(s) from {len(results)} source(s).\n")
    for key, arts in sorted(results.items()):
        if arts:
            print(f"  {key:<25} {len(arts)} article(s)")
    print()


def _cmd_run_pages(router: NewsRouter) -> None:
    counts = router.run_pages()
    total = sum(counts.values())
    print(f"\nPage monitor + PDF ingestion complete -- {total} new article(s).\n")
    for key, count in sorted(counts.items()):
        if count:
            print(f"  {key:<25} {count} article(s)")
    print()


def _cmd_health() -> None:
    monitor = HealthMonitor()
    monitor.print_report()


def _cmd_list_articles(limit: int) -> None:
    articles = db.get_recent_articles(limit)
    if not articles:
        print("\nNo articles in database yet.\n")
        return

    sep = "-" * 78
    print(f"\n{sep}")
    print(f"  Last {len(articles)} article(s)")
    print(sep)
    for art in articles:
        ts = (art.published_at or art.ingested_at or "")[:16]
        lang = f"[{art.language}]" if art.language else "[??]"
        print(f"  {ts}  {lang:<5}  [{art.source:<20}]  via {art.ingestion_method}")
        print(f"    {art.title[:72]}")
        if art.url:
            print(f"    {art.url[:78]}")
        print()
    print(sep + "\n")


def _cmd_stats() -> None:
    stats = db.get_stats()
    sep = "=" * 50
    print(f"\n{sep}")
    print("  XMORE NEWS -- DATABASE STATS")
    print(sep)
    for k, v in stats.items():
        print(f"  {k:<32}: {v}")
    print(f"{sep}\n")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        prog="ingest",
        description="Xmore News multi-tier ingestion: RSS + Google News + Page Monitor + PDF",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--run-all", action="store_true",
                        help="Run all ingestion tiers (RSS + Google News + pages/PDFs)")
    parser.add_argument("--run-rss", action="store_true",
                        help="Run official RSS feeds only")
    parser.add_argument("--run-google", action="store_true",
                        help="Run Google News RSS only")
    parser.add_argument("--run-pages", action="store_true",
                        help="Run page monitor + PDF engine only")
    parser.add_argument("--health", action="store_true",
                        help="Print source health report")
    parser.add_argument("--list-articles", metavar="N", nargs="?", const=20, type=int,
                        help="List last N articles from database (default 20)")
    parser.add_argument("--stats", action="store_true",
                        help="Print database statistics")
    parser.add_argument("-v", "--verbose", action="store_true",
                        help="Enable debug-level logging")

    args = parser.parse_args()
    _setup_logging(args.verbose)

    db.init()
    router = NewsRouter()

    if args.run_all:
        _cmd_run_all(router)
    elif args.run_rss:
        _cmd_run_rss(router)
    elif args.run_google:
        _cmd_run_google(router)
    elif args.run_pages:
        _cmd_run_pages(router)
    elif args.health:
        _cmd_health()
    elif args.list_articles is not None:
        _cmd_list_articles(args.list_articles)
    elif args.stats:
        _cmd_stats()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
