"""
Sentiment Analysis Module

This module fetches financial news from Finnhub and analyzes sentiment using FinBERT.
Results are stored in the database for use by prediction agents.

Key components:
- Finnhub API integration for company news
- FinBERT transformer model for financial sentiment analysis
- Database persistence with aggregated sentiment scores
"""

import os
import time
from datetime import datetime, timedelta
import logging

import finnhub

from database import get_connection, log_system_run, create_tables
import config

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Check if using PostgreSQL
DATABASE_URL = os.getenv('DATABASE_URL')
FINNHUB_API_KEY = os.getenv('FINNHUB_API_KEY', '')


def _adapt_sql(sql):
    """Convert SQLite SQL to PostgreSQL when needed."""
    if DATABASE_URL:
        sql = sql.replace('?', '%s')
        sql = sql.replace('INSERT OR IGNORE', 'INSERT')
        if 'INSERT' in sql and 'ON CONFLICT' not in sql:
            sql = sql.rstrip().rstrip(')') + ') ON CONFLICT DO NOTHING'
    return sql


def create_sentiment_table():
    """
    Create the sentiment_scores table if it doesn't exist.

    Schema:
    - symbol: Stock ticker
    - date: Date of sentiment analysis
    - avg_sentiment: Average sentiment score (-1 to 1)
    - sentiment_label: Bullish/Neutral/Bearish
    - article_count: Number of articles analyzed
    - positive_count: Articles with positive sentiment
    - negative_count: Articles with negative sentiment
    - neutral_count: Articles with neutral sentiment
    """
    if DATABASE_URL:
        auto_id = "SERIAL PRIMARY KEY"
    else:
        auto_id = "INTEGER PRIMARY KEY AUTOINCREMENT"

    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS sentiment_scores (
                id {auto_id},
                symbol TEXT NOT NULL,
                date DATE NOT NULL,
                avg_sentiment REAL,
                sentiment_label TEXT,
                article_count INTEGER DEFAULT 0,
                positive_count INTEGER DEFAULT 0,
                negative_count INTEGER DEFAULT 0,
                neutral_count INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(symbol, date)
            )
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_sentiment_symbol_date ON sentiment_scores(symbol, date)")
        logger.info("Sentiment table ready")


def get_finnhub_news(symbol: str, days_back: int = 7) -> list:
    """
    Fetch company news from Finnhub API.

    Args:
        symbol: Stock ticker (e.g., 'AAPL')
        days_back: Number of days to look back for news

    Returns:
        List of news articles with headline, datetime, source, url
    """
    if not FINNHUB_API_KEY:
        logger.warning("FINNHUB_API_KEY not set, skipping news fetch")
        return []

    client = finnhub.Client(api_key=FINNHUB_API_KEY)

    # Calculate date range
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days_back)

    # Clean symbol for Finnhub (remove .CA suffix for EGX stocks)
    clean_symbol = symbol.split('.')[0]

    try:
        news = client.company_news(
            clean_symbol,
            _from=start_date.strftime('%Y-%m-%d'),
            to=end_date.strftime('%Y-%m-%d')
        )
        logger.info(f"  Fetched {len(news)} articles for {symbol}")
        return news
    except Exception as e:
        logger.error(f"  Error fetching news for {symbol}: {e}")
        return []


def analyze_sentiment_finbert(headlines: list) -> dict:
    """
    Analyze sentiment of headlines using FinBERT.

    Args:
        headlines: List of news headline strings

    Returns:
        dict with:
        - avg_score: Average sentiment (-1 to 1)
        - label: 'Bullish', 'Neutral', or 'Bearish'
        - positive_count, negative_count, neutral_count
    """
    if not headlines:
        return {
            'avg_score': 0,
            'label': 'Neutral',
            'positive_count': 0,
            'negative_count': 0,
            'neutral_count': 0
        }

    try:
        from transformers import pipeline
        sentiment_pipeline = pipeline("sentiment-analysis", model="ProsusAI/finbert")
    except ImportError:
        logger.warning("Transformers not installed, returning neutral sentiment")
        return {
            'avg_score': 0,
            'label': 'Neutral',
            'positive_count': 0,
            'negative_count': 0,
            'neutral_count': len(headlines)
        }
    except Exception as e:
        logger.error(f"Error loading FinBERT: {e}")
        return {
            'avg_score': 0,
            'label': 'Neutral',
            'positive_count': 0,
            'negative_count': 0,
            'neutral_count': len(headlines)
        }

    scores = []
    positive_count = 0
    negative_count = 0
    neutral_count = 0

    for headline in headlines:
        try:
            # Truncate long headlines (FinBERT max length)
            text = headline[:512] if len(headline) > 512 else headline
            result = sentiment_pipeline(text)[0]

            label = result['label'].lower()
            score = result['score']

            if label == 'positive':
                scores.append(score)
                positive_count += 1
            elif label == 'negative':
                scores.append(-score)
                negative_count += 1
            else:  # neutral
                scores.append(0)
                neutral_count += 1

        except Exception as e:
            logger.warning(f"Error analyzing headline: {e}")
            neutral_count += 1
            scores.append(0)

    avg_score = sum(scores) / len(scores) if scores else 0

    # Determine overall label based on average score
    if avg_score > 0.1:
        label = 'Bullish'
    elif avg_score < -0.1:
        label = 'Bearish'
    else:
        label = 'Neutral'

    return {
        'avg_score': avg_score,
        'label': label,
        'positive_count': positive_count,
        'negative_count': negative_count,
        'neutral_count': neutral_count
    }


