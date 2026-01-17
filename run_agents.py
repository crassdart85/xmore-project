import pandas as pd
from datetime import datetime, timedelta
import config
from database import get_connection
import sys
import traceback

# Import agents
try:
    from agents.agent_ml import MLAgent
    print("✅ ML Agent imported successfully")
except Exception as e:
    print(f"❌ Failed to import agents: {e}")
    traceback.print_exc()
    sys.exit(1)

def execute():
    try:
        print("🚀 Starting predictions...")
        
        # Create ML Agent
        # Note: You must run train_model.py first!
        ml_agent = MLAgent()
        agents = [ml_agent]
        
        print(f"✅ Created Agent: {ml_agent.name}")
        
        today = datetime.now().strftime('%Y-%m-%d')
        target = (datetime.now() + timedelta(days=7)).strftime('%Y-%m-%d')
        print(f"📅 Prediction date: {today}")
        print(f"🎯 Target date: {target}")
        print(f"📊 Processing {len(config.ALL_STOCKS)} stocks...")

        with get_connection() as conn:
            for stock in config.ALL_STOCKS:
                print(f"\n--- {stock} ---")
                
                # Fetch FULL price history for indicators (OHLCV)
                query = f"SELECT * FROM prices WHERE symbol='{stock}' ORDER BY date"
                df = pd.read_sql(query, conn)
                print(f"  Loaded {len(df)} price records")
                
                if len(df) < 50:
                    print(f"  ⚠️  Not enough data, skipping")
                    continue
                
                # Show recent prices
                recent = df.tail(3)
                print(f"  Recent Close: {recent['close'].values}")
                
                # Run agent
                for agent in agents:
                    signal = agent.predict(df)
                    
                    conn.execute("""
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