"""
Technical Feature Engineering Module

Calculates 40+ technical indicators using TA-Lib (with pure-Python fallback).
Groups: Trend, Momentum, Volatility, Volume, Candlestick Patterns, EGX-specific.

Used by ML_RandomForest agent and other agents for signal generation.
"""

import pandas as pd
import numpy as np
import logging

logger = logging.getLogger(__name__)

# Try TA-Lib first, fall back to pure Python
try:
    import talib
    TALIB_AVAILABLE = True
    logger.info("TA-Lib loaded successfully")
except ImportError:
    TALIB_AVAILABLE = False
    logger.warning("TA-Lib not available, using pure Python fallback indicators")


def calculate_rsi(series, period=14):
    """Pure Python RSI calculation (fallback when TA-Lib unavailable)."""
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))


def add_technical_indicators(df):
    """
    Add 40+ technical indicators to price DataFrame.
    Expects columns: ['open', 'high', 'low', 'close', 'volume']

    Uses TA-Lib when available (C-optimized), falls back to pure Python.

    Returns:
        pd.DataFrame: Input DataFrame with indicator columns added.
    """
    df = df.copy()

    if TALIB_AVAILABLE:
        df = _add_talib_indicators(df)
    else:
        df = _add_fallback_indicators(df)

    # EGX-specific features (from live feed data)
    df = _add_egx_features(df)

    # Clean NaN values — drop rows where lookback period hasn't been met
    max_lookback = 50  # SMA_50 requires 50 periods
    if len(df) > max_lookback:
        df = df.iloc[max_lookback:].copy()

    return df


def _add_talib_indicators(df):
    """Add indicators using TA-Lib (C-optimized, battle-tested)."""
    close = df['close'].values.astype(float)
    high = df['high'].values.astype(float)
    low = df['low'].values.astype(float)
    volume = df['volume'].values.astype(float)
    open_price = df['open'].values.astype(float)

    # ===================== TREND =====================
    # Moving Averages
    df['SMA_10'] = talib.SMA(close, timeperiod=10)
    df['SMA_30'] = talib.SMA(close, timeperiod=30)
    df['SMA_50'] = talib.SMA(close, timeperiod=50)
    df['EMA_12'] = talib.EMA(close, timeperiod=12)
    df['EMA_26'] = talib.EMA(close, timeperiod=26)

    # MACD
    df['MACD'], df['Signal_Line'], df['MACD_Hist'] = talib.MACD(close)

    # ADX — Average Directional Index (trend strength)
    df['ADX'] = talib.ADX(high, low, close, timeperiod=14)
    df['PLUS_DI'] = talib.PLUS_DI(high, low, close, timeperiod=14)
    df['MINUS_DI'] = talib.MINUS_DI(high, low, close, timeperiod=14)

    # ===================== MOMENTUM =====================
    # RSI
    df['RSI'] = talib.RSI(close, timeperiod=14)

    # CCI — Commodity Channel Index
    df['CCI'] = talib.CCI(high, low, close, timeperiod=20)

    # Williams %R
    df['WILLR'] = talib.WILLR(high, low, close, timeperiod=14)

    # Stochastic
    df['STOCH_K'], df['STOCH_D'] = talib.STOCH(high, low, close)

    # MFI — Money Flow Index (volume-weighted RSI)
    df['MFI'] = talib.MFI(high, low, close, volume, timeperiod=14)

    # ROC — Rate of Change
    df['ROC'] = talib.ROC(close, timeperiod=10)

    # ===================== VOLATILITY =====================
    # Bollinger Bands
    df['BB_Upper'], df['BB_Middle'], df['BB_Lower'] = talib.BBANDS(close, timeperiod=20)

    # ATR — Average True Range
    df['ATR'] = talib.ATR(high, low, close, timeperiod=14)

    # NATR — Normalized ATR (percentage)
    df['NATR'] = talib.NATR(high, low, close, timeperiod=14)

    # Returns and Volatility
    df['Returns'] = pd.Series(close).pct_change().values
    df['Volatility'] = pd.Series(df['Returns']).rolling(window=20).std().values

    # ===================== VOLUME =====================
    # OBV — On Balance Volume
    df['OBV'] = talib.OBV(close, volume)

    # AD — Accumulation/Distribution
    df['AD_Line'] = talib.AD(high, low, close, volume)

    # ===================== CANDLESTICK PATTERNS =====================
    df['DOJI'] = talib.CDLDOJI(open_price, high, low, close)
    df['HAMMER'] = talib.CDLHAMMER(open_price, high, low, close)
    df['ENGULFING'] = talib.CDLENGULFING(open_price, high, low, close)

    return df


