#!/usr/bin/env python3
"""
main.py — Xmore Reliable News Acquisition Layer
CLI Entrypoint

Usage examples:
  python main.py --source CBE
  python main.py --source EGX
  python main.py --source IMF
  python main.py --run-all
  python main.py --health-check
  python main.py --list-articles --source EGX --limit 20
  python main.py --list-articles --language ar
  python main.py --run-all --verbose
"""

import argparse
import json
import logging
import sys
from pathlib import Path
from typing import Optional

import storage
from config import EMAIL_SOURCES, PDF_SOURCES, RSS_SOURCES
from health_monitor import HealthMonitor
from router import NewsRouter

# ---------------------------------------------------------------------------
# Logging setup — goes to stdout AND xmore_news.log
# ---------------------------------------------------------------------------
LOG_FILE = Path(__file__).parent / "xmore_news.log"


def _setup_logging(verbose: bool = False) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    fmt = "%(asctime)s [%(levelname)-8s] %(name)s - %(message)s"
    datefmt = "%Y-%m-%d %H:%M:%S"

    # Force UTF-8 on Windows (default console is cp1252 which breaks Arabic/arrows)
    import io
    utf8_stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

    handlers: list[logging.Handler] = [
        logging.StreamHandler(utf8_stdout),
        logging.FileHandler(str(LOG_FILE), encoding="utf-8"),
    ]
    for h in handlers:
        h.setFormatter(logging.Formatter(fmt, datefmt=datefmt))

    root = logging.getLogger()
    root.setLevel(level)
    for h in handlers:
        root.addHandler(h)

    # Quieten noisy third-party loggers unless in verbose mode
    if not verbose:
        for noisy in ("urllib3", "googleapiclient", "google.auth", "feedparser"):
            logging.getLogger(noisy).setLevel(logging.WARNING)


logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------

def cmd_fetch_source(source: str) -> int:
    """Fetch news for a single named source."""
    valid = sorted(set(list(EMAIL_SOURCES) + list(RSS_SOURCES) + list(PDF_SOURCES)))
    if source not in valid:
        print(f"Unknown source '{source}'.")
        print(f"Valid sources: {', '.join(valid)}")
        return 1

    router = NewsRouter()
    logger.info("=== Fetching source: %s ===", source)
    articles = router.get_news_for_source(source)

    print(f"\n[{source}] {len(articles)} new article(s) ingested this run.")
    _print_article_summary(articles)
    return 0


def cmd_run_all() -> int:
    """Run all configured sources."""
    router = NewsRouter()
    logger.info("=== Running ALL sources ===")
    results = router.run_all()

    total = sum(len(v) for v in results.values())
    print(f"\nRun complete. {total} total new article(s) across {len(results)} source(s).\n")

    for src, arts in sorted(results.items()):
        status = f"{len(arts)} new" if arts else "0 new"
        print(f"  {src:<30} {status}")
    return 0


def cmd_health_check() -> int:
    """Print source health table and return exit-code 1 if any issues."""
    monitor = HealthMonitor()
    monitor.print_report()
    warnings = monitor.run_check()
    summary = monitor.summary()

    if summary.get("offline", 0) > 0:
        print(f"CRITICAL: {summary['offline']} source(s) offline.")
        return 2
    if summary.get("degraded", 0) > 0:
        print(f"WARNING: {summary['degraded']} source(s) degraded.")
        return 1
    return 0


def cmd_list_articles(
    source: Optional[str],
    limit: int,
    language: Optional[str],
    json_output: bool,
) -> int:
    """Display stored articles."""
    articles = storage.get_articles(source=source, limit=limit, language=language)

    if not articles:
        qualifier = f" for source '{source}'" if source else ""
        print(f"No articles found{qualifier}.")
        return 0

    if json_output:
        print(json.dumps(articles, indent=2, ensure_ascii=False))
        return 0

    qualifier = f" [{source}]" if source else ""
    print(f"\nShowing {len(articles)} article(s){qualifier}:\n")
    print("-" * 80)
    for a in articles:
        syms = json.loads(a["detected_symbols"]) if isinstance(a["detected_symbols"], str) else a["detected_symbols"]
        sym_str = ", ".join(syms) if syms else "—"
        pub = (a.get("published_at") or "")[:16]
        print(
            f"[{a['source']:<20}] [{a['ingestion_method']:<11}] "
            f"[{a['language']}] {pub}"
        )
        print(f"  {a['title'][:90]}")
        if sym_str != "—":
            print(f"  Symbols: {sym_str}")
        print()
    return 0


