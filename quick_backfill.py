# quick_backfill.py
import yfinance as yf
from datetime import datetime, timedelta
import config
from database import get_connection

end_date = datetime.now()
start_date = end_date - timedelta(days=90)

with get_connection() as conn:
    for symbol in config.ALL_STOCKS:
        print(f"Fetching {symbol}...")
        ticker = yf.Ticker(symbol)
        df = ticker.history(start=start_date, end=end_date)
        
        for date, row in df.iterrows():
            conn.execute("""
                INSERT OR REPLACE INTO prices (symbol, date, close, volume)
                VALUES (?, ?, ?, ?)
            """, (symbol, date.strftime('%Y-%m-%d'), row['Close'], int(row['Volume'])))
        
        print(f"✅ {symbol}: {len(df)} days")

print("Done!")