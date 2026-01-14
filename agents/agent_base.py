from abc import ABC, abstractmethod
import pandas as pd

class BaseAgent(ABC):
    def __init__(self, name):
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