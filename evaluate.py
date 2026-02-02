"""
Prediction Evaluation Module

This script checks past predictions against actual market outcomes to determine agent performance.
It populates the 'evaluations' table in the database.
"""
import pandas as pd
from datetime import datetime, timedelta
import config
from database import get_connection
import argparse

def evaluate_predictions():
    """
    Compare resolved predictions against actual stock price movements.
    
    Process:
    1. Identify predictions where the target_date has passed but no evaluation exists.
    2. Retrieve actual close prices for prediction_date and target_date.
    3. Calculate percentage change.
    4. Determine actual outcome (UP/DOWN/FLAT) based on MIN_MOVE_THRESHOLD.
    5. Compare prediction vs actual outcome.
    6. Store result in 'evaluations' table.
    
    Example Evaluation Logic:
    - User predicts "UP" for target date.
    - Start Price: $100, End Price: $101.
    - Change: +1%.
    - If MIN_MOVE_THRESHOLD is 0.5%, Actual Outcome is "UP".
    - Result: Correct (TRUE).
    """
    today = datetime.now().strftime('%Y-%m-%d')
    print(f"🧐 Evaluating predictions due by {today}...")

    with get_connection() as conn:
        # 1. Get predictions that haven't been evaluated yet
        # We join with evaluations to ensure we don't re-evaluate (e.id IS NULL)
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
            
            if not start_price_row:
                print(f"⚠️ Missing price data to evaluate {symbol} for {pred['prediction_date']}")
                continue
            if not end_price_row:
                # This could happen if it's a holiday or weekend. We might want to check data quality here.
                print(f"⚠️ Missing price data to evaluate {symbol} for {pred['target_date']}")
                continue
                
            start_price = start_price_row['close']
            end_price = end_price_row['close']
            
            # 3. Calculate actual change
            if start_price == 0: continue # Prevent division by zero
            pct_change = ((end_price - start_price) / start_price) * 100
            
            # 4. Determine outcome
            actual_outcome = "FLAT"
            if pct_change >= config.MIN_MOVE_THRESHOLD:
                actual_outcome = "UP"
            elif pct_change <= -config.MIN_MOVE_THRESHOLD:
                actual_outcome = "DOWN"
            
            # 5. Was it correct?
            predicted = pred['prediction']
            was_correct = False
            if predicted == "HOLD":
                # Holding is correct if flat, or strictly speaking if we just avoided a loss?
                # For simplicity, let's say HOLD is correct if "FLAT"
                was_correct = (actual_outcome == "FLAT")
            else:
                was_correct = (predicted == actual_outcome)
            
            # 6. Store evaluation
            conn.execute("""
                INSERT INTO evaluations 
                (prediction_id, symbol, agent_name, prediction, actual_outcome, was_correct, actual_change_pct)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (pred['id'], symbol, pred['agent_name'], predicted, actual_outcome, was_correct, pct_change))
            
            status_icon = "✅" if was_correct else "❌"
            print(f"{status_icon} Evaluated {symbol} ({pred['agent_name']}): Pred {predicted} vs Actual {actual_outcome} ({pct_change:.2f}%)")

def evaluate_lookback(days_ago=7):
    """
    Evaluate performance specifically for predictions that targeted a specific past date.
    Useful for "Weekly Review" style reporting.
    
    Args:
        days_ago (int): Number of days to look back for the TARGET date.
    """
    target_date = (datetime.now() - timedelta(days=days_ago)).strftime('%Y-%m-%d')
    print(f"\n📅 Look-back Analysis for Target Date: {target_date}")
    
    with get_connection() as conn:
        # Fetch evaluations that were aiming for this specific target date
        query = """
            SELECT e.*, p.prediction_date
            FROM evaluations e
            JOIN predictions p ON e.prediction_id = p.id
            WHERE p.target_date = ?
        """
        evals = pd.read_sql_query(query, conn, params=(target_date,))
        
        if len(evals) == 0:
            print(f"  No evaluations found targeting {target_date}")
            return

        total = len(evals)
        correct = evals['was_correct'].sum()
        accuracy = (correct / total) * 100
        
        print(f"  📊 Total Predictions: {total}")
        print(f"  🎯 Correct: {correct}")
        print(f"  📈 Accuracy: {accuracy:.1f}%")
        
        print("\n  Detailed Breakdown:")
        print(evals[['symbol', 'agent_name', 'prediction', 'actual_outcome', 'was_correct']].to_string(index=False))

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Evaluate Xmore2 Predictions')
    parser.add_argument('--lookback', action='store_true', help='Run look-back analysis for previous week')
    parser.add_argument('--days', type=int, default=7, help='Days ago for look-back (default: 7)')
    args = parser.parse_args()
    
    # Always run standard evaluation first to ensure latest data is processed
    evaluate_predictions()
    
    if args.lookback:
        evaluate_lookback(days_ago=args.days)