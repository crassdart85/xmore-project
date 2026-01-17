import pandas as pd
import joblib
import os
from agents.agent_base import BaseAgent
from features import add_technical_indicators, add_sentiment_features
from database import get_connection

MODEL_PATH = 'models/stock_predictor.pkl'

class MLAgent(BaseAgent):
    def __init__(self):
        super().__init__("ML_RandomForest")
        self.model = None
        self.load_model()
        
    def load_model(self):
        if os.path.exists(MODEL_PATH):
            try:
                self.model = joblib.load(MODEL_PATH)
            except Exception as e:
                print(f"Error loading model: {e}")
        else:
            print(f"Warning: Model not found at {MODEL_PATH}. Prediction will fail.")

    def predict(self, price_df):
        """
        Predict using the pre-trained Random Forest model.
        Expects price_df to have full history for indicator calculation.
        Example Usage: agent.predict(historical_df)
        """
        if self.model is None:
            return "HOLD"
            
        # We need to fetch news to compute sentiment features for the current date
        # In a real system, we'd pass news_df in, or fetch it here.
        # Let's fetch the last few days of news for this symbol
        symbol = price_df.iloc[0]['symbol'] if 'symbol' in price_df.columns else None
        
        # 1. Feature Engineering
        df = price_df.copy()
        
        # If symbol is known, get news
        news_df = pd.DataFrame()
        if symbol:
            with get_connection() as conn:
                # Fetch recent news
                news_df = pd.read_sql(f"SELECT date, sentiment_score FROM news WHERE symbol='{symbol}'", conn)
        
        df = add_technical_indicators(df)
        df = add_sentiment_features(df, news_df)
        
        # Prepare features for the last row (presuming we predict for 'tomorrow' based on 'today')
        last_row = df.iloc[[-1]].copy()
        
        features = ['open', 'high', 'low', 'close', 'volume', 
                'SMA_10', 'SMA_50', 'RSI', 'MACD', 'Signal_Line', 
                'BB_Upper', 'BB_Lower', 'Volatility', 'sentiment_score']
        
        # Check for NaNs (e.g. if not enough history)
        if last_row[features].isnull().any().any():
            return "HOLD" # Not enough data
            
        # Predict
        X = last_row[features]
        prediction = self.model.predict(X)[0] # 0, 1, or 2
        
        # Get probability if possible
        probs = self.model.predict_proba(X)[0]
        confidence = max(probs)
        
        # Map back to strings
        # 0=DOWN, 1=FLAT, 2=UP
        mapping = {0: "DOWN", 1: "FLAT", 2: "UP"}
        return mapping.get(prediction, "HOLD")
