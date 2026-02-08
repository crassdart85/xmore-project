"""
Main Agent Execution Script

This script instantiates all available agents and runs them against recent price data
to generate predictions for the coming week.
"""
import os
import pandas as pd
from datetime import datetime, timedelta
import config
from database import get_connection
from sentiment import get_latest_sentiment
import sys
import traceback

# Import agents
try:
    from agents.agent_rsi import RSIAgent
    from agents.agent_ma import MAAgent
    from agents.agent_volume import VolumeAgent
    from agents.agent_ml import MLAgent
    print("✅ All agents imported successfully")
except Exception as e:
    print(f"❌ Failed to import agents: {e}")
    traceback.print_exc()
    sys.exit(1)

def execute():
    """
    Run all agents to generate predictions for all configured stocks.
    
    Workflow:
    1. Initialize agents (RSI, Moving Averages, Volume).
    2. Load historical price data for each stock.
    3. Generate signals using agent logic.
    4. Save predictions to the database.
    
    Raises:
        Exception: If any critical error occurs during execution.
        
    Example:
        >>> execute()
        # Output:
        # 🚀 Starting predictions...
        # ...
        # ✅ All predictions saved!
    """
    try:
        print("🚀 Starting predictions...")

        # Create all agents
        # 1. RSI Agent (Momentum)
        rsi_agent = RSIAgent()
        # 2. Moving Average Agent (Trend Following)
        ma_agent = MAAgent(short_window=10, long_window=50)
        # 3. Volume Agent (Activity Highs)
        vol_agent = VolumeAgent()
        # 4. ML Agent (Machine Learning)
        # Note: You must run train_model.py first!
        ml_agent = MLAgent()

        agents = [rsi_agent, ma_agent, vol_agent, ml_agent]

        print(f"✅ Created {len(agents)} agents")
        
        # Define prediction windows
        today = datetime.now().strftime('%Y-%m-%d')
        target = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d') # 1 day horizon for faster evaluation
        print(f"📅 Prediction date: {today}")
        print(f"🎯 Target date: {target}")
        print(f"📊 Processing {len(config.ALL_STOCKS)} stocks...")

        with get_connection() as conn:
            cursor = conn.cursor()
            for stock in config.ALL_STOCKS:
                print(f"\n--- {stock} ---")

                # Fetch FULL price history for indicators (OHLCV)
                if os.getenv('DATABASE_URL'):
                    cursor.execute("SELECT date, open, high, low, close, volume FROM prices WHERE symbol=%s ORDER BY date", (stock,))
                else:
                    cursor.execute("SELECT date, open, high, low, close, volume FROM prices WHERE symbol=? ORDER BY date", (stock,))

                rows = cursor.fetchall()
                if os.getenv('DATABASE_URL'):
                    # PostgreSQL with RealDictCursor returns dicts
                    df = pd.DataFrame(rows)
                else:
                    # SQLite returns tuples
                    df = pd.DataFrame(rows, columns=['date', 'open', 'high', 'low', 'close', 'volume'])

                print(f"  Loaded {len(df)} price records")
                
                if len(df) < 50:
                    print(f"  ⚠️  Not enough data, skipping")
                    continue
                
                # Show recent prices
                recent = df.tail(3)
                print(f"  Recent Close: {recent['close'].values}")

                # Fetch sentiment data for this stock
                sentiment = get_latest_sentiment(stock)
                if sentiment:
                    print(f"  Sentiment: {sentiment.get('sentiment_label', 'N/A')} ({sentiment.get('avg_sentiment', 0):.2f})")
                else:
                    print(f"  Sentiment: No data")

                # Run agents with sentiment
                cursor = conn.cursor()
                for agent in agents:
                    signal = agent.predict(df, sentiment=sentiment)

                    # Use PostgreSQL-compatible upsert when DATABASE_URL is set
                    if os.getenv('DATABASE_URL'):
                        cursor.execute("""
                            INSERT INTO predictions
                            (symbol, prediction_date, target_date, agent_name, prediction)
                            VALUES (%s, %s, %s, %s, %s)
                            ON CONFLICT (symbol, prediction_date, target_date, agent_name)
                            DO UPDATE SET prediction = EXCLUDED.prediction
                        """, (stock, today, target, agent.name, signal))
                    else:
                        cursor.execute("""
                            INSERT OR REPLACE INTO predictions
                            (symbol, prediction_date, target_date, agent_name, prediction)
                            VALUES (?, ?, ?, ?, ?)
                        """, (stock, today, target, agent.name, signal))

                    print(f"  🔮 {agent.name}: {signal}")
        
        print("\n✅ All predictions saved!")
        
    except Exception as e:
        print(f"\n❌ Error in execute(): {e}")
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    try:
        execute()
    except Exception as e:
        print(f"❌ Fatal error: {e}")
        traceback.print_exc()
        sys.exit(1)