import pandas as pd
from agents.agent_base import BaseAgent
import config

class RSIAgent(BaseAgent):
    """
    Relative Strength Index (RSI) Agent.
    
    This agent uses the RSI indicator to identify overbought and oversold conditions.
    
    Strategy:
    - UP (Buy): RSI < 30 (Oversold).
    - DOWN (Sell): RSI > 70 (Overbought).
    - HOLD: RSI between 30 and 70.
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
        """Standard RSI calculation using Pandas"""
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

    def predict(self, data: pd.DataFrame):
        """
        Analyze price data and generate trading signal based on RSI thresholds.
        
        Args:
            data (pd.DataFrame): DataFrame containing 'close' price column.
            
        Returns:
            str: "UP", "DOWN", or "HOLD".
            
        Example:
            >>> agent = RSIAgent()
            >>> signal = agent.predict(df)
            >>> print(signal)
            'DOWN'  # if RSI > 70
        """
        # We need at least 15 days of data to calculate a 14-day RSI
        if len(data) < config.RSI_PERIOD + 1:
            return "HOLD"
            
        rsi_values = self.calculate_rsi(data, window=config.RSI_PERIOD)
        current_rsi = rsi_values.iloc[-1]
        
        # Logic based on your config.py thresholds
        if current_rsi < config.RSI_OVERSOLD:
            # RSI < 30 indicates the asset is oversold and price may bounce up
            return "UP"
        elif current_rsi > config.RSI_OVERBOUGHT:
            # RSI > 70 indicates the asset is overbought and price may drop
            return "DOWN"
        else:
            return "HOLD"