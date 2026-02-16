"""Deterministic rule-based sentiment engine."""

from __future__ import annotations

from typing import Final

from xmore_sentiment.schemas import ExtractedFacts, RuleScore


KEYWORD_WEIGHTS: Final[dict[str, float]] = {
    "growth": 0.12,
    "beat": 0.16,
    "surge": 0.16,
    "upgrade": 0.14,
    "raised": 0.10,
    "decline": -0.14,
    "miss": -0.18,
    "drop": -0.12,
    "downgrade": -0.14,
    "warning": -0.16,
    "default": -0.22,
}


def compute_rule_score(facts: ExtractedFacts) -> RuleScore:
    """
    Deterministic financial sentiment score from extracted facts.
    """
    components: dict[str, float] = {}
    score = 0.0

    if facts.profit_change_percent is not None:
        if facts.profit_change_percent > 0:
            components["profit_positive"] = 0.5
            score += 0.5
        elif facts.profit_change_percent < 0:
            components["profit_negative"] = -0.5
            score -= 0.5

    if facts.revenue_change_percent is not None:
        if facts.revenue_change_percent > 0:
            components["revenue_positive"] = 0.3
            score += 0.3
        elif facts.revenue_change_percent < 0:
            components["revenue_negative"] = -0.3
            score -= 0.3

    if facts.debt_change_percent is not None:
        if facts.debt_change_percent < 0:
            components["debt_reduced"] = 0.2
            score += 0.2
        elif facts.debt_change_percent > 0:
            components["debt_increased"] = -0.2
            score -= 0.2

    if facts.guidance_direction.value == "raised":
        components["guidance_raised"] = 0.4
        score += 0.4
    elif facts.guidance_direction.value == "lowered":
        components["guidance_lowered"] = -0.4
        score -= 0.4

    keyword_score = sum(KEYWORD_WEIGHTS.get(k.lower().strip(), 0.0) for k in facts.tone_keywords_detected)
    if keyword_score:
        components["tone_keywords"] = round(keyword_score, 4)
        score += keyword_score

    company_specific = facts.company_mentioned and facts.primary_subject
    applied_weight = 1.0
    if facts.macro_related and not company_specific:
        applied_weight = 0.5
        components["macro_downweight"] = -0.0
        score *= applied_weight

    normalized = _clip(score, -1.0, 1.0)
    return RuleScore(
        raw_score=normalized,
        components=components,
        normalized=normalized,
        company_specific_weight_applied=applied_weight,
    )


def _clip(value: float, lower: float, upper: float) -> float:
    return max(lower, min(upper, value))

