"""
RSS News Collector for Egyptian Financial News

This module fetches news from Egyptian financial RSS feeds and analyzes sentiment.
It supplements the NewsAPI collector with local Egyptian sources that have better
coverage of EGX-listed companies.

Supported Sources:
- Mubasher Egypt (Arabic business news)
- Enterprise (English business news)
- Egypt Today Business (English)
- Daily News Egypt (English)
- Al-Mal News (Arabic)
"""

import feedparser
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import re
import logging

from database import get_connection
from egx_symbols import get_stock_info, get_search_keywords, EGX_SYMBOL_DATABASE

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ============================================
# RSS FEED SOURCES
# ============================================

EGYPTIAN_NEWS_FEEDS = [
    {
        "name": "Enterprise Egypt",
        "url": "https://enterprise.press/feed/",
        "language": "en",
        "focus": "business",
        "reliability": "high"
    },
    {
        "name": "Daily News Egypt",
        "url": "https://dailynewsegypt.com/feed/",
        "language": "en",
        "focus": "general",
        "reliability": "medium"
    },
    {
        "name": "Egypt Today Business",
        "url": "https://www.egypttoday.com/RSS/15",
        "language": "en",
        "focus": "business",
        "reliability": "high"
    },
    {
        "name": "Ahram Online Business",
        "url": "https://english.ahram.org.eg/UI/Front/RSS.aspx?CatID=3",
        "language": "en",
        "focus": "business",
        "reliability": "high"
    },
    {
        "name": "Mubasher Egypt",
        "url": "https://www.mubasher.info/api/1/feed/stories-feed-egypt",
        "language": "ar",
        "focus": "markets",
        "reliability": "high"
    },
]


def _adapt_sql(sql: str) -> str:
    """Convert SQLite SQL to PostgreSQL when needed."""
    import os
    if os.getenv('DATABASE_URL'):
        sql = sql.replace('?', '%s')
        sql = sql.replace('INSERT OR IGNORE', 'INSERT')
        if 'INSERT' in sql and 'ON CONFLICT' not in sql:
            sql = sql.rstrip().rstrip(')') + ') ON CONFLICT DO NOTHING'
    return sql


def fetch_rss_feed(feed_url: str, timeout: int = 30) -> List[Dict]:
    """
    Fetch and parse an RSS feed.

    Args:
        feed_url: URL of the RSS feed
        timeout: Request timeout in seconds

    Returns:
        List of article dictionaries with title, link, published date, summary
    """
    try:
        feed = feedparser.parse(feed_url)

        if feed.bozo and feed.bozo_exception:
            logger.warning(f"Feed parse warning for {feed_url}: {feed.bozo_exception}")

        articles = []
        for entry in feed.entries:
            # Parse published date
            pub_date = None
            if hasattr(entry, 'published_parsed') and entry.published_parsed:
                pub_date = datetime(*entry.published_parsed[:6])
            elif hasattr(entry, 'updated_parsed') and entry.updated_parsed:
                pub_date = datetime(*entry.updated_parsed[:6])
            else:
                pub_date = datetime.now()

            articles.append({
                'title': entry.get('title', ''),
                'link': entry.get('link', ''),
                'summary': entry.get('summary', entry.get('description', '')),
                'published': pub_date,
                'source': feed.feed.get('title', 'Unknown')
            })

        return articles

    except Exception as e:
        logger.error(f"Error fetching RSS feed {feed_url}: {e}")
        return []


def match_article_to_symbols(article: Dict) -> List[str]:
    """
    Match an article to relevant stock symbols based on content.

    Args:
        article: Article dictionary with title and summary

    Returns:
        List of matching stock symbols (Yahoo format)
    """
    text = f"{article.get('title', '')} {article.get('summary', '')}".upper()
    matched_symbols = []

    for ticker, stock in EGX_SYMBOL_DATABASE.items():
        # Check for ticker mention
        if re.search(rf'\b{ticker}\b', text):
            matched_symbols.append(stock.yahoo)
            continue

        # Check for company name (partial match)
        name_words = stock.name_en.upper().split()
        # Match if at least 2 significant words match
        significant_words = [w for w in name_words if len(w) > 3]
        matches = sum(1 for w in significant_words if w in text)
        if matches >= 2:
            matched_symbols.append(stock.yahoo)
            continue

        # Check Arabic name
        if stock.name_ar and stock.name_ar in article.get('title', ''):
            matched_symbols.append(stock.yahoo)

    return list(set(matched_symbols))


def analyze_sentiment_simple(text: str) -> Dict[str, any]:
    """
    Simple keyword-based sentiment analysis for financial news.

    This is a fallback when FinBERT is not available. Uses financial keyword matching.

    Args:
        text: Article title or summary

    Returns:
        Dictionary with sentiment_score (-1 to 1) and sentiment_label
    """
    text_lower = text.lower()

    # Financial positive keywords
    positive_words = [
        'rise', 'gain', 'profit', 'growth', 'surge', 'rally', 'bull', 'upturn',
        'increase', 'boost', 'record', 'high', 'expand', 'dividend', 'success',
        'ارتفاع', 'صعود', 'ربح', 'نمو', 'أرباح', 'إيجابي', 'تحسن'
    ]

    # Financial negative keywords
    negative_words = [
        'fall', 'drop', 'loss', 'decline', 'plunge', 'crash', 'bear', 'downturn',
        'decrease', 'slump', 'low', 'cut', 'fail', 'debt', 'risk', 'concern',
        'انخفاض', 'هبوط', 'خسارة', 'تراجع', 'سلبي', 'ديون', 'مخاطر'
    ]

    pos_count = sum(1 for word in positive_words if word in text_lower)
    neg_count = sum(1 for word in negative_words if word in text_lower)

    total = pos_count + neg_count
    if total == 0:
        return {'sentiment_score': 0.0, 'sentiment_label': 'neutral'}

    score = (pos_count - neg_count) / total

    if score > 0.2:
        label = 'positive'
    elif score < -0.2:
        label = 'negative'
    else:
        label = 'neutral'

    return {'sentiment_score': round(score, 3), 'sentiment_label': label}


