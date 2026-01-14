import yfinance as yf
from newsapi import NewsApiClient
from datetime import datetime, timedelta
import time

# Import your existing logic
import config
from database import get_connection, log_system_run, log_data_quality_issue

def collect_prices():
    """Fetch stock prices from Yahoo Finance and save to DB"""
    print("📈 Fetching price data...")
    success_count = 0
    
    for symbol in config.ALL_STOCKS:
        try:
            # Download data
            ticker = yf.Ticker(symbol)
            # Fetch 5 days to ensure we cover weekends/holidays
            df = ticker.history(period="5d")
            
            with get_connection() as conn:
                for date, row in df.iterrows():
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
    """Fetch news headlines from NewsAPI"""
    print("📰 Fetching news data...")
    newsapi = NewsApiClient(api_key=config.NEWS_API_KEY)
    success_count = 0
    
    # We'll look for news from the last 2 days
    from_date = (datetime.now() - timedelta(days=2)).strftime('%Y-%m-%d')
    
    for symbol in config.ALL_STOCKS:
        try:
            articles = newsapi.get_everything(q=symbol, from_param=from_date, language='en')
            
            with get_connection() as conn:
                for art in articles['articles'][:10]: # Top 10 headlines per stock
                    conn.execute("""
                        INSERT OR IGNORE INTO news 
                        (symbol, date, headline, source, url)
                        VALUES (?, ?, ?, ?, ?)
                    """, (
                        symbol,
                        art['publishedAt'][:10], # Extract YYYY-MM-DD
                        art['title'],
                        art['source']['name'],
                        art['url']
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