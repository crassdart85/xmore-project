from abc import ABC, abstractmethod
import pandas as pd

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
    def predict(self, data: pd.DataFrame):
        """
        Every agent must implement this method.
        
        Args:
            data: DataFrame with columns ['date', 'close', ...]
            
        Returns:
            str: "UP", "DOWN", or "HOLD"
        """
        pass