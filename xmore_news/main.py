"""CLI entrypoint for Xmore News Intelligence ingestion."""

from __future__ import annotations

import argparse
import logging
import signal
import sys
import time
from collections.abc import Sequence

from xmore_news import config
from xmore_news.scheduler import collect_and_store_once, start_scheduler
from xmore_news.storage import SQLiteNewsStorage


def run_once(
    *,
    db_path: str | None = None,
    translate_ar: bool = False,
    keyword_filter: Sequence[str] | None = None,
) -> dict:
    """Public one-shot runner."""
    return collect_and_store_once(
        db_path=db_path or config.DB_PATH,
        translate_ar=translate_ar,
        keyword_filter=keyword_filter,
    )


def parse_args(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Xmore News Intelligence Pipeline")
    parser.add_argument("--db-path", default=config.DB_PATH, help="SQLite file path for news storage")
    parser.add_argument("--run-once", action="store_true", help="Run one ingestion cycle then exit")
    parser.add_argument(
        "--interval-minutes",
        type=int,
        default=config.SCHEDULER_INTERVAL_MINUTES,
        help="Scheduler interval in minutes (default: 30)",
    )
    parser.add_argument("--translate-ar", action="store_true", help="Translate Arabic text to English before sentiment")
    parser.add_argument(
        "--keywords",
        default="",
        help="Optional comma-separated keyword filter (e.g. inflation,interest rates,central bank)",
    )
    parser.add_argument("--log-level", default="INFO", help="Logging level (DEBUG, INFO, WARNING, ERROR)")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    logging.basicConfig(
        level=getattr(logging, str(args.log_level).upper(), logging.INFO),
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    )

    # Ensure schema exists at startup.
    SQLiteNewsStorage(args.db_path)

    keywords = [s.strip() for s in args.keywords.split(",") if s.strip()]

    if args.run_once:
        summary = run_once(db_path=args.db_path, translate_ar=args.translate_ar, keyword_filter=keywords or None)
        logging.getLogger(__name__).info("Run-once finished: %s", summary)
        return 0

    scheduler = start_scheduler(
        db_path=args.db_path,
        interval_minutes=args.interval_minutes,
        translate_ar=args.translate_ar,
        keyword_filter=keywords or None,
    )
    run_once(db_path=args.db_path, translate_ar=args.translate_ar, keyword_filter=keywords or None)

    stop = {"value": False}

    def _shutdown_handler(*_: object) -> None:
        stop["value"] = True

    signal.signal(signal.SIGINT, _shutdown_handler)
    signal.signal(signal.SIGTERM, _shutdown_handler)

    while not stop["value"]:
        time.sleep(0.5)

    scheduler.shutdown(wait=False)
    logging.getLogger(__name__).info("Scheduler stopped gracefully.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

