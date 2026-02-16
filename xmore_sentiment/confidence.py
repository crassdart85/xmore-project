"""Confidence model for sentiment scoring outputs."""

from __future__ import annotations

from xmore_sentiment.schemas import ConfidenceBreakdown, ExtractedFacts


def compute_confidence(
    facts: ExtractedFacts,
    *,
    keyword_polarity: float,
    rule_score: float,
) -> ConfidenceBreakdown:
    """
    Compute confidence using extraction certainty and structural strength.
    """
    llm_certainty = _clip(facts.certainty, 0.0, 1.0)
    entity_strength = 1.0 if (facts.company_mentioned and facts.primary_subject) else (0.6 if facts.company_mentioned else 0.3)
    quantitative_data_presence = _quant_presence(facts)
    agreement_strength = _agreement_strength(keyword_polarity, rule_score)

    confidence = (
        llm_certainty * 0.35
        + entity_strength * 0.25
        + quantitative_data_presence * 0.25
        + agreement_strength * 0.15
    )
    confidence = _clip(confidence, 0.0, 1.0)

    return ConfidenceBreakdown(
        llm_certainty=llm_certainty,
        entity_strength=entity_strength,
        quantitative_data_presence=quantitative_data_presence,
        agreement_strength=agreement_strength,
        confidence=confidence,
    )


def _quant_presence(facts: ExtractedFacts) -> float:
    fields = [
        facts.revenue_change_percent,
        facts.profit_change_percent,
        facts.debt_change_percent,
        None if facts.guidance_direction.value == "null" else facts.guidance_direction.value,
    ]
    count = sum(1 for item in fields if item is not None)
    return count / len(fields)


def _agreement_strength(keyword_polarity: float, rule_score: float) -> float:
    if abs(rule_score) < 0.05 and abs(keyword_polarity) < 0.05:
        return 1.0
    if (rule_score > 0 and keyword_polarity > 0) or (rule_score < 0 and keyword_polarity < 0):
        return 0.9
    if abs(rule_score - keyword_polarity) <= 0.25:
        return 0.6
    return 0.25


def _clip(value: float, lower: float, upper: float) -> float:
    return max(lower, min(upper, value))

