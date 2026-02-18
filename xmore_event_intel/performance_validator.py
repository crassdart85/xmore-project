"""Historical sentiment-performance validation and adaptive weighting."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from statistics import mean


def compute_forward_return(price_at_publish: float | None, forward_price: float | None) -> float | None:
    if price_at_publish in (None, 0) or forward_price is None:
        return None
    return (forward_price - price_at_publish) / price_at_publish


def compute_correlation(xs: list[float], ys: list[float]) -> float | None:
    if len(xs) < 3 or len(xs) != len(ys):
        return None
    x_bar = mean(xs)
    y_bar = mean(ys)
    num = sum((x - x_bar) * (y - y_bar) for x, y in zip(xs, ys))
    den_x = sum((x - x_bar) ** 2 for x in xs) ** 0.5
    den_y = sum((y - y_bar) ** 2 for y in ys) ** 0.5
    if den_x == 0 or den_y == 0:
        return None
    return num / (den_x * den_y)


def directional_hit(sentiment_score: float, realized_return: float | None) -> int | None:
    if realized_return is None:
        return None
    if sentiment_score == 0:
        return 1 if abs(realized_return) < 1e-6 else 0
    return 1 if sentiment_score * realized_return > 0 else 0


@dataclass
class EventValidationMetrics:
    rolling_accuracy_30: float | None
    corr_1d: float | None
    corr_3d: float | None
    corr_5d: float | None
    overall_win_rate: float | None
    win_rate_by_event_type: dict[str, float]
    updated_event_weights: dict[str, float]


def evaluate_historical_performance(
    records: list[dict],
    *,
    existing_weights: dict[str, float] | None = None,
) -> EventValidationMetrics:
    """
    records fields:
      event_type, sentiment_score, return_1d, return_3d, return_5d
    """
    existing = existing_weights or {}
    recent_30 = records[:30]

    rolling_hits = [directional_hit(r["sentiment_score"], r.get("return_1d")) for r in recent_30]
    rolling_hits = [h for h in rolling_hits if h is not None]
    rolling_accuracy_30 = (sum(rolling_hits) / len(rolling_hits)) if rolling_hits else None

    corr_1d = _correlation_for_horizon(records, "return_1d")
    corr_3d = _correlation_for_horizon(records, "return_3d")
    corr_5d = _correlation_for_horizon(records, "return_5d")

    all_hits = [directional_hit(r["sentiment_score"], r.get("return_1d")) for r in records]
    all_hits = [h for h in all_hits if h is not None]
    overall_win_rate = (sum(all_hits) / len(all_hits)) if all_hits else None

    grouped_hits: dict[str, list[int]] = defaultdict(list)
    for r in records:
        h = directional_hit(r["sentiment_score"], r.get("return_1d"))
        if h is None:
            continue
        grouped_hits[str(r.get("event_type", "unknown"))].append(h)

    win_rate_by_event_type: dict[str, float] = {}
    for event_type, hits in grouped_hits.items():
        if not hits:
            continue
        win_rate_by_event_type[event_type] = sum(hits) / len(hits)

    updated_weights = _adapt_event_weights(existing, win_rate_by_event_type)
    return EventValidationMetrics(
        rolling_accuracy_30=rolling_accuracy_30,
        corr_1d=corr_1d,
        corr_3d=corr_3d,
        corr_5d=corr_5d,
        overall_win_rate=overall_win_rate,
        win_rate_by_event_type=win_rate_by_event_type,
        updated_event_weights=updated_weights,
    )


def _correlation_for_horizon(records: list[dict], col: str) -> float | None:
    xs: list[float] = []
    ys: list[float] = []
    for r in records:
        ret = r.get(col)
        if ret is None:
            continue
        xs.append(float(r.get("sentiment_score", 0.0)))
        ys.append(float(ret))
    return compute_correlation(xs, ys)


def _adapt_event_weights(
    existing: dict[str, float],
    win_rate_by_event_type: dict[str, float],
) -> dict[str, float]:
    updated = dict(existing)
    for event_type, wr in win_rate_by_event_type.items():
        current = float(updated.get(event_type, 1.0))
        if wr >= 0.58:
            current = min(1.8, current * 1.05)
        elif wr <= 0.48:
            current = max(0.4, current * 0.95)
        updated[event_type] = round(current, 6)
    return updated

