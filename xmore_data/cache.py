"""
Caching layer for market data.

Uses joblib for efficient caching with expiration policy.
Cache keys: symbol + interval + date_range
"""

import joblib
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional
import os
import pandas as pd
import hashlib

from .config import Config
from .utils import get_logger

logger = get_logger(__name__)


class MarketDataCache:
    """
    Local file-based cache for market data using joblib.
    
    Features:
    - Per-symbol + interval + date_range cache
    - 24h expiration (configurable)
    - Force refresh flag
    - Automatic cleanup of stale cache
    """

    def __init__(self, cache_dir: Optional[Path] = None, ttl_hours: int = 24):
        """
        Initialize cache.
        
        Args:
            cache_dir: Directory for cache files (defaults to config)
            ttl_hours: Time-to-live in hours (defaults to config)
        """
        self.cache_dir = cache_dir or Config.CACHE_DIR
        self.ttl_hours = ttl_hours
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def get(
        self,
        symbol: str,
        interval: str,
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
        force_refresh: bool = False
    ) -> Optional[pd.DataFrame]:
        """
        Retrieve data from cache if available and not stale.
        
        Args:
            symbol: Stock symbol
            interval: Time interval
            start: Start date (for cache key)
            end: End date (for cache key)
            force_refresh: Bypass cache
        
        Returns:
            DataFrame if found and valid, None otherwise
        """
        if force_refresh:
            logger.info(f"Cache: Force refresh requested for {symbol}")
            return None
        
        cache_file = self._get_cache_path(symbol, interval, start, end)
        
        if not cache_file.exists():
            return None
        
        # Check if stale
        mtime = os.path.getmtime(cache_file)
        age_hours = (datetime.now() - datetime.fromtimestamp(mtime)).total_seconds() / 3600
        
        if age_hours > self.ttl_hours:
            logger.info(f"Cache expired for {symbol} ({age_hours:.1f}h old, TTL={self.ttl_hours}h)")
            cache_file.unlink()  # Delete stale file
            return None
        
        try:
            df = joblib.load(cache_file)
            logger.info(f"✓ Cache hit: {symbol} [{interval}] ({age_hours:.1f}h old)")
            return df
        except Exception as e:
            logger.warning(f"Cache corrupted for {symbol}: {e}")
            cache_file.unlink()
            return None

    def set(
        self,
        symbol: str,
        interval: str,
        df: pd.DataFrame,
        start: Optional[datetime] = None,
        end: Optional[datetime] = None
    ) -> None:
        """
        Store data in cache.
        
        Args:
            symbol: Stock symbol
            interval: Time interval
            df: Data DataFrame
            start: Start date
            end: End date
        """
        if df is None or df.empty:
            logger.warning(f"Not caching empty data for {symbol}")
            return
        
        cache_file = self._get_cache_path(symbol, interval, start, end)
        
        try:
            joblib.dump(df, cache_file, compress=3)  # Compress for efficiency
            logger.debug(f"Cached {symbol} [{interval}] → {cache_file}")
        except Exception as e:
            logger.warning(f"Failed to cache {symbol}: {e}")

    def _get_cache_path(
        self,
        symbol: str,
        interval: str,
        start: Optional[datetime] = None,
        end: Optional[datetime] = None
    ) -> Path:
        """
        Generate cache file path from symbol, interval, and date range.
        
        Args:
            symbol: Stock symbol
            interval: Time interval
            start: Start date
            end: End date
        
        Returns:
            Path to cache file
        """
        # Create date range part of key
        start_str = start.date().isoformat() if start else "none"
        end_str = end.date().isoformat() if end else "none"
        
        # Create hash of full key for filename
        key = f"{symbol}_{interval}_{start_str}_{end_str}"
        key_hash = hashlib.md5(key.encode()).hexdigest()[:8]
        
        filename = f"{symbol}_{interval}_{key_hash}.joblib"
        return self.cache_dir / filename

    def clear(self, symbol: Optional[str] = None) -> None:
        """
        Clear cache for a symbol or all.
        
        Args:
            symbol: If provided, clear only this symbol. If None, clear all.
        """
        if symbol:
            # Clear caches for this symbol
            for cache_file in self.cache_dir.glob(f"{symbol}_*.joblib"):
                cache_file.unlink()
            logger.info(f"Cleared cache for {symbol}")
        else:
            # Clear all caches
            for cache_file in self.cache_dir.glob("*.joblib"):
                cache_file.unlink()
            logger.info(f"Cleared all cache ({len(list(self.cache_dir.glob('*.joblib')))} files)")

    def cleanup_stale(self) -> int:
        """
        Remove all stale cache files.
        
        Returns:
            Number of files removed
        """
        removed = 0
        cutoff = datetime.now() - timedelta(hours=self.ttl_hours)
        
        for cache_file in self.cache_dir.glob("*.joblib"):
            mtime = datetime.fromtimestamp(os.path.getmtime(cache_file))
            if mtime < cutoff:
                cache_file.unlink()
                removed += 1
        
        if removed > 0:
            logger.info(f"Cleaned up {removed} stale cache files")
        
        return removed

    def get_cache_stats(self) -> dict:
        """
        Get cache statistics.
        
        Returns:
            Dict with cache info
        """
        cache_files = list(self.cache_dir.glob("*.joblib"))
        total_size = sum(f.stat().st_size for f in cache_files) / (1024 * 1024)  # MB
        
        return {
            "cache_dir": str(self.cache_dir),
            "file_count": len(cache_files),
            "size_mb": round(total_size, 2),
            "ttl_hours": self.ttl_hours
        }
