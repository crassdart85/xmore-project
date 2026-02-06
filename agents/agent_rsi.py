import pandas as pd
from typing import Optional, Dict, Any
from agents.agent_base import BaseAgent
import config

class RSIAgent(BaseAgent):
    """
    Relative Strength Index (RSI) Agent.

    This agent uses the RSI indicator to identify overbought and oversold conditions.
    Sentiment data is used to confirm or adjust signals when available.

    Strategy:
    - UP (Buy): RSI < 30 (Oversold), boosted by bullish sentiment.
    - DOWN (Sell): RSI > 70 (Overbought), boosted by bearish sentiment.
    - HOLD: RSI between 30 and 70, or conflicting signals.
    """
    def __init__(self):
        """Initialize RSI Agent with default name."""
        super().__init__(name="RSI_Agent")

    def calculate_rsi(self, data, window=14):
        """
        Calculate RSI values using Wilder's smoothing method.

        Args:
            data (pd.DataFrame): DataFrame with 'close' price column.
            window (int): Lookback period. Defaults to 14.

        Returns:
            pd.Series: RSI values.
        """
        delta = data['close'].diff()

        # Separate gains and losses
        gain = (delta.where(delta > 0, 0))
        loss = (-delta.where(delta < 0, 0))

        # Calculate smoothed averages (Wilder's method)
        avg_gain = gain.ewm(alpha=1/window, min_periods=window, adjust=False).mean()
        avg_loss = loss.ewm(alpha=1/window, min_periods=window, adjust=False).mean()

        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        return rsi

    def predict(self, data: pd.DataFrame, sentiment: Optional[Dict[str, Any]] = None):
        """
        Analyze price data and generate trading signal based on RSI thresholds.
        Sentiment is used as a confirmation signal when available.

        Args:
            data (pd.DataFrame): DataFrame containing 'close' price column.
            sentiment: Optional dict with sentiment data (avg_sentiment, sentiment_label)

        Returns:
            str: "UP", "DOWN", or "HOLD".
        """
        # We need at least 15 days of data to calculate a 14-day RSI
        if len(data) < config.RSI_PERIOD + 1:
            return "HOLD"

        rsi_values = self.calculate_rsi(data, window=config.RSI_PERIOD)
        current_rsi = rsi_values.iloc[-1]

        # Get base signal from RSI
        if current_rsi < config.RSI_OVERSOLD:
            base_signal = "UP"
        elif current_rsi > config.RSI_OVERBOUGHT:
            base_signal = "DOWN"
        else:
            base_signal = "HOLD"

        # If no sentiment data, return base signal
        if not sentiment or sentiment.get('article_count', 0) == 0:
            return base_signal

        # Use sentiment to confirm or adjust signal
        sentiment_label = sentiment.get('sentiment_label', 'Neutral')
        avg_sentiment = sentiment.get('avg_sentiment', 0)

        # Strong sentiment can push HOLD into a direction
        if base_signal == "HOLD":
            # Only act on strong sentiment (score > 0.3 or < -0.3)
            if avg_sentiment > 0.3:
                return "UP"
            elif avg_sentiment < -0.3:
                return "DOWN"
            return "HOLD"

        # Sentiment confirms or contradicts signal
        if base_signal == "UP":
            # Bullish sentiment confirms, bearish sentiment cancels
            if sentiment_label == "Bearish":
                return "HOLD"
            return "UP"

        if base_signal == "DOWN":
            # Bearish sentiment confirms, bullish sentiment cancels
            if sentiment_label == "Bullish":
                return "HOLD"
            return "DOWN"

        return base_signal
