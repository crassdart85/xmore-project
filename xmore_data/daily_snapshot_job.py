"""
Daily EGX snapshot job.

Runs one daily batch fetch for configured EGX symbols using DataManager
(provider order: EGXPY -> yfinance -> Alpha Vantage), exports per-symbol
CSV snapshots, and writes execution manifests with per-symbol source/failure.
"""

from __future__ import annotations

import argparse
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    from .config import Config
    from .data_manager import DataManager
    from .utils import get_logger
except ImportError:
    # Support direct script execution: python xmore_data/daily_snapshot_job.py ...
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from xmore_data.config import Config
    from xmore_data.data_manager import DataManager
    from xmore_data.utils import get_logger


logger = get_logger(__name__)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Daily EGX market data snapshot exporter (with provider fallback and cache)."
    )
    parser.add_argument(
        "--symbols",
        nargs="+",
        help="Optional symbols list. Defaults to Config.EGX30_SYMBOLS.",
    )
    parser.add_argument(
        "--interval",
        default="1d",
        choices=Config.SUPPORTED_INTERVALS,
        help="OHLCV interval to fetch (default: 1d).",
    )
    parser.add_argument(
        "--start",
        default=None,
        help="Optional start date/range (e.g., 2025-01-01, 90d). Defaults to DataManager behavior.",
    )
    parser.add_argument(
        "--end",
        default=None,
        help="Optional end date (YYYY-MM-DD, today, yesterday). Defaults to now.",
    )
    parser.add_argument(
        "--output-dir",
        default="data_exports/daily_egx_snapshots",
        help="Base output directory for snapshot exports.",
    )
    parser.add_argument(
        "--refresh",
        action="store_true",
        help="Force refresh from providers (bypass cache and overwrite existing snapshots).",
    )
    parser.add_argument(
        "--fail-on-error",
        action="store_true",
        help="Exit non-zero if any symbol fails.",
    )
    return parser


def run_daily_snapshot_job(args: argparse.Namespace) -> int:
    symbols = args.symbols or Config.EGX30_SYMBOLS
    run_started = datetime.now(timezone.utc)
    run_date = datetime.now().date().isoformat()
    snapshot_dir = Path(args.output_dir) / run_date
    snapshot_dir.mkdir(parents=True, exist_ok=True)

    dm = DataManager(
        use_cache=not args.refresh,
        cache_ttl_hours=Config.CACHE_EXPIRATION_HOURS,
        verbose=True,
    )

    logger.info("Daily snapshot start | symbols=%s | interval=%s", len(symbols), args.interval)
    logger.info("Provider chain available: %s", ", ".join(dm.provider_info))

    successes: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []
    skipped_existing: list[str] = []

    for symbol in symbols:
        out_file = snapshot_dir / f"{symbol}_{args.interval}_{run_date}.csv"

        # Idempotency: skip redundant work if snapshot already exists and no refresh requested.
        if out_file.exists() and not args.refresh:
            logger.info("Skipping %s (snapshot already exists): %s", symbol, out_file)
            skipped_existing.append(symbol)
            continue

        started = time.perf_counter()
        try:
            df = dm.fetch_data(
                symbol=symbol,
                interval=args.interval,
                start=args.start,
                end=args.end,
                force_refresh=args.refresh,
            )

            if df is None or df.empty:
                raise ValueError("Fetched dataframe is empty")

            df.to_csv(out_file, index=False)

            elapsed_ms = round((time.perf_counter() - started) * 1000, 1)
            source = dm.get_last_source(symbol) or "unknown"
            row = {
                "symbol": symbol,
                "rows": int(len(df)),
                "source": source,
                "latency_ms": elapsed_ms,
                "latest_date": str(df["Date"].iloc[-1]),
                "latest_close": float(df["Close"].iloc[-1]),
                "file": str(out_file),
            }
            successes.append(row)
            logger.info(
                "Snapshot saved | symbol=%s | source=%s | rows=%s | latency_ms=%s",
                symbol,
                source,
                row["rows"],
                elapsed_ms,
            )
        except Exception as exc:
            elapsed_ms = round((time.perf_counter() - started) * 1000, 1)
            error_row = {
                "symbol": symbol,
                "error": str(exc),
                "latency_ms": elapsed_ms,
            }
            failures.append(error_row)
            logger.error("Snapshot failed | symbol=%s | error=%s", symbol, exc)

    manifest = {
        "run_started_utc": run_started.replace(microsecond=0).isoformat(),
        "run_finished_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "run_date": run_date,
        "interval": args.interval,
        "start": args.start,
        "end": args.end,
        "refresh": bool(args.refresh),
        "provider_chain": dm.provider_info,
        "total_symbols": len(symbols),
        "success_count": len(successes),
        "failure_count": len(failures),
        "skipped_existing_count": len(skipped_existing),
        "skipped_existing": skipped_existing,
        "successes": successes,
        "failures": failures,
    }

    manifest_file = snapshot_dir / "snapshot_manifest.json"
    manifest_file.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    logger.info("Manifest written: %s", manifest_file)
    logger.info(
        "Daily snapshot complete | success=%s | failures=%s | skipped=%s",
        len(successes),
        len(failures),
        len(skipped_existing),
    )

    if failures and args.fail_on_error:
        return 1
    return 0


def main() -> int:
    parser = _build_parser()
    args = parser.parse_args()
    return run_daily_snapshot_job(args)


if __name__ == "__main__":
    raise SystemExit(main())
