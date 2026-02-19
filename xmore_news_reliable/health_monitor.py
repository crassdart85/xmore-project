"""
health_monitor.py — Xmore Reliable News Acquisition Layer
Evaluates source health records and surfaces actionable warnings.
Designed to run once daily (or on-demand via CLI).
"""

import logging
from datetime import datetime, timezone
from typing import Dict, List

import storage
from config import HEALTH_DEGRADED_THRESHOLD, HEALTH_OFFLINE_HOURS

logger = logging.getLogger(__name__)

STATUS_ICONS: Dict[str, str] = {
    "active": "OK ",
    "degraded": "!! ",
    "offline": "XX ",
}


class HealthMonitor:
    """
    Reads source_health records from the DB and generates structured warnings.
    Does NOT modify any state — purely a read-and-report component.
    """

    def run_check(self) -> List[Dict[str, str]]:
        """
        Evaluate all tracked sources and return a list of warning dicts.
        Each warning has keys: source, status, message.
        """
        records = storage.get_source_health()
        now = datetime.now(tz=timezone.utc)
        warnings: List[Dict[str, str]] = []

        for rec in records:
            source = rec["source_name"]
            status = rec["status"]
            consecutive = rec["consecutive_failures"]
            last_success_raw = rec["last_success"]

            if status == "offline":
                msg = (
                    f"[OFFLINE] {source} — "
                    f"last success: {last_success_raw or 'never'}"
                )
                logger.error(msg)
                warnings.append({"source": source, "status": "offline", "message": msg})

            elif status == "degraded":
                msg = (
                    f"[DEGRADED] {source} — "
                    f"{consecutive} consecutive failures"
                )
                logger.warning(msg)
                warnings.append({"source": source, "status": "degraded", "message": msg})

            else:
                # Active — but check staleness independently as a soft warning
                if last_success_raw:
                    try:
                        last_dt = datetime.fromisoformat(last_success_raw)
                        if last_dt.tzinfo is None:
                            last_dt = last_dt.replace(tzinfo=timezone.utc)
                        hours_since = (now - last_dt).total_seconds() / 3600
                        if hours_since >= HEALTH_OFFLINE_HOURS * 0.75:
                            msg = (
                                f"[STALE] {source} — "
                                f"no success in {hours_since:.1f}h "
                                f"(threshold: {HEALTH_OFFLINE_HOURS}h)"
                            )
                            logger.warning(msg)
                            warnings.append({
                                "source": source,
                                "status": "stale",
                                "message": msg,
                            })
                    except ValueError:
                        pass

        return warnings

    def print_report(self) -> None:
        """Print a human-readable health table to stdout."""
        records = storage.get_source_health()
        now = datetime.now(tz=timezone.utc)

        if not records:
            print("\nNo source health data yet. Run an ingestion first.\n")
            return

        line = "=" * 76
        print(f"\n{line}")
        print(f"{'XMORE SOURCE HEALTH REPORT':^76}")
        print(f"{'Generated: ' + now.strftime('%Y-%m-%d %H:%M UTC'):^76}")
        print(line)
        print(
            f"{'Source':<30} {'Status':<12} {'Rate':>6}  "
            f"{'OK':>5} {'Fail':>5}  {'Last Success'}"
        )
        print("-" * 76)

        for rec in records:
            icon = STATUS_ICONS.get(rec["status"], "?  ")
            rate = f"{rec['success_rate'] * 100:.0f}%"
            last = (rec["last_success"] or "never")[:16]
            print(
                f"{rec['source_name']:<30} "
                f"{icon}{rec['status']:<9} "
                f"{rate:>6}  "
                f"{rec['success_count']:>5} "
                f"{rec['failure_count']:>5}  "
                f"{last}"
            )

        print(line)
        warnings = self.run_check()
        if warnings:
            print(f"\n  {len(warnings)} warning(s):")
            for w in warnings:
                print(f"    {w['message']}")
        else:
            print("\n  All sources within healthy thresholds.")
        print()

    def summary(self) -> Dict[str, int]:
        """Return counts of active / degraded / offline sources."""
        records = storage.get_source_health()
        counts: Dict[str, int] = {"active": 0, "degraded": 0, "offline": 0}
        for rec in records:
            s = rec["status"]
            counts[s] = counts.get(s, 0) + 1
        return counts