def cmd_list_sources() -> int:
    """Show all configured sources."""
    print("\nConfigured sources:\n")
    print(f"{'Source':<25} {'Email':<8} {'RSS':<8} {'PDF':<8} Description")
    print("-" * 75)
    all_sources = sorted(set(list(EMAIL_SOURCES) + list(RSS_SOURCES)))
    for src in all_sources:
        has_email = "yes" if src in EMAIL_SOURCES else "no"
        has_rss = "yes" if src in RSS_SOURCES else "no"
        pdf_key = {
            "EGX": "EGX_disclosure",
            "CBE": "CBE_publications",
            "FRA": "FRA_decisions",
            "Ministry_Finance": "Ministry_Finance_reports",
        }.get(src, "")
        has_pdf = "yes" if pdf_key else "no"
        desc = (
            EMAIL_SOURCES.get(src, RSS_SOURCES.get(src, None))
        )
        desc_text = getattr(desc, "description", "") if desc else ""
        print(f"{src:<25} {has_email:<8} {has_rss:<8} {has_pdf:<8} {desc_text}")

    print("\nStandalone PDF sources:")
    for k, cfg in PDF_SOURCES.items():
        print(f"  {k:<30} {cfg.description}")
    return 0


# ---------------------------------------------------------------------------
# Article summary helper
# ---------------------------------------------------------------------------

def _print_article_summary(articles: list) -> None:
    if not articles:
        return
    preview = articles[:5]
    print()
    for a in preview:
        method = a.get("ingestion_method", "?").upper()
        print(f"  [{method:^12}] {a['title'][:75]}")
    if len(articles) > 5:
        print(f"  ... and {len(articles) - 5} more")


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="xmore-news",
        description="Xmore Reliable News Acquisition Layer — EGX Alpha Engine",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py --source CBE             # Fetch CBE news (email + RSS + PDF)
  python main.py --source EGX             # Fetch EGX disclosures
  python main.py --run-all                # Run every configured source
  python main.py --health-check           # Print health dashboard
  python main.py --list-articles --filter-source EGX --limit 10
  python main.py --list-articles --language ar --json
  python main.py --list-sources           # Show available sources
        """,
    )
    parser.add_argument(
        "--filter-source",
        metavar="NAME",
        dest="filter_source",
        help="Filter articles by source name (used with --list-articles)",
    )

    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument(
        "--source",
        metavar="NAME",
        help="Ingest news for this source (CBE, EGX, IMF, Enterprise, FRA, …)",
    )
    mode.add_argument(
        "--run-all",
        action="store_true",
        help="Run all configured sources",
    )
    mode.add_argument(
        "--health-check",
        action="store_true",
        help="Print source health report (exit 1 = degraded, 2 = offline)",
    )
    mode.add_argument(
        "--list-articles",
        action="store_true",
        help="List articles stored in the database",
    )
    mode.add_argument(
        "--list-sources",
        action="store_true",
        help="Show all configured ingestion sources",
    )

    parser.add_argument(
        "--limit",
        type=int,
        default=20,
        metavar="N",
        help="Max articles to display with --list-articles (default: 20)",
    )
    parser.add_argument(
        "--language",
        choices=["en", "ar"],
        help="Filter articles by language with --list-articles",
    )
    parser.add_argument(
        "--json",
        dest="json_output",
        action="store_true",
        help="Output articles as JSON (with --list-articles)",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable DEBUG-level logging",
    )
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    _setup_logging(verbose=args.verbose)
    storage.initialize_db()

    logger.debug("Args: %s", args)

    if args.run_all:
        sys.exit(cmd_run_all())
    elif args.source:
        sys.exit(cmd_fetch_source(args.source))
    elif args.health_check:
        sys.exit(cmd_health_check())
    elif args.list_articles:
        sys.exit(cmd_list_articles(
            source=getattr(args, "filter_source", None),
            limit=args.limit,
            language=args.language,
            json_output=args.json_output,
        ))
    elif args.list_sources:
        sys.exit(cmd_list_sources())


if __name__ == "__main__":
    main()
