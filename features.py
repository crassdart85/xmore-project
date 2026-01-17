import pandas as pd
import numpy as np

def calculate_rsi(series, period=14):
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def add_technical_indicators(df):
    """
    Add technical indicators to price DataFrame
    Expects columns: ['close', 'volume']
    """
    df = df.copy()
    
    # 1. Moving Averages
    df['SMA_10'] = df['close'].rolling(window=10).mean()
    df['SMA_50'] = df['close'].rolling(window=50).mean()
    
    # 2. RSI
    df['RSI'] = calculate_rsi(df['close'])
    
    # 3. MACD
    exp12 = df['close'].ewm(span=12, adjust=False).mean()
    exp26 = df['close'].ewm(span=26, adjust=False).mean()
    df['MACD'] = exp12 - exp26
    df['Signal_Line'] = df['MACD'].ewm(span=9, adjust=False).mean()
    
    # 4. Bollinger Bands (20, 2)
    df['BB_Middle'] = df['close'].rolling(window=20).mean()
    df['BB_Std'] = df['close'].rolling(window=20).std()
    df['BB_Upper'] = df['BB_Middle'] + (2 * df['BB_Std'])
    df['BB_Lower'] = df['BB_Middle'] - (2 * df['BB_Std'])
    
    # 5. Volatility (Returns Std Dev)
    df['Returns'] = df['close'].pct_change()
    df['Volatility'] = df['Returns'].rolling(window=20).std()
    
    return df

def add_sentiment_features(price_df, news_df):
    """
    Merge daily sentiment into price DataFrame.
    news_df should have ['date', 'sentiment_score']
    """
    if news_df is None or len(news_df) == 0:
        price_df['sentiment_score'] = 0
        return price_df
        
    # Group news by date
    daily_sentiment = news_df.groupby('date')['sentiment_score'].mean().reset_index()
    
    # Merge
    # Ensure date formats match (assuming YYYY-MM-DD strings)
    price_df = pd.merge(price_df, daily_sentiment, on='date', how='left')
    
    # Fill missing sentiment with 0 (neutral) or forward fill
    price_df['sentiment_score'] = price_df['sentiment_score'].fillna(0)
    
    return price_df
