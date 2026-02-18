"""Deterministic event tagging engine."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class EventTag:
    event_type: str
    event_strength: float


EVENT_BASE_WEIGHTS: dict[str, float] = {
    "dividend_announcement": 0.65,
    "capital_increase": 0.7,
    "earnings_surprise_positive": 0.85,
    "earnings_surprise_negative": -0.85,
    "macro_interest_rate": 0.55,
    "guidance_raised": 0.7,
    "guidance_lowered": -0.7,
    "general_financial_update": 0.25,
}


def tag_event(
    text: str,
    *,
    revenue_change_percent: float | None = None,
    profit_change_percent: float | None = None,
    guidance_direction: str | None = None,
) -> EventTag:
    s = str(text or "").lower()
    s_ar = s

    if _contains_any(s, ("dividend", "cash dividend", "توزيع", "توزيعات")):
        return EventTag("dividend_announcement", EVENT_BASE_WEIGHTS["dividend_announcement"])

    if _contains_any(
        s,
        ("capital increase", "rights issue", "raise capital", "زياده راس المال", "زيادة رأس المال"),
    ):
        return EventTag("capital_increase", EVENT_BASE_WEIGHTS["capital_increase"])

    if _contains_any(s, ("central bank", "interest rate", "cbe", "البنك المركزي", "سعر الفايده", "سعر الفائدة")):
        return EventTag("macro_interest_rate", EVENT_BASE_WEIGHTS["macro_interest_rate"])

    rev = revenue_change_percent
    prof = profit_change_percent
    if _contains_any(s, ("revenue", "sales", "الايرادات", "الإيرادات")):
        if (rev is not None and rev > 0) or (prof is not None and prof > 0):
            return EventTag("earnings_surprise_positive", EVENT_BASE_WEIGHTS["earnings_surprise_positive"])
        if (rev is not None and rev < 0) or (prof is not None and prof < 0):
            return EventTag("earnings_surprise_negative", EVENT_BASE_WEIGHTS["earnings_surprise_negative"])

    if guidance_direction == "raised":
        return EventTag("guidance_raised", EVENT_BASE_WEIGHTS["guidance_raised"])
    if guidance_direction == "lowered":
        return EventTag("guidance_lowered", EVENT_BASE_WEIGHTS["guidance_lowered"])

    if _contains_any(
        s_ar,
        ("ارباح", "أرباح", "نتائج", "earnings", "guidance", "forecast", "توقعات", "quarter", "ربع"),
    ):
        return EventTag("general_financial_update", EVENT_BASE_WEIGHTS["general_financial_update"])

    return EventTag("general_financial_update", 0.0)


def _contains_any(text: str, terms: tuple[str, ...]) -> bool:
    return any(t in text for t in terms)

