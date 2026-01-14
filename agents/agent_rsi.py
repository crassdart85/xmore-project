import pandas as pd
from agents.agent_base import BaseAgent
import config

class RSIAgent(BaseAgent):
    def __init__(self):
        super().__init__(name="RSI_Agent")

    def calculate_rsi(self, data, window=14):
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
        # We need at least 15 days of data to calculate a 14-day RSI
        if len(data) < config.RSI_PERIOD + 1:
            return "HOLD"
            
        rsi_values = self.calculate_rsi(data, window=config.RSI_PERIOD)
        current_rsi = rsi_values.iloc[-1]
        
        # Logic based on your config.py thresholds
        if current_rsi < config.RSI_OVERSOLD:
            return "UP"
        elif current_rsi > config.RSI_OVERBOUGHT:
            return "DOWN"
        else:
            return "HOLD"