"""
Utility functions for data layer: logging, retry logic, validation, formatting.
"""

import logging
import time
from functools import wraps
from typing import Callable, TypeVar, Any, Optional
from pathlib import Path
import pandas as pd
from datetime import datetime, timedelta

from .config import Config

# Setup logging
logger = logging.getLogger(__name__)
log_file = Config.LOG_FILE
log_file.parent.mkdir(parents=True, exist_ok=True)

handler = logging.FileHandler(log_file)
console_handler = logging.StreamHandler()
formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
handler.setFormatter(formatter)
console_handler.setFormatter(formatter)

logger.addHandler(handler)
logger.addHandler(console_handler)
logger.setLevel(Config.LOG_LEVEL)

T = TypeVar('T')


def exponential_backoff(
    max_attempts: int = Config.RETRY_ATTEMPTS,
    base_delay: float = Config.RETRY_BASE_DELAY,
    max_delay: float = Config.RETRY_MAX_DELAY
) -> Callable:
    """
    Decorator: Retry function with exponential backoff.
    
    Args:
        max_attempts: Maximum retry attempts
        base_delay: Initial delay in seconds
        max_delay: Maximum delay cap in seconds
    
    Returns:
        Decorated function with retry logic
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            delay = base_delay
            last_exception = None
            
            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    if attempt < max_attempts:
                        logger.warning(
                            f"{func.__name__} failed (attempt {attempt}/{max_attempts}). "
                            f"Retrying in {delay}s: {str(e)}"
                        )
                        time.sleep(delay)
                        delay = min(delay * 2, max_delay)
                    else:
                        logger.error(
                            f"{func.__name__} failed after {max_attempts} attempts: {str(e)}"
                        )
            
            raise last_exception
        
        return wrapper
    return decorator


def validate_dataframe(df: pd.DataFrame, source: str) -> pd.DataFrame:
    """
    Validate and standardize DataFrame from any provider.
    
    Ensures:
    - Columns are standard
    - Date is datetime
    - Numeric columns are numeric
    - No duplicates
    - Sorted by date ascending
    
    Args:
        df: Input DataFrame
        source: Provider name (for logging)
    
    Returns:
        Cleaned and standardized DataFrame
    
    Raises:
        ValueError: If validation fails
    """
    if df is None or df.empty:
        raise ValueError(f"{source}: Received empty/None DataFrame")
    
    df = df.copy()
    
    # Normalize raw column labels (provider-specific names -> standard schema)
    df.columns = [str(col).strip() for col in df.columns]
    canonical_map = {
        "date": "Date",
        "datetime": "Date",
        "time": "Date",
        "timestamp": "Date",
        "open": "Open",
        "1. open": "Open",
        "high": "High",
        "2. high": "High",
        "low": "Low",
        "3. low": "Low",
        "close": "Close",
        "4. close": "Close",
        "adj close": "Adj Close",
        "adjclose": "Adj Close",
        "5. adjusted close": "Adj Close",
        "volume": "Volume",
        "5. volume": "Volume",
        "6. volume": "Volume",
    }
    rename_map = {}
    for col in df.columns:
        normalized = " ".join(col.lower().replace("_", " ").split())
        if normalized in canonical_map:
            rename_map[col] = canonical_map[normalized]
    if rename_map:
        df.rename(columns=rename_map, inplace=True)
    
    # Try to detect and rename Date/Datetime column
    for col in df.columns:
        if col.lower() in ['date', 'datetime', 'time', 'timestamp']:
            df.rename(columns={col: 'Date'}, inplace=True)
            break
    
    # Ensure Date column is first
    if 'Date' not in df.columns:
        if df.index.name and df.index.name.lower() in ['date', 'datetime']:
            df.reset_index(inplace=True)
            df.rename(columns={df.columns[0]: 'Date'}, inplace=True)
        else:
            raise ValueError(f"{source}: No Date/Datetime column found")
    
    # Convert Date to datetime
    try:
        df['Date'] = pd.to_datetime(df['Date'])
    except Exception as e:
        raise ValueError(f"{source}: Cannot parse Date column as datetime: {e}")
    
    # Ensure all standard columns exist (Adj Close can be derived from Close)
    for col in Config.STANDARD_COLUMNS:
        if col not in df.columns:
            if col == "Adj Close" and "Close" in df.columns:
                df[col] = df["Close"]
            else:
                df[col] = pd.NA

    # Numeric columns
    numeric_cols = ['Open', 'High', 'Low', 'Close', 'Adj Close', 'Volume']
    for col in numeric_cols:
        if col in df.columns:
            try:
                df[col] = pd.to_numeric(df[col], errors='coerce')
            except Exception as e:
                logger.warning(f"{source}: Cannot convert {col} to numeric: {e}")
    
    # Remove duplicates (keep last)
    initial_rows = len(df)
    df = df.drop_duplicates(subset=['Date'], keep='last')
    if len(df) < initial_rows:
        logger.info(f"{source}: Removed {initial_rows - len(df)} duplicate dates")
    
    # Sort by date ascending
    df = df.sort_values('Date').reset_index(drop=True)
    
    # Handle missing values (forward fill for 1-3 bars, then warn)
    for col in numeric_cols:
        if col in df.columns:
            na_count = df[col].isna().sum()
            if na_count > 0:
                df[col] = df[col].fillna(method='ffill', limit=3)
                remaining_na = df[col].isna().sum()
                if remaining_na > 0:
                    logger.warning(f"{source}: {col} has {remaining_na} unfilled NaNs")
    
    # Enforce final standard column order and drop extra columns
    df = df[Config.STANDARD_COLUMNS]

    logger.info(f"{source}: Validated {len(df)} rows | Date range: {df['Date'].min()} to {df['Date'].max()}")
    
    return df


def format_output_summary(df: pd.DataFrame, symbol: str, source: str = "") -> str:
    """
    Format a summary of fetched data.
    
    Args:
        df: Data DataFrame
        symbol: Trading symbol
        source: Data provider name
    
    Returns:
        Formatted string summary
    """
    if df.empty:
        return f"⚠️  No data for {symbol}"
    
    latest = df.iloc[-1]
    prev_close = df.iloc[-2]['Close'] if len(df) > 1 else latest['Close']
    change = latest['Close'] - prev_close
    change_pct = (change / prev_close * 100) if prev_close != 0 else 0
    
    source_str = f" [from {source}]" if source else ""
    
    summary = f"""
