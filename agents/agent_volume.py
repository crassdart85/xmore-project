import pandas as pd
from agents.agent_base import BaseAgent
import config

class VolumeAgent(BaseAgent):
    """
    Volume Spike Agent.
    
    This agent generates signals based on unusual volume activity.
    High volume often precedes a significant price movement.
    
    Strategy:
    - Condition: Today's Volume > 1.5x Average Volume (20 days).
    - Signal UP (Buy): If price closed higher than yesterday (Green candle).
    - Signal DOWN (Sell): If price closed lower than yesterday (Red candle).
    - HOLD: Normal volume or flat price.
    """
    def __init__(self, volume_multiplier=1.5, avg_period=20):
        """
        Args:
            volume_multiplier (float): Factor to determine "high" volume (e.g., 1.5x).
            avg_period (int): Number of days for average volume calculation.
        """
        super().__init__("Volume_Spike_Agent")
        self.volume_multiplier = volume_multiplier
        self.avg_period = avg_period

    def predict(self, data: pd.DataFrame):
        """
        Analyze volume patterns to generate trading signals.
        
        Args:
            data (pd.DataFrame): DataFrame containing 'close' and 'volume'.
            
        Returns:
            str: "UP", "DOWN", or "HOLD".
            
        Example:
            >>> df = pd.DataFrame({'volume': [100, 100, ... 500], 'close': [10, ..., 11]})
            >>> signal = agent.predict(df)
            >>> print(signal)
            'UP'
        """
        # Need enough data for average calculation + 1 current day
        if len(data) < self.avg_period + 1:
            return "HOLD"
        
        # Calculate Average Volume (excluding today to avoid bias, or including - usually past 20)
        # We'll use the rolling mean of the *previous* 20 days to compare against *today*
        data['vol_avg'] = data['volume'].rolling(window=self.avg_period).mean().shift(1)
        
        current = data.iloc[-1]
        previous = data.iloc[-2]
        
        # Check if today's volume is significant
        if current['volume'] > (current['vol_avg'] * self.volume_multiplier):
            
            # Volume spike detected! Check price direction.
            if current['close'] > previous['close']:
                return "UP"  # High volume buying
            elif current['close'] < previous['close']:
                return "DOWN" # High volume selling
                
        return "HOLD"