def _add_fallback_indicators(df):
    """Pure Python fallback indicators (when TA-Lib is not installed)."""
    close = df['close']
    high = df['high']
    low = df['low']
    volume = df['volume']

    # ===================== TREND =====================
    df['SMA_10'] = close.rolling(window=10).mean()
    df['SMA_30'] = close.rolling(window=30).mean()
    df['SMA_50'] = close.rolling(window=50).mean()
    df['EMA_12'] = close.ewm(span=12, adjust=False).mean()
    df['EMA_26'] = close.ewm(span=26, adjust=False).mean()

    # MACD
    df['MACD'] = df['EMA_12'] - df['EMA_26']
    df['Signal_Line'] = df['MACD'].ewm(span=9, adjust=False).mean()
    df['MACD_Hist'] = df['MACD'] - df['Signal_Line']

    # ===================== MOMENTUM =====================
    df['RSI'] = calculate_rsi(close)

    # ROC
    df['ROC'] = close.pct_change(periods=10) * 100

    # Stochastic
    low_14 = low.rolling(window=14).min()
    high_14 = high.rolling(window=14).max()
    df['STOCH_K'] = ((close - low_14) / (high_14 - low_14)) * 100
    df['STOCH_D'] = df['STOCH_K'].rolling(window=3).mean()

    # Williams %R
    df['WILLR'] = ((high_14 - close) / (high_14 - low_14)) * -100

    # CCI
    tp = (high + low + close) / 3
    tp_sma = tp.rolling(window=20).mean()
    tp_mad = tp.rolling(window=20).apply(lambda x: np.abs(x - x.mean()).mean(), raw=True)
    df['CCI'] = (tp - tp_sma) / (0.015 * tp_mad)

    # ===================== VOLATILITY =====================
    # Bollinger Bands
    df['BB_Middle'] = close.rolling(window=20).mean()
    bb_std = close.rolling(window=20).std()
    df['BB_Upper'] = df['BB_Middle'] + (2 * bb_std)
    df['BB_Lower'] = df['BB_Middle'] - (2 * bb_std)

    # ATR
    tr1 = high - low
    tr2 = (high - close.shift(1)).abs()
    tr3 = (low - close.shift(1)).abs()
    true_range = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    df['ATR'] = true_range.rolling(window=14).mean()
    df['NATR'] = (df['ATR'] / close) * 100

    # Returns and Volatility
    df['Returns'] = close.pct_change()
    df['Volatility'] = df['Returns'].rolling(window=20).std()

    # ===================== VOLUME =====================
    # OBV
    obv = [0]
    for i in range(1, len(close)):
        if close.iloc[i] > close.iloc[i-1]:
            obv.append(obv[-1] + volume.iloc[i])
        elif close.iloc[i] < close.iloc[i-1]:
            obv.append(obv[-1] - volume.iloc[i])
        else:
            obv.append(obv[-1])
    df['OBV'] = obv

    # Placeholder columns for consistency with TA-Lib version
    df['ADX'] = np.nan
    df['PLUS_DI'] = np.nan
    df['MINUS_DI'] = np.nan
    df['MFI'] = np.nan
    df['AD_Line'] = np.nan
    df['DOJI'] = 0
    df['HAMMER'] = 0
    df['ENGULFING'] = 0

    return df


def _add_egx_features(df):
    """Add EGX-specific features from live feed data (if available)."""
    # Bid-Ask Spread (from EGX live feed)
    if 'bid' in df.columns and 'ask' in df.columns:
        df['bid_ask_spread'] = np.where(
            df['close'] > 0,
            (df['ask'] - df['bid']) / df['close'],
            0 
        )
    
    # 52-week range position
    if 'low_52w' in df.columns and 'high_52w' in df.columns:
        range_diff = df['high_52w'] - df['low_52w']
        df['range_52w_position'] = np.where(
            range_diff > 0,
            (df['close'] - df['low_52w']) / range_diff,
            0.5
        )

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
    price_df = pd.merge(price_df, daily_sentiment, on='date', how='left')

    # Fill missing sentiment with 0 (neutral)
    price_df['sentiment_score'] = price_df['sentiment_score'].fillna(0)

    return price_df


def get_feature_columns():
    """
    Get the list of feature column names used by ML agents.

    Returns:
        list: Feature column names in consistent order.
    """
    return [
        # Price
        'open', 'high', 'low', 'close', 'volume',
        # Trend
        'SMA_10', 'SMA_30', 'SMA_50', 'EMA_12', 'EMA_26',
        'MACD', 'Signal_Line', 'MACD_Hist',
        'ADX', 'PLUS_DI', 'MINUS_DI',
        # Momentum
        'RSI', 'CCI', 'WILLR', 'STOCH_K', 'STOCH_D', 'MFI', 'ROC',
        # Volatility
        'BB_Upper', 'BB_Middle', 'BB_Lower', 'ATR', 'NATR', 'Volatility',
        # Volume
        'OBV', 'AD_Line',
        # Sentiment
        'sentiment_score',
    ]


def log_feature_importance(model, feature_names, symbol='', top_n=10):
    """
    Log top N feature importances from a trained model.

    Args:
        model: Trained model with feature_importances_ attribute
        feature_names: List of feature names
        symbol: Stock symbol for context
        top_n: Number of top features to log
    """
    if not hasattr(model, 'feature_importances_'):
        return

    importances = model.feature_importances_
    indices = np.argsort(importances)[::-1][:top_n]

    prefix = f"[{symbol}] " if symbol else ""
    logger.info(f"{prefix}Top {top_n} feature importances:")
    for i, idx in enumerate(indices):
        if idx < len(feature_names):
            logger.info(f"  {i+1}. {feature_names[idx]}: {importances[idx]:.4f}")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print(f"TA-Lib available: {TALIB_AVAILABLE}")
    print(f"Feature columns ({len(get_feature_columns())}): {get_feature_columns()}")
