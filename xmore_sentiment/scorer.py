"""Sentiment scoring orchestrator."""

from __future__ import annotations

from datetime import timedelta

from xmore_sentiment.confidence import compute_confidence
from xmore_sentiment.rule_engine import compute_rule_score
from xmore_sentiment.schemas import ArticleInput, ExtractedFacts, SentimentResult
from xmore_sentiment.validator import dual_validate, keyword_polarity_score


def score_article(
    article: ArticleInput,
    facts: ExtractedFacts,
    *,
    weight_multiplier: float = 1.0,
) -> SentimentResult:
    """
    Compute sentiment result from extracted facts + dual validation.
    """
    rule = compute_rule_score(facts)
    keyword_polarity = keyword_polarity_score(f"{article.title}\n{article.content}")
    validation = dual_validate(rule.normalized, keyword_polarity)

    conf = compute_confidence(
        facts,
        keyword_polarity=keyword_polarity,
        rule_score=rule.normalized,
    )
    adjusted_conf = max(0.0, min(1.0, conf.confidence * validation.confidence_penalty))

    final = max(-1.0, min(1.0, rule.normalized * adjusted_conf * weight_multiplier))
    symbol = _pick_primary_symbol(article, facts)

    return SentimentResult(
        article_id=article.id or -1,
        symbol=symbol,
        raw_score=rule.normalized,
        confidence=adjusted_conf,
        final_sentiment=final,
        keyword_polarity=keyword_polarity,
        disagreement=validation.disagreement,
        uncertain=validation.uncertain,
        publish_date=article.published_at,
    )


def apply_sentiment_to_signal(
    base_signal_confidence: float,
    sentiment_score: float,
    sentiment_confidence: float,
    *,
    max_adjustment: float = 0.2,
) -> float:
    """
    Risk control integration:
    - never triggers trades on its own
    - only adjusts confidence/position sizing.
    """
    base = max(0.0, min(1.0, base_signal_confidence))
    adjustment = sentiment_score * sentiment_confidence * max_adjustment
    return max(0.0, min(1.0, base + adjustment))


def compute_future_dates(published_at) -> tuple:
    return (
        published_at,
        published_at + timedelta(days=1),
        published_at + timedelta(days=3),
        published_at + timedelta(days=5),
    )


def _pick_primary_symbol(article: ArticleInput, facts: ExtractedFacts) -> str:
    if facts.company_names:
        return facts.company_names[0].replace(".CA", "").upper()
    if article.mentioned_symbols:
        return article.mentioned_symbols[0].replace(".CA", "").upper()
    return "MARKET"

