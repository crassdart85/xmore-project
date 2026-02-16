"""Dual validation and historical performance metrics for sentiment."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Iterable

from xmore_sentiment.schemas import ValidationMetrics


POSITIVE_KEYWORDS: tuple[str, ...] = (
    "growth",
    "beat",
    "surge",
    "record",
    "raised guidance",
    "upgrade",
    "profit rose",
    "strong demand",
)
NEGATIVE_KEYWORDS: tuple[str, ...] = (
    "decline",
    "miss",
    "warning",
    "downgrade",
    "loss widened",
    "debt burden",
    "profit fell",
    "weak demand",
    "default",
)


@dataclass
class DualValidationResult:
    keyword_polarity: float
    disagreement: float
    uncertain: bool
    confidence_penalty: float


def keyword_polarity_score(text: str) -> float:
    """Dictionary polarity score in [-1,1]."""
    lowered = (text or "").lower()
    pos = sum(lowered.count(w) for w in POSITIVE_KEYWORDS)
    neg = sum(lowered.count(w) for w in NEGATIVE_KEYWORDS)
    total = pos + neg
    if total == 0:
        return 0.0
    return max(-1.0, min(1.0, (pos - neg) / total))


def dual_validate(rule_score: float, keyword_polarity: float, threshold: float = 0.65) -> DualValidationResult:
    """
    Compare rule score vs keyword polarity and mark uncertain if disagreement is high.
    """
    disagreement = abs(rule_score - keyword_polarity)
    uncertain = disagreement > threshold
    penalty = 0.7 if uncertain else 1.0
    return DualValidationResult(
        keyword_polarity=keyword_polarity,
        disagreement=disagreement,
        uncertain=uncertain,
        confidence_penalty=penalty,
    )


def build_validation_metrics(rows: Iterable[dict], weight_multiplier: float) -> ValidationMetrics:
    """
    Compute correlation + direction accuracy metrics from sentiment history rows.
    """
    rows_list = list(rows)
    sample_size = len(rows_list)
    if sample_size == 0:
        return ValidationMetrics(sample_size=0, weight_multiplier=weight_multiplier)

    corr_1d = _correlation(rows_list, "sentiment_score", "return_1d")
    corr_3d = _correlation(rows_list, "sentiment_score", "return_3d")
    corr_5d = _correlation(rows_list, "sentiment_score", "return_5d")

    acc_1d = _direction_accuracy(rows_list, "sentiment_score", "return_1d")
    acc_3d = _direction_accuracy(rows_list, "sentiment_score", "return_3d")
    acc_5d = _direction_accuracy(rows_list, "sentiment_score", "return_5d")

    return ValidationMetrics(
        sample_size=sample_size,
        corr_1d=corr_1d,
        corr_3d=corr_3d,
        corr_5d=corr_5d,
        accuracy_1d=acc_1d,
        accuracy_3d=acc_3d,
        accuracy_5d=acc_5d,
        weight_multiplier=weight_multiplier,
    )


def adjust_weight_multiplier(current_weight: float, metrics: ValidationMetrics) -> float:
    """
    Auto-adjust sentiment weight based on rolling performance.
    """
    if metrics.sample_size < 100:
        return current_weight

    avg_accuracy = _avg([metrics.accuracy_1d, metrics.accuracy_3d, metrics.accuracy_5d])
    if avg_accuracy is None:
        return current_weight

    new_weight = current_weight
    if avg_accuracy < 0.48:
        new_weight *= 0.9
    elif avg_accuracy > 0.56:
        new_weight *= 1.05

    return max(0.3, min(1.5, new_weight))


def _direction_accuracy(rows: list[dict], lhs: str, rhs: str) -> float | None:
    hits = 0
    total = 0
    for row in rows:
        l = row.get(lhs)
        r = row.get(rhs)
        if l is None or r is None:
            continue
        if abs(float(l)) < 1e-9 or abs(float(r)) < 1e-9:
            continue
        total += 1
        if (float(l) > 0 and float(r) > 0) or (float(l) < 0 and float(r) < 0):
            hits += 1
    if total == 0:
        return None
    return hits / total


def _correlation(rows: list[dict], lhs: str, rhs: str) -> float | None:
    xs: list[float] = []
    ys: list[float] = []
    for row in rows:
        xv = row.get(lhs)
        yv = row.get(rhs)
        if xv is None or yv is None:
            continue
        xs.append(float(xv))
        ys.append(float(yv))
    if len(xs) < 3:
        return None

    x_mean = sum(xs) / len(xs)
    y_mean = sum(ys) / len(ys)
    cov = sum((x - x_mean) * (y - y_mean) for x, y in zip(xs, ys))
    x_var = sum((x - x_mean) ** 2 for x in xs)
    y_var = sum((y - y_mean) ** 2 for y in ys)
    if x_var <= 1e-12 or y_var <= 1e-12:
        return None
    return cov / math.sqrt(x_var * y_var)


def _avg(values: list[float | None]) -> float | None:
    usable = [v for v in values if v is not None]
    if not usable:
        return None
    return sum(usable) / len(usable)

