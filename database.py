"""
Database schema and management for Trading System
Creates tables, handles connections, provides helper functions
"""

import sqlite3
from datetime import datetime
import logging
from typing import Optional, List, Dict, Any
from contextlib import contextmanager

from config import DATABASE_PATH

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ============================================
# DATABASE CONNECTION
# ============================================

@contextmanager
def get_connection():
    """Context manager for database connections"""
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row  # Access columns by name
    try:
        yield conn
        conn.commit()
    except Exception as e:
        conn.rollback()
        logger.error(f"Database error: {e}")
        raise
    finally:
        conn.close()

# ============================================
# SCHEMA CREATION
# ============================================

def create_tables():
    """Create all database tables"""
    with get_connection() as conn:
        cursor = conn.cursor()
        
        # Table 1: Stock Prices
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS prices (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                date DATE NOT NULL,
                open REAL,
                high REAL,
                low REAL,
                close REAL NOT NULL,
                volume INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                data_source TEXT DEFAULT 'yahoo_finance',
                UNIQUE(symbol, date)
            )
        """)
        
        # Table 2: Financial News
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS news (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                date DATE NOT NULL,
                headline TEXT NOT NULL,
                source TEXT,
                url TEXT,
                sentiment_score REAL,  -- -1 to 1 (negative to positive)
                sentiment_label TEXT,  -- 'positive', 'negative', 'neutral'
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(symbol, headline, date)
            )
        """)
        
        # Table 3: Predictions
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS predictions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                prediction_date DATE NOT NULL,
                target_date DATE NOT NULL,  -- Date we're predicting for
                agent_name TEXT NOT NULL,
                prediction TEXT NOT NULL,  -- 'UP', 'DOWN', 'HOLD'
                confidence REAL,  -- 0 to 1
                predicted_change_pct REAL,  -- Optional: predicted % change
                metadata TEXT,  -- JSON string with additional info
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(symbol, prediction_date, target_date, agent_name)
            )
        """)
        
        # Table 4: Evaluations
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS evaluations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                prediction_id INTEGER NOT NULL,
                symbol TEXT NOT NULL,
                agent_name TEXT NOT NULL,
                prediction TEXT NOT NULL,
                actual_outcome TEXT,  -- 'UP', 'DOWN', 'FLAT'
                was_correct BOOLEAN,
                actual_change_pct REAL,
                prediction_error REAL,  -- If we predicted magnitude
                evaluated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (prediction_id) REFERENCES predictions(id)
            )
        """)
        
        # Table 5: Data Quality Log (for your failsafe!)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS data_quality_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date DATE NOT NULL,
                symbol TEXT NOT NULL,
                issue_type TEXT NOT NULL,  -- 'missing_data', 'api_failure', 'invalid_data'
                description TEXT,
                severity TEXT,  -- 'low', 'medium', 'high'
                resolved BOOLEAN DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Table 6: System Log (track script runs)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS system_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                script_name TEXT NOT NULL,
                status TEXT NOT NULL,  -- 'success', 'failure', 'partial'
                message TEXT,
                execution_time_seconds REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Create indexes for common queries
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_prices_symbol_date ON prices(symbol, date)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_news_symbol_date ON news(symbol, date)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_predictions_symbol ON predictions(symbol, prediction_date)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_predictions_date ON predictions(prediction_date)")
        
        logger.info("✅ Database tables created successfully")

# ============================================
# HELPER FUNCTIONS
# ============================================

def log_data_quality_issue(symbol: str, issue_type: str, description: str, severity: str = 'medium'):
    """Log data quality issues (your failsafe mechanism)"""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO data_quality_log (date, symbol, issue_type, description, severity)
            VALUES (DATE('now'), ?, ?, ?, ?)
        """, (symbol, issue_type, description, severity))
        logger.warning(f"⚠️  Data quality issue logged: {symbol} - {issue_type}")

def log_system_run(script_name: str, status: str, message: str = None, execution_time: float = None):
    """Log script execution"""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO system_log (script_name, status, message, execution_time_seconds)
            VALUES (?, ?, ?, ?)
        """, (script_name, status, message, execution_time))

