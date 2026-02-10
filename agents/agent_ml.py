"""
ML Random Forest Agent

Uses scikit-learn Random Forest classifier with 40+ TA-Lib technical indicators.
Implements walk-forward validation (TimeSeriesSplit) to prevent look-ahead bias.
Logs feature importance rankings for explainability.
"""

import pandas as pd
import numpy as np
import joblib
import os
import logging
from typing import Optional, Dict, Any

from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import TimeSeriesSplit

from agents.agent_base import BaseAgent
from features import add_technical_indicators, add_sentiment_features, get_feature_columns, log_feature_importance
from database import get_connection

logger = logging.getLogger(__name__)

MODEL_DIR = 'models'
MODEL_PATH = os.path.join(MODEL_DIR, 'stock_predictor.pkl')

# Prediction return thresholds
UP_THRESHOLD = 0.005   # +0.5% = UP
DOWN_THRESHOLD = -0.005 # -0.5% = DOWN


class MLAgent(BaseAgent):
    def __init__(self):
        super().__init__("ML_RandomForest")
        self.model = None
        self.feature_names = None
        self.load_model()
        
    def load_model(self):
        """Load pre-trained model if it exists."""
        if os.path.exists(MODEL_PATH):
            try:
                data = joblib.load(MODEL_PATH)
                if isinstance(data, dict):
                    self.model = data.get('model')
                    self.feature_names = data.get('feature_names', get_feature_columns())
                else:
                    self.model = data
                    self.feature_names = get_feature_columns()
                logger.info(f"Model loaded from {MODEL_PATH}")
            except Exception as e:
                logger.error(f"Error loading model: {e}")
        else:
            logger.warning(f"Model not found at {MODEL_PATH}. Will train on-the-fly.")

    def save_model(self, model, feature_names):
        """Save trained model with feature names."""
        os.makedirs(MODEL_DIR, exist_ok=True)
        data = {'model': model, 'feature_names': feature_names}
        joblib.dump(data, MODEL_PATH)
        logger.info(f"Model saved to {MODEL_PATH}")

    def predict(self, price_df, sentiment: Optional[Dict[str, Any]] = None):
        """
        Predict using the Random Forest model.
        Expects price_df to have full history for indicator calculation.
        
        If no pre-trained model exists, trains on available data using
        walk-forward validation (TimeSeriesSplit).
        """
        symbol = price_df.iloc[0]['symbol'] if 'symbol' in price_df.columns else 'UNKNOWN'
        
        # 1. Feature Engineering
        df = price_df.copy()
        
        # Get news sentiment if available
        news_df = pd.DataFrame()
        if symbol and symbol != 'UNKNOWN':
            try:
                with get_connection() as conn:
                    news_df = pd.read_sql(
                        f"SELECT date, sentiment_score FROM news WHERE symbol='{symbol}'", 
                        conn
                    )
            except Exception:
                pass
        
        df = add_technical_indicators(df)
        df = add_sentiment_features(df, news_df)
        
        # 2. Determine available features (handle missing columns gracefully)
        all_features = get_feature_columns()
        available_features = [f for f in all_features if f in df.columns and not df[f].isna().all()]
        
        if len(available_features) < 5:
            logger.warning(f"[{symbol}] Only {len(available_features)} features available, using HOLD")
            return "HOLD"
        
        # 3. If no model, try to train one
        if self.model is None:
            self.model, self.feature_names = self._train_model(df, available_features, symbol)
        
        if self.model is None:
            return "HOLD"  # Not enough data to train
        
        # 4. Use matched features (model was trained on specific features)
        features = [f for f in self.feature_names if f in df.columns]
        if len(features) < len(self.feature_names) * 0.5:
            logger.warning(f"[{symbol}] Too many features missing, retraining...")
            self.model, self.feature_names = self._train_model(df, available_features, symbol)
            features = available_features
        
        if self.model is None:
            return "HOLD"
        
        # 5. Predict on last row
        last_row = df.iloc[[-1]].copy()
        
        # Fill NaNs with 0 for the last row
        for feat in features:
            if feat in last_row.columns and last_row[feat].isna().any():
                last_row[feat] = 0
        
        try:
            X = last_row[features]
            prediction = self.model.predict(X)[0]
            
            # Get probability
            probs = self.model.predict_proba(X)[0]
            confidence = max(probs)
            
            # Map to strings: 0=DOWN, 1=FLAT, 2=UP
            mapping = {0: "DOWN", 1: "FLAT", 2: "UP"}
            result = mapping.get(prediction, "HOLD")
            
            logger.info(f"[{symbol}] Prediction: {result} (confidence: {confidence:.2f})")
            return result
            
        except Exception as e:
            logger.error(f"[{symbol}] Prediction error: {e}")
            return "HOLD"

    def _train_model(self, df, features, symbol=''):
        """
        Train Random Forest with walk-forward validation (TimeSeriesSplit).
        
        Args:
            df: DataFrame with technical indicators already added
            features: List of feature column names to use
            symbol: Stock symbol for logging
            
        Returns:
            tuple: (trained_model, feature_names) or (None, None) if not enough data
        """
        # Create target: 5-day forward return classification
        df = df.copy()
        df['future_return'] = df['close'].shift(-5) / df['close'] - 1
        df['target'] = df['future_return'].apply(
            lambda x: 2 if x > UP_THRESHOLD else (0 if x < DOWN_THRESHOLD else 1)
        )
        
        # Drop rows with NaN target (last 5 rows) or NaN features
        train_df = df.dropna(subset=['target'] + features).copy()
        
        if len(train_df) < 30:
            logger.warning(f"[{symbol}] Not enough data to train ({len(train_df)} rows)")
            return None, None
        
        X = train_df[features]
        y = train_df['target'].astype(int)
        
        # Walk-forward validation using TimeSeriesSplit
        n_splits = min(5, len(X) // 10)
        if n_splits < 2:
            n_splits = 2
            
        tscv = TimeSeriesSplit(n_splits=n_splits)
        scores = []
        
        best_model = None
        best_score = 0
        
        for train_idx, test_idx in tscv.split(X):
            X_train, X_test = X.iloc[train_idx], X.iloc[test_idx]
            y_train, y_test = y.iloc[train_idx], y.iloc[test_idx]
            
            model = RandomForestClassifier(
                n_estimators=100,
                max_depth=10,
                min_samples_split=5,
                min_samples_leaf=2,
                random_state=42,
                n_jobs=-1
            )
            model.fit(X_train, y_train)
            score = model.score(X_test, y_test)
            scores.append(score)
            
            if score > best_score:
                best_score = score
                best_model = model
        
        avg_score = np.mean(scores)
        logger.info(f"[{symbol}] Walk-forward validation: avg accuracy = {avg_score:.3f} (splits={n_splits})")
        
        # Log feature importance
        if best_model:
            log_feature_importance(best_model, features, symbol=symbol, top_n=10)
            # Save the model
            self.save_model(best_model, features)
        
        return best_model, features
