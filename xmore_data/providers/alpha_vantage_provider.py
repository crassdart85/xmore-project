"""
Alpha Vantage Provider - Tertiary fallback for market data.

Provides global OHLCV data. Limited by free tier rate limits (5 calls/min).
Only used when EGXPY and yfinance fail.
"""

from datetime import datetime, timedelta
from typing import Optional
import pandas as pd
import time
from threading import Lock

from ..config import Config
from ..utils import exponential_backoff, validate_dataframe, get_logger
from . import MarketDataProvider

logger = get_logger(__name__)


class AlphaVantageProvider(MarketDataProvider):
    """
    Provider for Alpha Vantage API.
    
    Requires: pip install alpha-vantage
    Requires: ALPHA_VANTAGE_API_KEY environment variable
    
    Note: Free tier limited to 5 API calls/min.
    Implements rate limiting via thread-safe counter.
    """

    # Class-level rate limit tracking
    _call_times: list[float] = []
    _lock = Lock()

    def __init__(self):
        super().__init__("Alpha Vantage")
        
        if not Config.ALPHA_VANTAGE_API_KEY:
            raise ValueError(
                "ALPHA_VANTAGE_API_KEY not set in .env\n"
                "Get free key at: https://www.alphavantage.co/api/"
            )
        
        self.client = self._initialize_client()

    def _initialize_client(self):
        """
        Initialize Alpha Vantage client.
        
        Returns:
            Alpha Vantage API client
        
        Raises:
            ImportError: If alpha-vantage not installed
        """
        try:
            from alpha_vantage.timeseries import TimeSeries
            
            ts = TimeSeries(
                key=Config.ALPHA_VANTAGE_API_KEY,
                output_format='pandas',
                indexing_type='date'
            )
            logger.info("✓ Alpha Vantage client initialized")
            return ts
        
        except ImportError:
            logger.error("alpha-vantage not installed. Install: pip install alpha-vantage")
            raise

    def _check_rate_limit(self) -> None:
        """
        Check and enforce rate limit (5 calls/min for free tier).
        
        Blocks if necessary to respect rate limits.
        """
        with AlphaVantageProvider._lock:
            now = time.time()
            # Remove calls older than rate window
            cutoff = now - Config.ALPHA_VANTAGE_RATE_WINDOW_SEC
            AlphaVantageProvider._call_times = [
                t for t in AlphaVantageProvider._call_times if t > cutoff
            ]
            
            # Check if we've exceeded limit
            if len(AlphaVantageProvider._call_times) >= Config.ALPHA_VANTAGE_RATE_LIMIT:
                oldest = AlphaVantageProvider._call_times[0]
                wait_time = Config.ALPHA_VANTAGE_RATE_WINDOW_SEC - (now - oldest)
                if wait_time > 0:
                    logger.warning(
                        f"Alpha Vantage rate limit ({Config.ALPHA_VANTAGE_RATE_LIMIT}/min) "
                        f"reached. Waiting {wait_time:.1f}s..."
                    )
                    time.sleep(wait_time + 0.5)
                    now = time.time()
            
            # Record this call
            AlphaVantageProvider._call_times.append(now)

    @exponential_backoff(max_attempts=Config.RETRY_ATTEMPTS)
    def fetch(
        self,
        symbol: str,
        interval: str = "1d",
        start: Optional[datetime] = None,
        end: Optional[datetime] = None
    ) -> pd.DataFrame:
        """
        Fetch historical market data from Alpha Vantage.
        
        Args:
            symbol: Stock symbol (e.g., "GOOGL", "AAPL")
            interval: OHLCV interval (1d, 1w, 1mo; intraday limited for free tier)
            start: Start date (defaults to 90 days ago)
            end: End date (defaults to today)
        
        Returns:
            Standardized DataFrame
        
        Raises:
            ValueError: If symbol not found or no data
            ConnectionError: If API fails
            TimeoutError: If request times out
        """
        try:
            # Enforce rate limiting
            self._check_rate_limit()
            
            logger.info(f"Fetching {symbol} from Alpha Vantage (interval={interval})")
            
            # Set defaults
            if end is None:
                end = datetime.now()
            if start is None:
                start = end - timedelta(days=90)
            
            # Alpha Vantage outputsize: compact (100 recent) vs full (up to 20 years)
            # Use full for better range coverage
            outputsize = 'full' if (end - start).days > 100 else 'compact'
            
            # Fetch data based on interval
            if interval == "1d":
                df, meta = self.client.get_daily(
                    symbol=symbol,
                    outputsize=outputsize
                )
            elif interval == "1w":
                df, meta = self.client.get_weekly(symbol=symbol)
            elif interval == "1mo":
                df, meta = self.client.get_monthly(symbol=symbol)
            else:
                # Intraday not well supported in free tier
                raise ValueError(f"Alpha Vantage free tier does not support {interval} intraday")
            
            if df is None or df.empty:
                raise ValueError(f"{symbol} not found on Alpha Vantage or no data in range")
            
            # Filter to date range
            df = df[(df.index >= start.date()) & (df.index <= end.date())]
            
            if df.empty:
                raise ValueError(f"No data in range for {symbol}")
            
            # Keep provider-native labels; validate_dataframe() handles
            # canonical mapping (including "1. open", "2. high", etc.).
            if "5. adjusted close" in df.columns:
                df["Adj Close"] = df["5. adjusted close"]
            
            # Reset index to make date a column
            df.reset_index(inplace=True)
            if 'index' in df.columns:
                df.rename(columns={'index': 'Date'}, inplace=True)
            
            # Validate and standardize
            df = validate_dataframe(df, f"AlphaVantage[{symbol}]")
            logger.info(f"✓ Alpha Vantage: {symbol} - {len(df)} rows")
            
            return df
        
        except Exception as e:
            logger.error(f"Alpha Vantage failed for {symbol}: {e}")
            raise

    def support_intraday(self) -> bool:
        """Alpha Vantage free tier has limited intraday support."""
        return False