╔══════════════════════════════════════════════════════════╗
║ {symbol}{source_str}
╠══════════════════════════════════════════════════════════╣
║ Latest Close     : EGP {latest['Close']:.2f}
║ Change           : {change:+.2f} ({change_pct:+.2f}%)
║ High / Low       : {latest['High']:.2f} / {latest['Low']:.2f}
║ Avg Volume       : {df['Volume'].mean():,.0f}
║ Data Points      : {len(df)} rows
║ Date Range       : {df['Date'].min().date()} to {df['Date'].max().date()}
╚══════════════════════════════════════════════════════════╝
    """
    return summary


def parse_date_range(start: Optional[str], end: Optional[str]) -> tuple[datetime, datetime]:
    """
    Parse start/end date strings. Support formats: YYYY-MM-DD, relative (90d, 1y, etc).
    
    Args:
        start: Start date string or relative period
        end: End date string (defaults to today)
    
    Returns:
        Tuple of (start_datetime, end_datetime)
    """
    end_dt = datetime.now() if not end else _parse_single_date(end)
    
    if not start:
        start_dt = end_dt - timedelta(days=90)  # Default: last 90 days
    else:
        # Check if relative period (e.g., "90d", "1y", "6mo")
        if start.endswith('d'):
            days = int(start[:-1])
            start_dt = end_dt - timedelta(days=days)
        elif start.endswith('w'):
            weeks = int(start[:-1])
            start_dt = end_dt - timedelta(weeks=weeks)
        elif start.endswith('mo'):
            months = int(start[:-2])
            start_dt = end_dt - timedelta(days=months * 30)
        elif start.endswith('y'):
            years = int(start[:-1])
            start_dt = end_dt - timedelta(days=years * 365)
        else:
            start_dt = _parse_single_date(start)
    
    return start_dt, end_dt


def _parse_single_date(date_str: str) -> datetime:
    """Parse single date string in YYYY-MM-DD format."""
    lowered = date_str.strip().lower()
    if lowered == "today":
        return datetime.now()
    if lowered == "yesterday":
        return datetime.now() - timedelta(days=1)
    try:
        return datetime.strptime(date_str, '%Y-%m-%d')
    except ValueError:
        raise ValueError(f"Invalid date format: {date_str}. Use YYYY-MM-DD")


def get_logger(name: str) -> logging.Logger:
    """Get or create a named logger."""
    return logging.getLogger(name)
