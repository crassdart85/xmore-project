import pandas as pd
import numpy as np
import config
from database import get_connection
from features import add_technical_indicators, add_sentiment_features
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import TimeSeriesSplit
from sklearn.metrics import classification_report, accuracy_score
import joblib
import os

MODEL_PATH = 'models/stock_predictor.pkl'

def load_data():
    """Load all price and news data from DB"""
    print("📥 Loading data from database...")
    with get_connection() as conn:
        prices = pd.read_sql("SELECT * FROM prices ORDER BY date", conn)
        news = pd.read_sql("SELECT symbol, date, sentiment_score FROM news", conn)
    return prices, news

def prepare_dataset(prices, news):
    print("🛠️  Preparing dataset...")
    all_data = []
    
    for symbol in prices['symbol'].unique():
        # Filter for symbol
        p_df = prices[prices['symbol'] == symbol].copy()
        n_df = news[news['symbol'] == symbol].copy()
        
        if len(p_df) < 50: # Need enough data for indicators
            continue
            
        # Feature Engineering
        p_df = add_technical_indicators(p_df)
        p_df = add_sentiment_features(p_df, n_df)
        
        # Create Target (7 day horizon)
        # Classify: 2=UP, 0=DOWN, 1=FLAT
        horizon = config.PREDICTION_HORIZON_DAYS
        threshold = config.MIN_MOVE_THRESHOLD / 100
        
        p_df['Future_Close'] = p_df['close'].shift(-horizon)
        p_df['Pct_Change'] = (p_df['Future_Close'] - p_df['close']) / p_df['close']
        
        conditions = [
            (p_df['Pct_Change'] > threshold),
            (p_df['Pct_Change'] < -threshold)
        ]
        choices = [2, 0] # UP, DOWN
        p_df['Target'] = np.select(conditions, choices, default=1) # FLAT
        
        # Drop rows with NaN (due to indicators or shift)
        p_df = p_df.dropna()
        
        all_data.append(p_df)
    
    if not all_data:
        return pd.DataFrame()
        
    return pd.concat(all_data)

def train():
    prices, news = load_data()
    df = prepare_dataset(prices, news)
    
    if len(df) == 0:
        print("❌ Not enough data to train. Collect more data first.")
        return

    # Features to use
    features = ['open', 'high', 'low', 'close', 'volume', 
                'SMA_10', 'SMA_50', 'RSI', 'MACD', 'Signal_Line', 
                'BB_Upper', 'BB_Lower', 'Volatility', 'sentiment_score']
    
    X = df[features]
    y = df['Target']
    
    print(f"📊 Training on {len(X)} samples with {len(features)} features")
    
    # Time Series Split
    tscv = TimeSeriesSplit(n_splits=5)
    
    model = RandomForestClassifier(n_estimators=100, max_depth=10, random_state=42)
    
    fold = 1
    for train_index, test_index in tscv.split(X):
        X_train, X_test = X.iloc[train_index], X.iloc[test_index]
        y_train, y_test = y.iloc[train_index], y.iloc[test_index]
        
        model.fit(X_train, y_train)
        preds = model.predict(X_test)
        acc = accuracy_score(y_test, preds)
        print(f"  Fold {fold}: Accuracy = {acc:.2f}")
        fold += 1
    
    # Final training on all data
    print("🚀 Training final model on all data...")
    model.fit(X, y)
    
    # Save
    if not os.path.exists('models'):
        os.makedirs('models')
    joblib.dump(model, MODEL_PATH)
    print(f"✅ Model saved to {MODEL_PATH}")

if __name__ == "__main__":
    train()
