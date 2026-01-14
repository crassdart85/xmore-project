import pandas as pd
from datetime import datetime
import config
from database import get_connection

def evaluate_predictions():
    today = datetime.now().strftime('%Y-%m-%d')
    print(f"🧐 Evaluating predictions due by {today}...")

    with get_connection() as conn:
        # 1. Get predictions that haven't been evaluated yet
        query = """
            SELECT p.* FROM predictions p
            LEFT JOIN evaluations e ON p.id = e.prediction_id
            WHERE p.target_date <= ? AND e.id IS NULL
        """
        predictions = pd.read_sql_query(query, conn, params=(today,))

        for _, pred in predictions.iterrows():
            symbol = pred['symbol']
            
            # 2. Get the actual prices for the start and end dates
            price_query = "SELECT close FROM prices WHERE symbol = ? AND date = ?"
            start_price_row = conn.execute(price_query, (symbol, pred['prediction_date'])).fetchone()
            end_price_row = conn.execute(price_query, (symbol, pred['target_date'])).fetchone()

            if not start_price_row or not end_price_row:
                print(f"⚠️ Missing price data to evaluate {symbol} for {pred['target_date']}")
                continue

            start_price = start_price_row['close']
            actual_end_price = end_price_row['close']
            
            # 3. Calculate actual movement
            pct_change = ((actual_end_price - start_price) / start_price) * 100
            
            # 4. Determine outcome
            if pct_change > config.MIN_MOVE_THRESHOLD:
                actual_outcome = 'UP'
            elif pct_change < -config.MIN_MOVE_THRESHOLD:
                actual_outcome = 'DOWN'
            else:
                actual_outcome = 'FLAT'

            was_correct = (pred['prediction'] == actual_outcome)

            # 5. Save evaluation
            conn.execute("""
                INSERT INTO evaluations 
                (prediction_id, symbol, agent_name, prediction, actual_outcome, was_correct, actual_change_pct)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (pred['id'], symbol, pred['agent_name'], pred['prediction'], actual_outcome, was_correct, pct_change))
            
            print(f"📊 {symbol}: Predicted {pred['prediction']}, Actual {actual_outcome} ({pct_change:.2f}%) -> {'✅' if was_correct else '❌'}")

if __name__ == "__main__":
    evaluate_predictions()