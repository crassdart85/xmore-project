"""CLI runner for Xmore Sentiment Intelligence Layer."""

from __future__ import annotations

import argparse
import logging
import os
import sys
from collections.abc import Sequence

try:
    from dotenv import load_dotenv

    load_dotenv()
except Exception:
    pass

from xmore_sentiment.extractor import LLMFactExtractor
from xmore_sentiment.schemas import ArticleInput
from xmore_sentiment.scorer import score_article
from xmore_sentiment.storage import SentimentStorage, StorageConfig
from xmore_sentiment.validator import adjust_weight_multiplier, build_validation_metrics


def parse_args(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Xmore Structured Sentiment Pipeline")
    parser.add_argument("--db-path", default=os.getenv("XMORE_SENTIMENT_DB_PATH", "xmore_sentiment.db"))
    parser.add_argument("--prices-db-path", default=os.getenv("XMORE_PRICES_DB_PATH", "stocks.db"))
    parser.add_argument("--import-news-db", default="", help="Path to xmore_news sqlite db")
    parser.add_argument("--limit", type=int, default=100, help="Max articles per run")
    parser.add_argument("--log-level", default="INFO", help="DEBUG|INFO|WARNING|ERROR")
    return parser.parse_args(argv)


def run_pipeline(args: argparse.Namespace) -> dict:
    storage = SentimentStorage(
        StorageConfig(
            sqlite_path=args.db_path,
            price_db_path=args.prices_db_path,
        )
    )

    if args.import_news_db:
        imported = storage.import_articles_from_news_db(args.import_news_db)
        logging.info("Imported %s articles from %s", imported, args.import_news_db)

    extractor = LLMFactExtractor()
    weight_multiplier = storage.get_current_weight_multiplier()

    processed = 0
    discarded = 0
    articles = storage.fetch_unprocessed_articles(limit=args.limit)
    for article in articles:
        try:
            facts = extractor.extract(article)
            if facts is None:
                discarded += 1
                storage.mark_article_processed(article.id or -1)
                continue

            article_id = article.id if article.id is not None else storage.upsert_article(article)
            if article_id is None:
                discarded += 1
                continue
            article.id = article_id

            storage.save_facts(article_id, facts)

            symbols = facts.company_names or article.mentioned_symbols or ["MARKET"]
            for symbol in symbols:
                scoped_article = ArticleInput.model_validate({**article.model_dump(), "mentioned_symbols": [symbol]})
                result = score_article(scoped_article, facts, weight_multiplier=weight_multiplier)
                result.symbol = symbol.replace(".CA", "").upper()
                result.article_id = article_id
                result = storage.enrich_with_prices(result)
                storage.save_sentiment_result(result)

            storage.mark_article_processed(article_id)
            processed += 1
        except Exception:
            logging.exception("Failed processing article id=%s", article.id)
            discarded += 1
            if article.id:
                storage.mark_article_processed(article.id)

    history = storage.fetch_sentiment_history(limit=500)
    metrics = build_validation_metrics(history, weight_multiplier=weight_multiplier)
    new_weight = adjust_weight_multiplier(weight_multiplier, metrics)
    metrics.weight_multiplier = new_weight
    storage.save_validation_metrics(metrics)

    summary = {
        "fetched": len(articles),
        "processed": processed,
        "discarded": discarded,
        "weight_before": weight_multiplier,
        "weight_after": new_weight,
        "metrics_sample_size": metrics.sample_size,
    }
    return summary


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    logging.basicConfig(
        level=getattr(logging, str(args.log_level).upper(), logging.INFO),
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    )

    summary = run_pipeline(args)
    logging.info("Sentiment pipeline complete: %s", summary)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
