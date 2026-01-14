import pandas as pd
from agents.agent_base import BaseAgent
import config

class MAAgent(BaseAgent):
    def __init__(self, short_window=10, long_window=50):
        super().__init__("MA_Crossover_Agent")
        self.short_window = short_window
        self.long_window = long_window

    def predict(self, data: pd.DataFrame):
        if len(data) < self.long_window:
            return "HOLD"
        
        # Calculate moving averages
        data['ma_short'] = data['close'].rolling(window=self.short_window).mean()
        data['ma_long'] = data['close'].rolling(window=self.long_window).mean()
        
        # Get current and previous values
        current = data.iloc[-1]
        previous = data.iloc[-2]
        
        # Check for crossover
        if current['ma_short'] > current['ma_long'] and previous['ma_short'] <= previous['ma_long']:
            return "UP"  # Bullish crossover
        elif current['ma_short'] < current['ma_long'] and previous['ma_short'] >= previous['ma_long']:
            return "DOWN"  # Bearish crossover
        elif current['ma_short'] > current['ma_long']:
            return "UP"  # Still in uptrend
        else:
            return "DOWN"  # Still in downtrend