"""Deterministic earnings delta extraction."""

from __future__ import annotations

import re
from typing import Iterable

from pydantic import BaseModel, ConfigDict, Field


class EarningsDelta(BaseModel):
    """Structured quantitative extraction from article text."""

    model_config = ConfigDict(extra="forbid")

    revenue_current: float | None = None
    revenue_previous: float | None = None
    revenue_change_percent: float | None = None
    profit_current: float | None = None
    profit_previous: float | None = None
    profit_change_percent: float | None = None
    eps_current: float | None = None
    eps_expected: float | None = None
    earnings_surprise: float | None = None
    quantitative_fields_present: int = Field(ge=0)


_PERCENT_RE = re.compile(r"([+-]?\d+(?:\.\d+)?)\s*%")
_NUMBER_RE = re.compile(r"([+-]?\d+(?:[.,]\d+)?)\s*(billion|million|bn|mn|مليار|مليون)?", re.IGNORECASE)


def extract_earnings_delta(text: str) -> EarningsDelta:
    s = str(text or "")
    s_lower = s.lower()

    revenue_numbers = _extract_label_numbers(s, ("revenue", "sales", "الايرادات", "الإيرادات"))
    profit_numbers = _extract_label_numbers(s, ("profit", "net income", "ارباح", "أرباح", "صافي الربح"))
    eps_numbers = _extract_label_numbers(s, ("eps", "ربحيه السهم", "ربحية السهم"))

    rev_current, rev_previous = _pair_or_none(revenue_numbers)
    prof_current, prof_previous = _pair_or_none(profit_numbers)
    eps_current, eps_expected = _pair_or_none(eps_numbers)

    revenue_change = _first_percent_near(s_lower, ("revenue", "sales", "الايرادات", "الإيرادات"))
    profit_change = _first_percent_near(s_lower, ("profit", "net income", "ارباح", "أرباح"))

    if revenue_change is None and rev_current is not None and rev_previous not in (None, 0):
        revenue_change = ((rev_current - rev_previous) / rev_previous) * 100.0
    if profit_change is None and prof_current is not None and prof_previous not in (None, 0):
        profit_change = ((prof_current - prof_previous) / prof_previous) * 100.0

    surprise = None
    if eps_current is not None and eps_expected not in (None, 0):
        surprise = (eps_current - eps_expected) / eps_expected
    elif prof_current is not None and prof_previous not in (None, 0):
        surprise = (prof_current - prof_previous) / prof_previous

    present_fields = [
        rev_current,
        rev_previous,
        revenue_change,
        prof_current,
        prof_previous,
        profit_change,
        eps_current,
        eps_expected,
        surprise,
    ]

    return EarningsDelta(
        revenue_current=rev_current,
        revenue_previous=rev_previous,
        revenue_change_percent=_safe_round(revenue_change),
        profit_current=prof_current,
        profit_previous=prof_previous,
        profit_change_percent=_safe_round(profit_change),
        eps_current=eps_current,
        eps_expected=eps_expected,
        earnings_surprise=_safe_round(surprise),
        quantitative_fields_present=sum(1 for x in present_fields if x is not None),
    )


def _extract_label_numbers(text: str, labels: Iterable[str]) -> list[float]:
    values: list[float] = []
    lower = text.lower()
    for label in labels:
        idx = lower.find(label.lower())
        if idx < 0:
            continue
        window = text[max(0, idx - 120) : idx + 180]
        for match in _NUMBER_RE.finditer(window):
            parsed = _parse_number(match.group(1), match.group(2))
            if parsed is not None:
                values.append(parsed)
    return values


def _first_percent_near(text: str, labels: Iterable[str]) -> float | None:
    for label in labels:
        idx = text.find(label.lower())
        if idx < 0:
            continue
        window = text[max(0, idx - 80) : idx + 120]
        m = _PERCENT_RE.search(window)
        if m:
            return float(m.group(1))
    return None


def _parse_number(value: str | None, unit: str | None) -> float | None:
    if not value:
        return None
    try:
        x = float(value.replace(",", "."))
    except Exception:
        return None
    u = (unit or "").lower()
    if u in {"billion", "bn", "مليار"}:
        x *= 1_000_000_000
    elif u in {"million", "mn", "مليون"}:
        x *= 1_000_000
    return float(x)


def _pair_or_none(values: list[float]) -> tuple[float | None, float | None]:
    if not values:
        return None, None
    if len(values) == 1:
        return values[0], None
    return values[0], values[1]


def _safe_round(value: float | None) -> float | None:
    if value is None:
        return None
    return round(float(value), 6)

