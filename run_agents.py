import pandas as pd
from datetime import datetime, timedelta
import config
from database import get_connection
import sys
import traceback

# Import both agents
try:
    from agents.agent_rsi import RSIAgent
    from agents.agent_ma import MAAgent
    print("✅ Agents imported successfully")
except Exception as e:
    print(f"❌ Failed to import agents: {e}")
    traceback.print_exc()
    sys.exit(1)

def execute():
    try:
        print("🚀 Starting predictions...")
        
        # Create both agents
        rsi_agent = RSIAgent()
        ma_agent = MAAgent(short_window=10, long_window=50)
        agents = [rsi_agent, ma_agent]
        
        print(f"✅ Created {len(agents)} agents: {[a.name for a in agents]}")
        
        today = datetime.now().strftime('%Y-%m-%d')
        target = (datetime.now() + timedelta(days=7)).strftime('%Y-%m-%d')
        print(f"📅 Prediction date: {today}")
        print(f"🎯 Target date: {target}")
        print(f"📊 Processing {len(config.ALL_STOCKS)} stocks...")

        with get_connection() as conn:
            for stock in config.ALL_STOCKS:
                print(f"\n--- {stock} ---")
                
                query = f"SELECT date, close FROM prices WHERE symbol='{stock}' ORDER BY date"
                df = pd.read_sql(query, conn)
                print(f"  Loaded {len(df)} price records")
                
                if len(df) == 0:
                    print(f"  ⚠️  No data found, skipping")
                    continue
                
                # Show recent prices
                if len(df) >= 3:
                    recent = df.tail(3)
                    print(f"  Recent prices: {recent['close'].values}")
                
                # Run each agent
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