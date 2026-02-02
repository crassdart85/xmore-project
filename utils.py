import sqlite3
import config
from datetime import datetime, timedelta

def get_db_connection():
    """
    Get a connection to the SQLite database.
    row_factory is set to sqlite3.Row for dict-like access.
    """
    conn = sqlite3.connect(config.DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def calculate_outcome(start_price, end_price, prediction):
    """
    Determine if a prediction was correct based on price movement.
    
    Args:
        start_price (float): Price at prediction start.
        end_price (float): Price at target date.
        prediction (str): "UP", "DOWN", or "HOLD".
        
    Returns:
        tuple: (actual_outcome (str), was_correct (bool), pct_change (float))
    """
    if start_price == 0:
        return "UNKNOWN", False, 0.0
        
    pct_change = ((end_price - start_price) / start_price) * 100
    
    actual_outcome = "FLAT"
    if pct_change >= config.MIN_MOVE_THRESHOLD:
        actual_outcome = "UP"
    elif pct_change <= -config.MIN_MOVE_THRESHOLD:
        actual_outcome = "DOWN"
        
    was_correct = False
    if prediction == "HOLD":
        # Holding is correct if market was FLAT
        was_correct = (actual_outcome == "FLAT")
    else:
        was_correct = (prediction == actual_outcome)
        
    return actual_outcome, was_correct, pct_change

def get_target_lookback_date(days_ago=7):
    """
    Get a date string for 'days_ago'. 
    Ideally this would handle weekends, but for now simple subtraction.
    """
    return (datetime.now() - timedelta(days=days_ago)).strftime('%Y-%m-%d')