def collect_sentiment(symbols: list = None, days_back: int = 7):
    """
    Main function to collect news and analyze sentiment for all stocks.

    Args:
        symbols: List of stock symbols (defaults to config.ALL_STOCKS)
        days_back: Number of days to look back for news

    Returns:
        int: Number of stocks successfully processed
    """
    if symbols is None:
        symbols = config.ALL_STOCKS

    logger.info(f"Starting sentiment collection for {len(symbols)} stocks")

    # Create table if needed
    create_sentiment_table()

    success_count = 0
    today = datetime.now().strftime('%Y-%m-%d')

    for symbol in symbols:
        logger.info(f"Processing {symbol}...")

        # Fetch news from Finnhub
        news = get_finnhub_news(symbol, days_back)

        if not news:
            logger.info(f"  No news found for {symbol}")
            # Still record a neutral entry so we know we checked
            _save_sentiment(symbol, today, 0, 'Neutral', 0, 0, 0, 0)
            success_count += 1
            continue

        # Extract headlines
        headlines = [article.get('headline', '') for article in news if article.get('headline')]

        # Analyze sentiment
        sentiment = analyze_sentiment_finbert(headlines)

        # Save to database
        _save_sentiment(
            symbol=symbol,
            date=today,
            avg_sentiment=sentiment['avg_score'],
            label=sentiment['label'],
            article_count=len(headlines),
            positive_count=sentiment['positive_count'],
            negative_count=sentiment['negative_count'],
            neutral_count=sentiment['neutral_count']
        )

        logger.info(f"  {symbol}: {sentiment['label']} (score: {sentiment['avg_score']:.3f}, articles: {len(headlines)})")
        success_count += 1

        # Rate limiting for Finnhub free tier (60 calls/min)
        time.sleep(1)

    return success_count


def _save_sentiment(symbol: str, date: str, avg_sentiment: float, label: str,
                    article_count: int, positive_count: int, negative_count: int, neutral_count: int):
    """Save sentiment data to database."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(_adapt_sql("""
            INSERT OR IGNORE INTO sentiment_scores
            (symbol, date, avg_sentiment, sentiment_label, article_count,
             positive_count, negative_count, neutral_count)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """), (symbol, date, avg_sentiment, label, article_count,
               positive_count, negative_count, neutral_count))


def get_latest_sentiment(symbol: str) -> dict:
    """
    Get the most recent sentiment data for a symbol.

    Args:
        symbol: Stock ticker

    Returns:
        dict with sentiment data or None if not found
    """
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(_adapt_sql("""
            SELECT * FROM sentiment_scores
            WHERE symbol = ?
            ORDER BY date DESC
            LIMIT 1
        """), (symbol,))
        row = cursor.fetchone()
        return dict(row) if row else None


def get_all_latest_sentiment() -> list:
    """
    Get the most recent sentiment for all stocks.

    Returns:
        List of sentiment records (one per symbol)
    """
    with get_connection() as conn:
        cursor = conn.cursor()
        # Subquery to get max date per symbol
        if DATABASE_URL:
            cursor.execute("""
                SELECT DISTINCT ON (symbol) *
                FROM sentiment_scores
                ORDER BY symbol, date DESC
            """)
        else:
            cursor.execute("""
                SELECT s.*
                FROM sentiment_scores s
                INNER JOIN (
                    SELECT symbol, MAX(date) as max_date
                    FROM sentiment_scores
                    GROUP BY symbol
                ) latest ON s.symbol = latest.symbol AND s.date = latest.max_date
            """)
        return [dict(row) for row in cursor.fetchall()]


if __name__ == "__main__":
    start_time = time.time()
    print(f"Starting sentiment analysis at {datetime.now()}")
    print(f"Processing {len(config.ALL_STOCKS)} stocks")

    # Ensure database tables exist
    create_tables()

    try:
        count = collect_sentiment()
        duration = time.time() - start_time
        msg = f"Analyzed sentiment for {count} stocks"
        log_system_run("sentiment.py", "success", msg, duration)
        print(f"Sentiment collection complete! {msg}")
        print(f"Duration: {duration:.1f} seconds")

    except Exception as e:
        duration = time.time() - start_time
        log_system_run("sentiment.py", "failure", str(e), duration)
        print(f"Sentiment collection failed: {e}")
        raise
