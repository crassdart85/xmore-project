import pandas as pd
from datetime import datetime, timedelta
from database import get_connection
import config

def evaluate_predictions():
    """
    Check last week's predictions against actual price movements
    """
    print("🔍 Evaluating predictions...")
    
    today = datetime.now().strftime('%Y-%m-%d')
    
    with get_connection() as conn:
        # Get predictions that should be evaluated (target_date is today or earlier)
        query = """
            SELECT p.id, p.symbol, p.prediction_date, p.target_date, 
                   p.agent_name, p.prediction
            FROM predictions p
            LEFT JOIN evaluations e ON p.id = e.prediction_id
            WHERE e.id IS NULL 
            AND p.target_date <= ?
            ORDER BY p.target_date
        """
        
        cursor = conn.cursor()
        cursor.execute(query, (today,))
        predictions = cursor.fetchall()
        
        if len(predictions) == 0:
            print("✅ No predictions to evaluate yet (target dates are in the future)")
            return
        
        print(f"📊 Found {len(predictions)} predictions to evaluate")
        
        evaluated = 0
        
        for pred in predictions:
            pred_id = pred[0]
            symbol = pred[1]
            pred_date = pred[2]
            target_date = pred[3]
            agent_name = pred[4]
            prediction = pred[5]
            
            # Get price on prediction date
            cursor.execute("""
                SELECT close FROM prices 
                WHERE symbol = ? AND date <= ?
                ORDER BY date DESC LIMIT 1
            """, (symbol, pred_date))
            
            pred_price_row = cursor.fetchone()
            if not pred_price_row:
                print(f"⚠️  No price data for {symbol} on {pred_date}, skipping")
                continue
            
            pred_price = pred_price_row[0]
            
            # Get price on target date (or closest after)
            cursor.execute("""
                SELECT close, date FROM prices 
                WHERE symbol = ? AND date >= ?
                ORDER BY date ASC LIMIT 1
            """, (symbol, target_date))
            
            target_price_row = cursor.fetchone()
            if not target_price_row:
                print(f"⚠️  No price data for {symbol} on/after {target_date}, skipping")
                continue
            
            target_price = target_price_row[0]
            actual_date = target_price_row[1]
            
            # Calculate actual change
            actual_change_pct = ((target_price - pred_price) / pred_price) * 100
            
            # Determine actual outcome
            if actual_change_pct > config.MIN_MOVE_THRESHOLD:
                actual_outcome = "UP"
            elif actual_change_pct < -config.MIN_MOVE_THRESHOLD:
                actual_outcome = "DOWN"
            else:
                actual_outcome = "HOLD"
            
            # Check if prediction was correct
            was_correct = (prediction == actual_outcome)
            
            # Save evaluation
            cursor.execute("""
                INSERT INTO evaluations 
                (prediction_id, symbol, agent_name, prediction, actual_outcome, 
                 was_correct, actual_change_pct)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (pred_id, symbol, agent_name, prediction, actual_outcome, 
                  was_correct, actual_change_pct))
            
            status = "✅" if was_correct else "❌"
            print(f"{status} {symbol} ({agent_name}): Predicted {prediction}, "
                  f"Actual {actual_outcome} ({actual_change_pct:+.2f}%)")
            
            evaluated += 1
        
        print(f"\n✅ Evaluated {evaluated} predictions")
        
        # Show summary
        cursor.execute("""
            SELECT agent_name, 
                   COUNT(*) as total,
                   SUM(CASE WHEN was_correct = 1 THEN 1 ELSE 0 END) as correct,
                   ROUND(AVG(CASE WHEN was_correct = 1 THEN 1.0 ELSE 0.0 END) * 100, 1) as accuracy
            FROM evaluations
            GROUP BY agent_name
        """)
        
        summary = cursor.fetchall()
        
        if summary:
            print("\n📊 Performance Summary:")
            print("-" * 60)
            for row in summary:
                print(f"{row[0]}: {row[2]}/{row[1]} correct ({row[3]}% accuracy)")
            print("-" * 60)

if __name__ == "__main__":
    evaluate_predictions()