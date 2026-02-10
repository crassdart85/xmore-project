"""
Database schema and management for Trading System.

This module handles all database interactions including:
- Connection management via context managers
- Schema creation and initialization
- Data logging (prices, news, predictions, evaluations)
- Statistics and reporting
"""

import os
import sqlite3
from datetime import datetime
import logging
from typing import Optional, List, Dict, Any
from contextlib import contextmanager

from config import DATABASE_PATH

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Use PostgreSQL on Render, SQLite locally
DATABASE_URL = os.getenv('DATABASE_URL')

# ============================================
# DATABASE CONNECTION
# ============================================

def _adapt_sql(sql):
    """Convert SQLite-style ? placeholders to PostgreSQL-style %s when using PostgreSQL."""
    if DATABASE_URL:
        return sql.replace('?', '%s')
    return sql

@contextmanager
def get_connection():
    """
    Context manager for database connections.
    Uses PostgreSQL when DATABASE_URL is set (production/Render),
    falls back to SQLite locally.

    Yields:
        Connection object with dict-like row access.

    Raises:
        Exception: Rolls back transaction and re-raises any database errors.

    Example:
        >>> with get_connection() as conn:
        >>>     rows = conn.execute("SELECT * FROM prices").fetchall()
    """
    if DATABASE_URL:
        # Production: PostgreSQL
        import psycopg2
        import psycopg2.extras
        conn = psycopg2.connect(DATABASE_URL)
        conn.cursor_factory = psycopg2.extras.RealDictCursor
    else:
        # Local: SQLite
        conn = sqlite3.connect(DATABASE_PATH)
        conn.row_factory = sqlite3.Row  # Access columns by name: row['column']

    try:
        yield conn
        conn.commit()  # Auto-commit if no errors
    except Exception as e:
        conn.rollback()  # Auto-rollback on error
        logger.error(f"Database error: {e}")
        raise
    finally:
        conn.close()  # Ensure connection is closed to prevent leaks

# ============================================
# SCHEMA CREATION
# ============================================

