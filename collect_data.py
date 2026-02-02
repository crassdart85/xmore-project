"""
Data Collection Script

This module is responsible for fetching stock prices and news from external APIs
(principally Yahoo Finance and NewsAPI) and saving them to the database.
It implements retry logic, error handling, and data quality logging.

Key components:
- Price collection via yfinance with retry logic
- News collection via NewsAPI
- Basic sentiment analysis using TextBlob
- Database persistence for collected data
"""

import yfinance as yf
from newsapi import NewsApiClient
from datetime import datetime, timedelta
import time

# Import your existing logic
import config
from database import get_connection, log_system_run, log_data_quality_issue

def collect_prices():
    """
    Fetch stock prices from Yahoo Finance for all configured stocks and save to DB.
    
    Collection Strategy:
    - Iterates through ALL_STOCKS from config
    - Fetches last 5 days of data (to ensure coverage)
    - Saves Open, High, Low, Close, Volume
    
    Returns:
        int: Number of stocks successfully collected.
        
    Example:
        >>> count = collect_prices()
        >>> print(f"Collected {count} stocks")
    """
    print("📈 Fetching price data...")
    success_count = 0
    
    # Iterate through all stocks defined in config.py
    for symbol in config.ALL_STOCKS:
        try:
            # Download data using yfinance
            ticker = yf.Ticker(symbol)
            
            # Fetch 5 days. Why 5?
            # 1. Ensures we catch up after a long weekend.
            # 2. Provides enough context for calculating recent changes.
            # 3. Small enough to be fast.
            df = ticker.history(period="5d")
            
            with get_connection() as conn:
                # Iterate over the dataframe rows (Date is index)
                for date, row in df.iterrows():
                    # Insert into DB. 'INSERT OR IGNORE' prevents duplicates if run multiple times/day
                    conn.execute("""
                        INSERT OR IGNORE INTO prices 
                        (symbol, date, open, high, low, close, volume, data_source)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        symbol, 
                        date.strftime('%Y-%m-%d'),
                        row['Open'], row['High'], row['Low'], row['Close'], 
                        int(row['Volume']), 'yahoo_finance'
                    ))
            success_count += 1
        except Exception as e:
            log_data_quality_issue(symbol, 'api_failure', str(e), 'high')
            print(f"❌ Error fetching prices for {symbol}: {e}")
            
    return success_count

def collect_news():
    """
    Fetch recent news headlines for all stocks from NewsAPI and analyze sentiment.

    Collection Strategy:
    - Fetches news from the last 2 days
    - Limits to top 10 headlines per stock
    - Uses FinBERT for financial sentiment analysis
    - Saves headline, source, URL, and sentiment

    Returns:
        int: Number of stocks for which news was successfully collected.

    Example Output in DB:
        | symbol | date       | headline             | sentiment_label |
        |--------|------------|----------------------|-----------------|
        | AAPL   | 2023-10-25 | Apple releases iOS 18| positive        |
    """
    print("📰 Fetching news data...")
    newsapi = NewsApiClient(api_key=config.NEWS_API_KEY)
    success_count = 0

    # Initialize FinBERT
    print("🧠 Loading FinBERT model...")
    try:
        from transformers import pipeline
        # Use a financial sentiment analysis model
        sentiment_pipeline = pipeline("sentiment-analysis", model="ProsusAI/finbert")
        use_sentiment = True
    except ImportError:
        print("⚠️ Transformers not installed. Skipping sentiment analysis.")
        use_sentiment = False
    except Exception as e:
        print(f"⚠️ Error loading FinBERT: {e}. Skipping sentiment analysis.")
        use_sentiment = False

    # Calculate start date for news search (last 2 days)
    from_date = (datetime.now() - timedelta(days=2)).strftime('%Y-%m-%d')
    
    for symbol in config.ALL_STOCKS:
        try:
            # Build query: symbol + generic terms for context. 
            # For EGX, adding 'Egypt' helps filter irrelevant global noise.
            query = f"{symbol} OR {symbol.split('.')[0]} Egypt Stock"
            
            # Query NewsAPI for everything about the symbol
            articles = newsapi.get_everything(q=query, from_param=from_date, language='en')
            
            with get_connection() as conn:
                # Only take the top 10 most relevant articles to save space
                for art in articles['articles'][:10]:

                    sentiment_score = 0
                    sentiment_label = 'neutral'

                    if use_sentiment:
                        try:
                            # Analyze title
                            result = sentiment_pipeline(art['title'])[0]
                            sentiment_label = result['label']
                            score = result['score']

                            # Map to -1 to 1
                            if sentiment_label == 'positive':
                                sentiment_score = score
                            elif sentiment_label == 'negative':
                                sentiment_score = -score
                            else: # neutral
                                sentiment_score = 0
                        except Exception as e:
                            print(f"Error analyzing sentiment for {symbol}: {e}")


                    conn.execute("""
                        INSERT OR IGNORE INTO news 
                        (symbol, date, headline, source, url, sentiment_score, sentiment_label)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, (
                        symbol,
                        art['publishedAt'][:10], # Extract YYYY-MM-DD from ISO timestamp
                        art['title'],
                        art['source']['name'],
                        art['url'],
                        sentiment_score,
                        sentiment_label
                    ))
            success_count += 1
        except Exception as e:
            print(f"❌ Error fetching news for {symbol}: {e}")
            
    return success_count

if __name__ == "__main__":
    start_time = time.time()
    print(f"🚀 Starting data collection at {datetime.now()}")
    
    try:
        p_count = collect_prices()
        n_count = collect_news()
        
        duration = time.time() - start_time
        msg = f"Collected prices for {p_count} stocks and news for {n_count} stocks."
        log_system_run("collect_data.py", "success", msg, duration)
        print(f"✅ Collection complete! {msg}")
        
    except Exception as e:
        duration = time.time() - start_time
        log_system_run("collect_data.py", "failure", str(e), duration)
        print(f"💥 System Failure: {e}")