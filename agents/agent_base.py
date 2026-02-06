from abc import ABC, abstractmethod
import pandas as pd
from typing import Optional, Dict, Any

class BaseAgent(ABC):
    """
    Abstract Base Class for all trading agents.

    All specific agent implementations (RSI, MovingAverage, etc.) must inherit from this
    class and implement the `predict` method.
    """
    def __init__(self, name):
        """
        Initialize the agent.

        Args:
            name (str): Unique name for the agent (used for logging and database).
        """
        self.name = name

    @abstractmethod
    def predict(self, data: pd.DataFrame, sentiment: Optional[Dict[str, Any]] = None):
        """
        Every agent must implement this method.

        Args:
            data: DataFrame with columns ['date', 'close', ...]
            sentiment: Optional dict with sentiment data:
                - avg_sentiment: float (-1 to 1)
                - sentiment_label: str ('Bullish', 'Neutral', 'Bearish')
                - article_count: int

        Returns:
            str: "UP", "DOWN", or "HOLD"
        """
        pass