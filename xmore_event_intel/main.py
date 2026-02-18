"""Event Intelligence and Arabic sentiment pipeline entrypoint."""

from __future__ import annotations

import argparse
import logging
from datetime import datetime

from xmore_event_intel.arabic_sentiment.arabic_lexicon import score_arabic_lexicon
from xmore_event_intel.arabic_sentiment.arabic_llm_extractor import ArabicLLMExtractor
from xmore_event_intel.arabic_sentiment.arabic_preprocessor import build_sentiment_text
from xmore_event_intel.earnings_extractor import extract_earnings_delta
from xmore_event_intel.event_tagging import tag_event
from xmore_event_intel.performance_validator import evaluate_historical_performance
from xmore_event_intel.sources.dailynews_scraper import fetch_dailynews_news
from xmore_event_intel.sources.egx_disclosures_scraper import fetch_egx_disclosures
from xmore_event_intel.sources.egypttoday_scraper import fetch_egypttoday_news
from xmore_event_intel.sources.enterprise_scraper import fetch_enterprise_news
from xmore_event_intel.sources.mubasher_scraper import fetch_mubasher_news
from xmore_event_intel.storage import (
    ArticleRecord,
    EventIntelStorage,
    SentimentScoreRecord,
    StructuredEventRecord,
)

logger = logging.getLogger(__name__)


def run_pipeline(limit: int = 500) -> dict:
    storage = EventIntelStorage()
    llm = ArabicLLMExtractor()
    existing_weights = storage.get_event_weights()

    articles = _collect_all_articles()
    if limit > 0:
        articles = articles[:limit]

    processed = 0
    for raw in articles:
        try:
            article = ArticleRecord(
                title=str(raw.get("title", "")),
                content=str(raw.get("content", "")),
                published_at=_parse_dt(raw.get("published_at")),
                source=str(raw.get("source", "")),
                url=str(raw.get("url", "")),
                detected_symbols=list(raw.get("detected_symbols", [])),
                raw_html=str(raw.get("raw_html", "")),
            )
            article_id = storage.upsert_article(article)

            combined_text = build_sentiment_text(article.title, article.content)
            lex = score_arabic_lexicon(combined_text)
            llm_facts = llm.extract(article.title, article.content)
            earnings = extract_earnings_delta(f"{article.title}\n{article.content}")

            guidance = llm_facts.guidance_direction if llm_facts else None
            revenue_delta = llm_facts.revenue_change_percent if llm_facts else earnings.revenue_change_percent
            profit_delta = llm_facts.profit_change_percent if llm_facts else earnings.profit_change_percent

            event = tag_event(
                f"{article.title}\n{article.content}",
                revenue_change_percent=revenue_delta,
                profit_change_percent=profit_delta,
                guidance_direction=guidance,
            )

            event_weight = existing_weights.get(event.event_type, 1.0)
            deterministic = _build_deterministic_score(
                event_strength=event.event_strength,
                lexicon_polarity=lex.polarity,
                earnings_surprise=earnings.earnings_surprise,
                event_weight=event_weight,
            )
            confidence = _compute_confidence(
                llm_certainty=(llm_facts.certainty if llm_facts else 0.35),
                quantitative_fields=earnings.quantitative_fields_present,
                entity_strength=(1.0 if article.detected_symbols else 0.45),
            )
            final_sentiment_score = deterministic * confidence
            symbol = article.detected_symbols[0] if article.detected_symbols else "MARKET"

            storage.save_structured_event(
                StructuredEventRecord(
                    article_id=article_id,
                    symbol=symbol,
                    event_type=event.event_type,
                    event_strength=event.event_strength,
                    revenue_change_percent=earnings.revenue_change_percent,
                    profit_change_percent=earnings.profit_change_percent,
                    earnings_surprise=earnings.earnings_surprise,
                    extracted_payload={
                        "lexicon_positive_terms": lex.positive_terms,
                        "lexicon_negative_terms": lex.negative_terms,
                        "llm_structured": llm_facts.model_dump() if llm_facts else None,
                        "earnings": earnings.model_dump(),
                    },
                )
            )

            prices = storage.enrich_forward_prices(symbol, article.published_at)
            storage.save_sentiment_score(
                SentimentScoreRecord(
                    article_id=article_id,
                    symbol=symbol,
                    event_type=event.event_type,
                    sentiment_score=round(max(-1.0, min(1.0, final_sentiment_score)), 6),
                    confidence=round(max(0.0, min(1.0, confidence)), 6),
                    publish_time=article.published_at,
                    price_at_publish=prices["price_at_publish"],
                    price_1d=prices["price_1d"],
                    price_3d=prices["price_3d"],
                    price_5d=prices["price_5d"],
                    return_1d=prices["return_1d"],
                    return_3d=prices["return_3d"],
                    return_5d=prices["return_5d"],
                )
            )
            processed += 1
        except Exception as exc:
            logger.exception("Article processing failed for url=%s error=%s", raw.get("url"), exc)

    history = storage.fetch_scoring_history(limit=500)
    metrics = evaluate_historical_performance(history, existing_weights=existing_weights)
    _persist_metrics(storage, metrics)

    return {
        "articles_collected": len(articles),
        "articles_processed": processed,
        "rolling_accuracy_30": metrics.rolling_accuracy_30,
        "corr_1d": metrics.corr_1d,
        "corr_3d": metrics.corr_3d,
        "corr_5d": metrics.corr_5d,
    }


