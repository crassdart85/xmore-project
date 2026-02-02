import pandas as pd
from agents.agent_base import BaseAgent
import config

class MAAgent(BaseAgent):
    """
    Moving Average Crossover Agent.
    
    This agent generates signals based on the crossover of short-term and long-term
    moving averages (Golden Cross / Death Cross logic).
    
    Strategy:
    - UP (Buy): Short MA crosses above Long MA (Golden Cross) or Short > Long.
    - DOWN (Sell): Short MA crosses below Long MA (Death Cross) or Short < Long.
    - HOLD: Insufficient data.
    """
    def __init__(self, short_window=10, long_window=50):
        """
        Args:
            short_window (int): Period for short-term moving average.
            long_window (int): Period for long-term moving average.
        """
        super().__init__("MA_Crossover_Agent")
        self.short_window = short_window
        self.long_window = long_window

    def predict(self, data: pd.DataFrame):
        """
        Analyze price data and generate a trading signal.
        
        Args:
            data (pd.DataFrame): DataFrame containing 'close' price column.
            
        Returns:
            str: "UP", "DOWN", or "HOLD".
            
        Example:
            >>> df = pd.DataFrame({'close': [100, 102, 104, ...]})
            >>> signal = agent.predict(df)
            >>> print(signal)
            'UP'
        """
        if len(data) < self.long_window:
            return "HOLD"
        
        # Calculate moving averages
        data['ma_short'] = data['close'].rolling(window=self.short_window).mean()
        data['ma_long'] = data['close'].rolling(window=self.long_window).mean()
        
        # Get current and previous values
        current = data.iloc[-1]
        previous = data.iloc[-2]
        
        # Check for crossover
        # Condition 1: Golden Cross (Short crosses above Long) -> BUY (UP)
        if current['ma_short'] > current['ma_long'] and previous['ma_short'] <= previous['ma_long']:
            return "UP"  # Bullish crossover
            
        # Condition 2: Death Cross (Short crosses below Long) -> SELL (DOWN)
        elif current['ma_short'] < current['ma_long'] and previous['ma_short'] >= previous['ma_long']:
            return "DOWN"  # Bearish crossover
            
        # Condition 3: Trend Continuation
        elif current['ma_short'] > current['ma_long']:
            return "UP"  # Still in uptrend
        else:
            return "DOWN"  # Still in downtrend