def create_tables():
    """
    Create all necessary database tables if they don't exist.

    Tables created:
    - prices: Historical stock data
    - news: Financial news articles and sentiment
    - predictions: Agent predictions
    - evaluations: Accuracy tracking of predictions
    - data_quality_log: Logs for data issues (missing data, API errors)
    - system_log: Logs for script execution runs
    """
    # Use different SQL syntax for PostgreSQL vs SQLite
    if DATABASE_URL:
        auto_id = "SERIAL PRIMARY KEY"
        bool_default = "BOOLEAN DEFAULT FALSE"
    else:
        auto_id = "INTEGER PRIMARY KEY AUTOINCREMENT"
        bool_default = "BOOLEAN DEFAULT 0"

    with get_connection() as conn:
        cursor = conn.cursor()

        # Table 1: Stock Prices
        cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS prices (
                id {auto_id},
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
        cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS news (
                id {auto_id},
                symbol TEXT NOT NULL,
                date DATE NOT NULL,
                headline TEXT NOT NULL,
                source TEXT,
                url TEXT,
                sentiment_score REAL,
                sentiment_label TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(symbol, headline, date)
            )
        """)

        # Table 3: Predictions
        cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS predictions (
                id {auto_id},
                symbol TEXT NOT NULL,
                prediction_date DATE NOT NULL,
                target_date DATE NOT NULL,
                agent_name TEXT NOT NULL,
                prediction TEXT NOT NULL,
                confidence REAL,
                predicted_change_pct REAL,
                metadata TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(symbol, prediction_date, target_date, agent_name)
            )
        """)

        # Table 4: Evaluations
        cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS evaluations (
                id {auto_id},
                prediction_id INTEGER NOT NULL,
                symbol TEXT NOT NULL,
                agent_name TEXT NOT NULL,
                prediction TEXT NOT NULL,
                actual_outcome TEXT,
                was_correct BOOLEAN,
                actual_change_pct REAL,
                prediction_error REAL,
                evaluated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (prediction_id) REFERENCES predictions(id)
            )
        """)

        # Table 5: Data Quality Log
        cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS data_quality_log (
                id {auto_id},
                date DATE NOT NULL,
                symbol TEXT NOT NULL,
                issue_type TEXT NOT NULL,
                description TEXT,
                severity TEXT,
                resolved {bool_default},
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Table 6: System Log
        cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS system_log (
                id {auto_id},
                script_name TEXT NOT NULL,
                status TEXT NOT NULL,
                message TEXT,
                execution_time_seconds REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Table 7: Consensus Results (3-Layer Pipeline Output)
        cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS consensus_results (
                id {auto_id},
                symbol TEXT NOT NULL,
                prediction_date DATE NOT NULL,
                
                -- Final output
                final_signal TEXT NOT NULL,
                conviction TEXT,
                confidence REAL,
                risk_adjusted {bool_default},
                
                -- Agreement
                agent_agreement REAL,
                agents_agreeing INTEGER,
                agents_total INTEGER,
                majority_direction TEXT,
                
                -- Bull / Bear scores
                bull_score INTEGER,
                bear_score INTEGER,
                
                -- Risk
                risk_action TEXT,
                risk_score INTEGER,
                
                -- Full data (JSON)
                bull_case_json TEXT,
                bear_case_json TEXT,
                risk_assessment_json TEXT,
                agent_signals_json TEXT,
                reasoning_chain_json TEXT,
                display_json TEXT,
                
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(symbol, prediction_date)
            )
        """)

        # Add reasoning column to predictions if it doesn't exist
        try:
            cursor.execute("ALTER TABLE predictions ADD COLUMN reasoning TEXT")
        except Exception:
            pass  # Column already exists

        # Table 8: Users (Auth)
        cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS users (
                id {auto_id},
                email TEXT NOT NULL,
                email_lower TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                display_name TEXT,
                preferred_language TEXT DEFAULT 'en',
                is_active {bool_default},
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_login_at TIMESTAMP
            )
        """)

        # Table 9: EGX 30 Stocks Reference
        cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS egx30_stocks (
                id {auto_id},
                symbol TEXT NOT NULL UNIQUE,
                name_en TEXT NOT NULL,
                name_ar TEXT NOT NULL,
                sector_en TEXT,
                sector_ar TEXT,
                is_active {bool_default},
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Table 10: User Watchlist
        cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS user_watchlist (
                id {auto_id},
                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                stock_id INTEGER NOT NULL REFERENCES egx30_stocks(id) ON DELETE CASCADE,
                added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id, stock_id)
            )
        """)

        # Table 12: User Positions (Virtual Portfolio)
        cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS user_positions (
                id {auto_id},
                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                symbol TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'OPEN',
                entry_date DATE NOT NULL,
                entry_price REAL,
                exit_date DATE,
                exit_price REAL,
                return_pct REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        # Partial index for unique OPEN position
        if DATABASE_URL:
            cursor.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_unique_open_position ON user_positions(user_id, symbol) WHERE status = 'OPEN'")
        else:
            # SQLite doesn't strictly support WHERE in unique index in older versions easily via standard SQL, 
            # but we can enforce logic in app or use a trigger. For now, we'll skip the partial index in SQLite or just rely on app logic.
            # Actually SQLite supports partial indexes since 3.8.0.
            cursor.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_unique_open_position ON user_positions(user_id, symbol) WHERE status = 'OPEN'")

        cursor.execute("CREATE INDEX IF NOT EXISTS idx_positions_user ON user_positions(user_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_positions_status ON user_positions(status)")

        # Table 13: Trade Recommendations
        cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS trade_recommendations (
                id {auto_id},
                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                symbol TEXT NOT NULL,
                recommendation_date DATE NOT NULL,
                
                action TEXT NOT NULL,
                signal TEXT NOT NULL,
                confidence INTEGER NOT NULL,
                conviction TEXT,
                risk_action TEXT,
                priority REAL,
                
                close_price REAL,
                stop_loss_pct REAL,
                target_pct REAL,
                stop_loss_price REAL,
                target_price REAL,
                risk_reward_ratio REAL,
                
                reasons TEXT,
                reasons_ar TEXT,
                
                bull_score INTEGER,
                bear_score INTEGER,
                agents_agreeing INTEGER,
                agents_total INTEGER,
                risk_flags TEXT,
                
                actual_next_day_return REAL,
                actual_5day_return REAL,
                was_correct {bool_default},
                
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                
                UNIQUE(user_id, symbol, recommendation_date)
            )
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_trade_rec_user_date ON trade_recommendations(user_id, recommendation_date DESC)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_trade_rec_date ON trade_recommendations(recommendation_date DESC)")

        # Table 11: Sentiment Scores (Aggregated)
        cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS sentiment_scores (
                id {auto_id},
                symbol TEXT NOT NULL,
                date DATE NOT NULL,
                avg_sentiment REAL,
                sentiment_label TEXT,
                article_count INTEGER DEFAULT 0,
                positive_count INTEGER DEFAULT 0,
                negative_count INTEGER DEFAULT 0,
                neutral_count INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(symbol, date)
            )
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_sentiment_symbol_date ON sentiment_scores(symbol, date)")

        # Seed EGX 30 stocks (insert or ignore for SQLite)
        egx30_stocks = [
            ('COMI.CA', 'Commercial International Bank', 'البنك التجاري الدولي', 'Banking', 'البنوك'),
            ('HRHO.CA', 'Hermes Holding', 'القابضة المصرية الكويتية (هيرميس)', 'Financial Services', 'الخدمات المالية'),
            ('TMGH.CA', 'Talaat Moustafa Group', 'مجموعة طلعت مصطفى', 'Real Estate', 'العقارات'),
            ('SWDY.CA', 'Elsewedy Electric', 'السويدي إليكتريك', 'Industrials', 'الصناعات'),
            ('EAST.CA', 'Eastern Company', 'الشرقية (إيسترن كومباني)', 'Consumer Staples', 'السلع الأساسية'),
            ('ETEL.CA', 'Telecom Egypt', 'المصرية للاتصالات', 'Telecom', 'الاتصالات'),
            ('ABUK.CA', 'Abu Qir Fertilizers', 'أبو قير للأسمدة', 'Materials', 'المواد'),
            ('ORWE.CA', 'Oriental Weavers', 'السجاد الشرقية (أوريانتال ويفرز)', 'Consumer Discretionary', 'السلع الاستهلاكية'),
            ('EFIH.CA', 'EFG Hermes', 'إي إف جي هيرميس', 'Financial Services', 'الخدمات المالية'),
            ('OCDI.CA', 'Orascom Development', 'أوراسكوم للتنمية', 'Real Estate', 'العقارات'),
            ('PHDC.CA', 'Palm Hills Development', 'بالم هيلز للتعمير', 'Real Estate', 'العقارات'),
            ('MNHD.CA', 'Madinet Nasr Housing', 'مدينة نصر للإسكان', 'Real Estate', 'العقارات'),
            ('CLHO.CA', 'Cleopatra Hospital', 'مستشفى كليوباترا', 'Healthcare', 'الرعاية الصحية'),
            ('EKHO.CA', 'Ezz Steel', 'حديد عز', 'Materials', 'المواد'),
            ('AMOC.CA', 'Alexandria Mineral Oils', 'الإسكندرية للزيوت المعدنية', 'Energy', 'الطاقة'),
            ('ESRS.CA', 'Ezz Steel (Rebars)', 'عز الدخيلة للصلب', 'Materials', 'المواد'),
            ('HELI.CA', 'Heliopolis Housing', 'مصر الجديدة للإسكان', 'Real Estate', 'العقارات'),
            ('GBCO.CA', 'GB Auto', 'جي بي أوتو', 'Consumer Discretionary', 'السلع الاستهلاكية'),
            ('CCAP.CA', 'Citadel Capital (Qalaa)', 'القلعة (سيتاديل كابيتال)', 'Financial Services', 'الخدمات المالية'),
            ('JUFO.CA', 'Juhayna Food', 'جهينة', 'Consumer Staples', 'السلع الأساسية'),
            ('SKPC.CA', 'Sidi Kerir Petrochemicals', 'سيدي كرير للبتروكيماويات', 'Materials', 'المواد'),
            ('ORAS.CA', 'Orascom Construction', 'أوراسكوم للإنشاءات', 'Industrials', 'الصناعات'),
            ('FWRY.CA', 'Fawry', 'فوري', 'Technology', 'التكنولوجيا'),
            ('EKHOA.CA', 'Ezz Aldekhela', 'عز الدخيلة', 'Materials', 'المواد'),
            ('BINV.CA', 'Beltone Financial', 'بلتون المالية القابضة', 'Financial Services', 'الخدمات المالية'),
            ('EIOD.CA', 'E-Finance', 'إي فاينانس', 'Technology', 'التكنولوجيا'),
            ('TALM.CA', 'Talem Medical', 'تاليم الطبية', 'Healthcare', 'الرعاية الصحية'),
            ('ADIB.CA', 'Abu Dhabi Islamic Bank Egypt', 'مصرف أبوظبي الإسلامي – مصر', 'Banking', 'البنوك'),
            ('DMCR.CA', 'Dice Medical & Scientific', 'دايس الطبية والعلمية', 'Healthcare', 'الرعاية الصحية'),
            ('ASCM.CA', 'Arabian Cement', 'الأسمنت العربية', 'Materials', 'المواد'),
        ]
        for stock in egx30_stocks:
            cursor.execute("""
                INSERT OR IGNORE INTO egx30_stocks (symbol, name_en, name_ar, sector_en, sector_ar)
                VALUES (?, ?, ?, ?, ?)
            """, stock)

        # Create indexes for common queries
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_prices_symbol_date ON prices(symbol, date)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_news_symbol_date ON news(symbol, date)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_predictions_symbol ON predictions(symbol, prediction_date)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_predictions_date ON predictions(prediction_date)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_consensus_symbol ON consensus_results(symbol, prediction_date)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_consensus_date ON consensus_results(prediction_date)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_users_email_lower ON users(email_lower)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_watchlist_user ON user_watchlist(user_id)")

        logger.info("✅ Database tables created successfully")

# ============================================
# HELPER FUNCTIONS
# ============================================

def log_data_quality_issue(symbol: str, issue_type: str, description: str, severity: str = 'medium'):
    """
    Log data quality issues to the database.
    
    Args:
        symbol (str): Stock symbol related to the issue.
        issue_type (str): Category of issue (e.g., 'missing_data', 'api_failure').
        description (str): Detailed description of the problem.
        severity (str): 'low', 'medium', or 'high'. Defaults to 'medium'.
    
    Example:
        >>> log_data_quality_issue('AAPL', 'missing_data', 'No close price for 2023-10-25')
    """
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(_adapt_sql("""
            INSERT INTO data_quality_log (date, symbol, issue_type, description, severity)
            VALUES (CURRENT_DATE, ?, ?, ?, ?)
        """), (symbol, issue_type, description, severity))
        logger.warning(f"⚠️  Data quality issue logged: {symbol} - {issue_type}")

def log_system_run(script_name: str, status: str, message: str = None, execution_time: float = None):
    """
    Log global script execution status.
    
    Args:
        script_name (str): Name of the script being run (e.g., 'collect_data.py').
        status (str): Outcome of the run ('success', 'failure', 'partial').
        message (str, optional): Additional details or error message.
        execution_time (float, optional): Runtime duration in seconds.
    """
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(_adapt_sql("""
            INSERT INTO system_log (script_name, status, message, execution_time_seconds)
            VALUES (?, ?, ?, ?)
        """), (script_name, status, message, execution_time))

def get_latest_price_date(symbol: str) -> Optional[str]:
    """
    Get the most recent date for which we have price data for a symbol.
    
    Args:
        symbol (str): Stock symbol to query.
        
    Returns:
        Optional[str]: Date string (YYYY-MM-DD) or None if no data exists.
        
    Example:
        >>> latest = get_latest_price_date('MSFT')
        >>> print(latest)
        '2023-10-27'
    """
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(_adapt_sql("""
            SELECT MAX(date) as latest_date
            FROM prices
            WHERE symbol = ?
        """), (symbol,))
        result = cursor.fetchone()
        return result['latest_date'] if result else None

def check_missing_data(symbol: str, start_date: str, end_date: str) -> List[str]:
    """
    Check for missing dates in price data within a range.
    
    Args:
        symbol (str): Stock symbol to check.
        start_date (str): Start of range (YYYY-MM-DD).
        end_date (str): End of range (YYYY-MM-DD).
        
    Returns:
        List[str]: List of dates that exist in the database for this range.
        
    Note:
        Logs a warning if more than 30% of expected days are missing.
        
    Example:
        >>> dates = check_missing_data('GOOGL', '2023-01-01', '2023-01-31')
        >>> if len(dates) < 20: print("Data gaps detected")
    """
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(_adapt_sql("""
            SELECT date FROM prices
            WHERE symbol = ? AND date BETWEEN ? AND ?
            ORDER BY date
        """), (symbol, start_date, end_date))

        dates = [row['date'] for row in cursor.fetchall()]
        
        # Simple check: count business days vs actual days
        # (More sophisticated version would exclude weekends/holidays)
        expected_days = (datetime.fromisoformat(end_date) - datetime.fromisoformat(start_date)).days
        actual_days = len(dates)
        
        if actual_days < expected_days * 0.7:  # Missing more than 30% of days
            logger.warning(f"⚠️  {symbol}: Only {actual_days}/{expected_days} days of data")
        
        return dates

def get_recent_prices(symbol: str, days: int = 60) -> List[Dict[str, Any]]:
    """
    Get recent price data for a symbol.
    
    Args:
        symbol (str): Stock symbol.
        days (int): Number of recent records to retrieve. Defaults to 60.
        
    Returns:
        List[Dict[str, Any]]: List of price records (dictionaries).
        
    Example:
        >>> prices = get_recent_prices('AAPL', days=5)
        >>> print(prices[0]['close'])
        175.50
    """
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(_adapt_sql("""
            SELECT * FROM prices
            WHERE symbol = ?
            ORDER BY date DESC
            LIMIT ?
        """), (symbol, days))

        return [dict(row) for row in cursor.fetchall()]

def get_statistics() -> Dict[str, Any]:
    """
    Get comprehensive database statistics.
    
    Returns:
        Dict[str, Any]: Dictionary containing counts of prices, news, predictions,
                       evaluations, stocks tracked, date ranges, and recent issues.
    """
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
        if DATABASE_URL:
            date_expr = "CURRENT_DATE - INTERVAL '7 days'"
        else:
            date_expr = "DATE('now', '-7 days')"
        cursor.execute(f"""
            SELECT COUNT(*) as count
            FROM data_quality_log
            WHERE date >= {date_expr} AND resolved = 0
        """)
        stats['recent_issues'] = cursor.fetchone()['count']
        
        return stats

# ============================================
# DATABASE INITIALIZATION
# ============================================

def initialize_database():
    """
    Initialize the database by creating tables and printing current statistics.
    Useful to run on first setup or to verify database state.
    """
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