def get_latest_price_date(symbol: str) -> Optional[str]:
    """Get the most recent date we have price data for a symbol"""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT MAX(date) as latest_date 
            FROM prices 
            WHERE symbol = ?
        """, (symbol,))
        result = cursor.fetchone()
        return result['latest_date'] if result else None

def check_missing_data(symbol: str, start_date: str, end_date: str) -> List[str]:
    """Check for missing dates in price data"""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT date FROM prices 
            WHERE symbol = ? AND date BETWEEN ? AND ?
            ORDER BY date
        """, (symbol, start_date, end_date))
        
        dates = [row['date'] for row in cursor.fetchall()]
        
        # Simple check: count business days vs actual days
        # (More sophisticated version would exclude weekends/holidays)
        expected_days = (datetime.fromisoformat(end_date) - datetime.fromisoformat(start_date)).days
        actual_days = len(dates)
        
        if actual_days < expected_days * 0.7:  # Missing more than 30% of days
            logger.warning(f"⚠️  {symbol}: Only {actual_days}/{expected_days} days of data")
        
        return dates

def get_recent_prices(symbol: str, days: int = 60) -> List[Dict[str, Any]]:
    """Get recent price data for a symbol"""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM prices 
            WHERE symbol = ?
            ORDER BY date DESC
            LIMIT ?
        """, (symbol, days))
        
        return [dict(row) for row in cursor.fetchall()]

def get_statistics() -> Dict[str, Any]:
    """Get database statistics"""
    with get_connection() as conn:
        cursor = conn.cursor()
        
        stats = {}
        
        # Count records in each table
        cursor.execute("SELECT COUNT(*) as count FROM prices")
        stats['total_prices'] = cursor.fetchone()['count']
        
        cursor.execute("SELECT COUNT(*) as count FROM news")
        stats['total_news'] = cursor.fetchone()['count']
        
        cursor.execute("SELECT COUNT(*) as count FROM predictions")
        stats['total_predictions'] = cursor.fetchone()['count']
        
        cursor.execute("SELECT COUNT(*) as count FROM evaluations")
        stats['total_evaluations'] = cursor.fetchone()['count']
        
        # Count stocks being tracked
        cursor.execute("SELECT COUNT(DISTINCT symbol) as count FROM prices")
        stats['stocks_tracked'] = cursor.fetchone()['count']
        
        # Date range
        cursor.execute("SELECT MIN(date) as earliest, MAX(date) as latest FROM prices")
        date_range = cursor.fetchone()
        stats['earliest_date'] = date_range['earliest']
        stats['latest_date'] = date_range['latest']
        
        # Recent data quality issues
        cursor.execute("""
            SELECT COUNT(*) as count 
            FROM data_quality_log 
            WHERE date >= DATE('now', '-7 days') AND resolved = 0
        """)
        stats['recent_issues'] = cursor.fetchone()['count']
        
        return stats

# ============================================
# DATABASE INITIALIZATION
# ============================================

def initialize_database():
    """Initialize database with all tables"""
    logger.info("🔧 Initializing database...")
    create_tables()
    
    # Display stats if database already has data
    stats = get_statistics()
    if stats['total_prices'] > 0:
        logger.info(f"📊 Database contains:")
        logger.info(f"   - {stats['total_prices']} price records")
        logger.info(f"   - {stats['total_news']} news articles")
        logger.info(f"   - {stats['total_predictions']} predictions")
        logger.info(f"   - {stats['stocks_tracked']} stocks tracked")
        logger.info(f"   - Date range: {stats['earliest_date']} to {stats['latest_date']}")
        
        if stats['recent_issues'] > 0:
            logger.warning(f"⚠️  {stats['recent_issues']} unresolved data quality issues in last 7 days")

# ============================================
# MAIN EXECUTION
# ============================================

if __name__ == "__main__":
    # When run directly, initialize database and show stats
    initialize_database()
    
    print("\n" + "="*60)
    print("Database initialized successfully!")
    print("="*60)
    
    stats = get_statistics()
    print(f"\n📊 Current Statistics:")
    for key, value in stats.items():
        print(f"  {key}: {value}")