def collect_rss_news(days_back: int = 3, use_finbert: bool = True) -> Dict[str, int]:
    """
    Collect news from all configured RSS feeds and save to database.

    Args:
        days_back: Only include articles from this many days ago
        use_finbert: Whether to use FinBERT for sentiment (falls back to simple)

    Returns:
        Dictionary with collection statistics
    """
    print("📰 Collecting Egyptian financial news from RSS feeds...")

    # Initialize FinBERT if requested
    sentiment_pipeline = None
    if use_finbert:
        try:
            from transformers import pipeline
            sentiment_pipeline = pipeline("sentiment-analysis", model="ProsusAI/finbert")
            print("🧠 Using FinBERT for sentiment analysis")
        except Exception as e:
            print(f"⚠️ FinBERT not available, using simple sentiment: {e}")

    cutoff_date = datetime.now() - timedelta(days=days_back)
    stats = {
        'feeds_processed': 0,
        'articles_fetched': 0,
        'articles_matched': 0,
        'articles_saved': 0,
        'errors': 0
    }

    for feed_config in EGYPTIAN_NEWS_FEEDS:
        try:
            print(f"  Fetching: {feed_config['name']}...")
            articles = fetch_rss_feed(feed_config['url'])
            stats['feeds_processed'] += 1
            stats['articles_fetched'] += len(articles)

            for article in articles:
                # Skip old articles
                if article['published'] < cutoff_date:
                    continue

                # Match to symbols
                matched_symbols = match_article_to_symbols(article)
                if not matched_symbols:
                    continue

                stats['articles_matched'] += 1

                # Analyze sentiment
                if sentiment_pipeline:
                    try:
                        result = sentiment_pipeline(article['title'][:512])[0]
                        sentiment_label = result['label']
                        score = result['score']
                        if sentiment_label == 'positive':
                            sentiment_score = score
                        elif sentiment_label == 'negative':
                            sentiment_score = -score
                        else:
                            sentiment_score = 0
                    except Exception:
                        sentiment = analyze_sentiment_simple(article['title'])
                        sentiment_score = sentiment['sentiment_score']
                        sentiment_label = sentiment['sentiment_label']
                else:
                    sentiment = analyze_sentiment_simple(article['title'])
                    sentiment_score = sentiment['sentiment_score']
                    sentiment_label = sentiment['sentiment_label']

                # Save to database for each matched symbol
                with get_connection() as conn:
                    cursor = conn.cursor()
                    for symbol in matched_symbols:
                        try:
                            cursor.execute(_adapt_sql("""
                                INSERT OR IGNORE INTO news
                                (symbol, date, headline, source, url, sentiment_score, sentiment_label)
                                VALUES (?, ?, ?, ?, ?, ?, ?)
                            """), (
                                symbol,
                                article['published'].strftime('%Y-%m-%d'),
                                article['title'][:500],
                                f"RSS:{feed_config['name']}",
                                article['link'],
                                sentiment_score,
                                sentiment_label
                            ))
                            stats['articles_saved'] += 1
                        except Exception as e:
                            logger.debug(f"Duplicate or error: {e}")

        except Exception as e:
            logger.error(f"Error processing feed {feed_config['name']}: {e}")
            stats['errors'] += 1

    return stats


def collect_news_for_symbol(symbol: str, days_back: int = 7) -> List[Dict]:
    """
    Collect news specifically for a single symbol from RSS feeds.

    Args:
        symbol: Stock symbol (COMI or COMI.CA)
        days_back: Days of news to fetch

    Returns:
        List of matched articles
    """
    stock = get_stock_info(symbol)
    if not stock:
        return []

    keywords = get_search_keywords(symbol)
    cutoff_date = datetime.now() - timedelta(days=days_back)
    matched_articles = []

    for feed_config in EGYPTIAN_NEWS_FEEDS:
        articles = fetch_rss_feed(feed_config['url'])
        for article in articles:
            if article['published'] < cutoff_date:
                continue

            text = f"{article['title']} {article['summary']}".upper()
            for keyword in keywords:
                if keyword.upper() in text:
                    article['matched_keyword'] = keyword
                    article['feed_source'] = feed_config['name']
                    matched_articles.append(article)
                    break

    return matched_articles


if __name__ == "__main__":
    print("=" * 60)
    print("Egyptian Financial News RSS Collector")
    print("=" * 60)

    # Test RSS feeds
    print("\nTesting RSS feed connectivity...")
    for feed in EGYPTIAN_NEWS_FEEDS:
        articles = fetch_rss_feed(feed['url'])
        status = "✅" if articles else "❌"
        print(f"  {status} {feed['name']}: {len(articles)} articles")

    # Run collection
    print("\nRunning news collection...")
    stats = collect_rss_news(days_back=3, use_finbert=False)

    print("\n📊 Collection Statistics:")
    for key, value in stats.items():
        print(f"  {key}: {value}")