def _collect_all_articles() -> list[dict]:
    collected = (
        fetch_enterprise_news()
        + fetch_dailynews_news()
        + fetch_egypttoday_news()
        + fetch_mubasher_news()
        + fetch_egx_disclosures()
    )
    out: list[dict] = []
    seen: set[str] = set()
    for row in collected:
        url = str(row.get("url", "")).strip()
        if not url or url in seen:
            continue
        seen.add(url)
        out.append(row)
    return out


def _build_deterministic_score(
    *,
    event_strength: float,
    lexicon_polarity: float,
    earnings_surprise: float | None,
    event_weight: float,
) -> float:
    surprise_component = 0.0 if earnings_surprise is None else max(-1.0, min(1.0, earnings_surprise))
    base = (0.55 * event_strength) + (0.25 * lexicon_polarity) + (0.20 * surprise_component)
    return max(-1.0, min(1.0, base * event_weight))


def _compute_confidence(*, llm_certainty: float, quantitative_fields: int, entity_strength: float) -> float:
    q_presence = min(1.0, quantitative_fields / 5.0)
    confidence = (0.5 * llm_certainty) + (0.3 * q_presence) + (0.2 * entity_strength)
    return max(0.0, min(1.0, confidence))


def _persist_metrics(storage: EventIntelStorage, metrics) -> None:
    now = datetime.utcnow()
    storage.save_metric("rolling_accuracy_30", metrics.rolling_accuracy_30, metric_date=now)
    storage.save_metric("corr_1d", metrics.corr_1d, metric_date=now)
    storage.save_metric("corr_3d", metrics.corr_3d, metric_date=now)
    storage.save_metric("corr_5d", metrics.corr_5d, metric_date=now)
    storage.save_metric("overall_win_rate", metrics.overall_win_rate, metric_date=now)

    for event_type, win_rate in metrics.win_rate_by_event_type.items():
        storage.save_metric(
            "win_rate_by_event_type",
            win_rate,
            event_type=event_type,
            metric_date=now,
            metadata={"window": "all_available"},
        )
    for event_type, weight in metrics.updated_event_weights.items():
        storage.upsert_event_weight(event_type, weight)


def _parse_dt(value) -> datetime:
    text = str(value or "").strip()
    if not text:
        return datetime.utcnow()
    for candidate in (text.replace("Z", "+00:00"), text):
        try:
            return datetime.fromisoformat(candidate)
        except ValueError:
            continue
    try:
        return datetime.strptime(text[:19], "%Y-%m-%d %H:%M:%S")
    except ValueError:
        return datetime.utcnow()


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Xmore Event Intelligence pipeline")
    parser.add_argument("--limit", type=int, default=500, help="Max articles to process")
    parser.add_argument("--log-level", type=str, default="INFO", help="DEBUG|INFO|WARNING|ERROR")
    return parser


def main() -> None:
    parser = _build_arg_parser()
    args = parser.parse_args()
    logging.basicConfig(
        level=getattr(logging, str(args.log_level).upper(), logging.INFO),
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )
    result = run_pipeline(limit=args.limit)
    logger.info("Pipeline complete: %s", result)


if __name__ == "__main__":
    main()

