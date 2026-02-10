from abc import ABC, abstractmethod
import pandas as pd
from typing import Optional, Dict, Any
from datetime import datetime


class AgentSignal:
    """
    Standardized output from every signal agent.
    
    Contains the prediction, confidence score, and detailed reasoning
    data that explains WHY the agent made its prediction.
    Used by the Bull/Bear evaluators to build cases for/against signals.
    """
    def __init__(self, agent_name="", symbol="", prediction="HOLD",
                 confidence=0.0, reasoning=None):
        self.agent_name = agent_name
        self.symbol = symbol
        self.prediction = prediction      # "UP" | "DOWN" | "HOLD" | "FLAT"
        self.confidence = confidence       # 0-100
        self.reasoning = reasoning or {}   # Agent-specific data explaining WHY
        self.timestamp = datetime.utcnow().isoformat()

    def to_dict(self):
        """Convert to dictionary for storage and serialization."""
        return {
            "agent_name": self.agent_name,
            "symbol": self.symbol,
            "prediction": self.prediction,
            "confidence": round(self.confidence, 1),
            "reasoning": self.reasoning,
            "timestamp": self.timestamp
        }

    @staticmethod
    def from_dict(d):
        """Create AgentSignal from dictionary."""
        sig = AgentSignal(
            agent_name=d.get("agent_name", ""),
            symbol=d.get("symbol", ""),
            prediction=d.get("prediction", "HOLD"),
            confidence=d.get("confidence", 0.0),
            reasoning=d.get("reasoning", {})
        )
        sig.timestamp = d.get("timestamp", sig.timestamp)
        return sig


class BaseAgent(ABC):
    """
    Abstract Base Class for all trading agents.

    All specific agent implementations (RSI, MovingAverage, etc.) must inherit from this
    class and implement the `predict` method.
    
    Agents now return structured AgentSignal dicts with reasoning data
    for the Bull/Bear evaluators and Risk Agent.
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

    def predict_signal(self, data: pd.DataFrame, symbol: str = "",
                       sentiment: Optional[Dict[str, Any]] = None) -> dict:
        """
        Generate a structured prediction signal with reasoning.
        
        Default implementation wraps the legacy predict() method.
        Agents should override this to provide rich reasoning data.
        
        Args:
            data: DataFrame with price data
            symbol: Stock ticker symbol
            sentiment: Optional sentiment data dict
            
        Returns:
            dict: AgentSignal as dictionary with prediction + reasoning
        """
        prediction = self.predict(data, sentiment)
        signal = AgentSignal(
            agent_name=self.name,
            symbol=symbol,
            prediction=prediction,
            confidence=50.0,  # Default confidence when not computed
            reasoning={}
        )
        return signal.to_dict()