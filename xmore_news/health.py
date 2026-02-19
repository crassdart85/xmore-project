"""
health.py — Xmore News Ingestion Layer
Read-only health reporter over the xmore_source_health table.
"""

import logging
from datetime import datetime, timezone
from typing import Dict, List

import db
from models import SourceHealth

logger = logging.getLogger(__name__)

_ICONS = {"active": "OK ", "degraded": "!! ", "offline": "XX "}


class HealthMonitor:
    """
    Evaluates source health records and surfaces actionable warnings.
    Read-only — never modifies state.
    """

    def get_all(self) -> List[SourceHealth]:
        return db.get_all_health()

    def check(self) -> List[Dict[str, str]]:
        """Return structured warning dicts for degraded / offline sources."""
        records = self.get_all()
        now = datetime.now(tz=timezone.utc)
        warnings: List[Dict[str, str]] = []

        for rec in records:
            if rec.status == "offline":
                msg = f"[OFFLINE]  {rec.source_name} — last success: {rec.last_success or 'never'}"
                logger.error(msg)
                warnings.append({"source": rec.source_name, "status": "offline", "message": msg})

            elif rec.status == "degraded":
                msg = (
                    f"[DEGRADED] {rec.source_name} — "
                    f"{rec.consecutive_failures} consecutive failures"
                )
                logger.warning(msg)
                warnings.append({"source": rec.source_name, "status": "degraded", "message": msg})

            else:
                # Active — soft stale check (18h = 75% of offline threshold)
                if rec.last_success:
                    try:
                        last = datetime.fromisoformat(rec.last_success)
                        if last.tzinfo is None:
                            last = last.replace(tzinfo=timezone.utc)
                        hours = (now - last).total_seconds() / 3600
                        if hours >= 18:
                            msg = f"[STALE]    {rec.source_name} — no success in {hours:.1f}h"
                            logger.warning(msg)
                            warnings.append({
                                "source": rec.source_name,
                                "status": "stale",
                                "message": msg,
                            })
                    except ValueError:
                        pass

        return warnings

    def print_report(self) -> None:
        records = self.get_all()
        now = datetime.now(tz=timezone.utc)

        if not records:
            print("\nNo health data yet. Run an ingestion first.\n")
            return

        sep = "=" * 78
        print(f"\n{sep}")
        print(f"{'XMORE NEWS — SOURCE HEALTH REPORT':^78}")
        print(f"{'Generated: ' + now.strftime('%Y-%m-%d %H:%M UTC'):^78}")
        print(sep)
        print(
            f"{'Source':<30} {'Status':<13} {'Rate':>6}  "
            f"{'OK':>6} {'Fail':>6}  {'Last Success'}"
        )
        print("-" * 78)

        for rec in records:
            icon = _ICONS.get(rec.status, "?  ")
            rate = f"{rec.success_rate * 100:.0f}%"
            last = (rec.last_success or "never")[:16]
            print(
                f"{rec.source_name:<30} {icon}{rec.status:<10} "
                f"{rate:>6}  {rec.success_count:>6} {rec.failure_count:>6}  {last}"
            )

        print(sep)
        warnings = self.check()
        if warnings:
            print(f"\n  {len(warnings)} warning(s):")
            for w in warnings:
                print(f"    {w['message']}")
        else:
            print("\n  All sources healthy.")
        print()

    def summary(self) -> Dict[str, int]:
        counts: Dict[str, int] = {"active": 0, "degraded": 0, "offline": 0}
        for rec in self.get_all():
            counts[rec.status] = counts.get(rec.status, 0) + 1
        return counts
