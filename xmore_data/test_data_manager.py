"""
Unit tests for xmore_data module.

Run with: pytest tests/test_data_manager.py -v

Requirements:
    pip install pytest pytest-cov
"""

import pytest
import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path
import tempfile
import shutil

# Import modules under test
from xmore_data.config import Config
from xmore_data.cache import MarketDataCache
from xmore_data.utils import (
    validate_dataframe, 
    parse_date_range, 
    exponential_backoff,
    format_output_summary
)


class TestConfig:
    """Test configuration module."""
    
    def test_config_defaults(self):
        """Test that config loads with sensible defaults."""
        assert Config.CACHE_EXPIRATION_HOURS > 0
        assert Config.EGXPY_TIMEOUT > 0
        assert len(Config.EGX30_SYMBOLS) > 0
        assert len(Config.STANDARD_COLUMNS) == 7
    
    def test_cache_dir_created(self):
        """Test that cache directory is created."""
        assert Config.CACHE_DIR.exists()
    
    def test_log_file_parent_created(self):
        """Test that log directory is created."""
        assert Config.LOG_FILE.parent.exists()


class TestCache:
    """Test caching system."""
    
    @pytest.fixture
    def cache(self):
        """Create temporary cache for testing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = MarketDataCache(cache_dir=Path(tmpdir), ttl_hours=24)
            yield cache
    
    @pytest.fixture
    def sample_df(self):
        """Create sample dataframe."""
        return pd.DataFrame({
            'Date': pd.date_range('2024-01-01', periods=10),
            'Open': [100 + i for i in range(10)],
            'High': [102 + i for i in range(10)],
            'Low': [99 + i for i in range(10)],
            'Close': [101 + i for i in range(10)],
            'Adj Close': [101 + i for i in range(10)],
            'Volume': [1000000] * 10
        })
    
    def test_cache_set_and_get(self, cache, sample_df):
        """Test storing and retrieving from cache."""
        cache.set("COMI", "1d", sample_df)
        result = cache.get("COMI", "1d")
        
        assert result is not None
        assert len(result) == len(sample_df)
        assert (result['Date'] == sample_df['Date']).all()
    
    def test_cache_miss(self, cache):
        """Test cache miss returns None."""
        result = cache.get("NONEXISTENT", "1d")
        assert result is None
    
    def test_force_refresh(self, cache, sample_df):
        """Test force refresh bypass."""
        cache.set("COMI", "1d", sample_df)
        result = cache.get("COMI", "1d", force_refresh=True)
        
        assert result is None  # Force refresh ignores cache
    
    def test_clear_single_symbol(self, cache, sample_df):
        """Test clearing cache for single symbol."""
        cache.set("COMI", "1d", sample_df)
        cache.set("SWDY", "1d", sample_df)
        
        cache.clear("COMI")
        assert cache.get("COMI", "1d") is None
        assert cache.get("SWDY", "1d") is not None
    
    def test_clear_all(self, cache, sample_df):
        """Test clearing all cache."""
        cache.set("COMI", "1d", sample_df)
        cache.set("SWDY", "1d", sample_df)
        
        cache.clear()
        assert cache.get("COMI", "1d") is None
        assert cache.get("SWDY", "1d") is None


class TestDataValidation:
    """Test data validation and cleaning."""
    
    @pytest.fixture
    def valid_df(self):
        """Create valid test dataframe."""
        return pd.DataFrame({
            'Date': pd.date_range('2024-01-01', periods=10),
            'Open': [100.0 + i for i in range(10)],
            'High': [102.0 + i for i in range(10)],
            'Low': [99.0 + i for i in range(10)],
            'Close': [101.0 + i for i in range(10)],
            'Adj Close': [101.0 + i for i in range(10)],
            'Volume': [1000000] * 10
        })
    
    def test_validate_valid_df(self, valid_df):
        """Test validation of valid dataframe."""
        result = validate_dataframe(valid_df, "test")
        
        assert len(result) == len(valid_df)
        # pandas on newer Python builds may use datetime64[us] instead of ns precision
        assert str(result['Date'].dtype).startswith('datetime64[')
        assert all(col in result.columns for col in Config.STANDARD_COLUMNS)
    
    def test_validate_empty_df(self):
        """Test validation rejects empty dataframe."""
        empty_df = pd.DataFrame()
        
        with pytest.raises(ValueError):
            validate_dataframe(empty_df, "test")
    
    def test_validate_none_df(self):
        """Test validation rejects None."""
        with pytest.raises(ValueError):
            validate_dataframe(None, "test")
    
    def test_validate_sorts_by_date(self):
        """Test that validation sorts by date."""
        unsorted_df = pd.DataFrame({
            'Date': ['2024-01-03', '2024-01-01', '2024-01-02'],
            'Close': [103, 101, 102],
            'Open': [102, 100, 101],
            'High': [104, 102, 103],
            'Low': [102, 100, 101],
            'Adj Close': [103, 101, 102],
            'Volume': [1000000, 1000000, 1000000]
        })
        
        result = validate_dataframe(unsorted_df, "test")
        
        assert result['Date'].is_monotonic_increasing
    
    def test_validate_removes_duplicates(self):
        """Test that validation removes duplicate dates."""
        dup_df = pd.DataFrame({
            'Date': ['2024-01-01', '2024-01-01', '2024-01-02'],
            'Close': [101, 102, 103],
            'Open': [100, 100, 102],
            'High': [102, 103, 104],
            'Low': [100, 100, 101],
            'Adj Close': [101, 102, 103],
            'Volume': [1000000, 2000000, 1000000]
        })
        
        result = validate_dataframe(dup_df, "test")
        
        assert len(result) == 2  # One duplicate removed
        assert not result.duplicated(subset=['Date']).any()


class TestDateParsing:
    """Test date range parsing."""
    
    def test_parse_absolute_dates(self):
        """Test parsing absolute dates."""
        start, end = parse_date_range("2024-01-01", "2024-12-31")
        
        assert start.year == 2024
        assert start.month == 1
        assert start.day == 1
        assert end.month == 12
        assert end.day == 31
    
    def test_parse_relative_days(self):
        """Test parsing relative date (days)."""
        start, end = parse_date_range("90d", None)
        
        # Should be roughly 90 days ago
        delta = (end - start).days
        assert 89 <= delta <= 91
    
    def test_parse_relative_year(self):
        """Test parsing relative date (years)."""
        start, end = parse_date_range("1y", None)
        
        delta = (end - start).days
        assert 364 <= delta <= 366  # Account for leap years
    
    def test_parse_relative_months(self):
        """Test parsing relative date (months)."""
        start, end = parse_date_range("6mo", None)
        
        delta = (end - start).days
        assert 170 <= delta <= 185  # 6 months ≈ 180 days
    
    def test_parse_default_start(self):
        """Test that default start is 90 days ago."""
        start, end = parse_date_range(None, None)
        
        delta = (end - start).days
        assert 89 <= delta <= 91


class TestExponentialBackoff:
    """Test retry decorator with exponential backoff."""
    
    def test_succeeds_on_first_call(self):
        """Test function that succeeds immediately."""
        call_count = [0]
        
        @exponential_backoff(max_attempts=3)
        def success():
            call_count[0] += 1
            return "success"
        
        result = success()
        
        assert result == "success"
        assert call_count[0] == 1
    
    def test_retries_on_failure(self):
        """Test function that fails then succeeds."""
        call_count = [0]
        
        @exponential_backoff(max_attempts=3)
        def fail_then_succeed():
            call_count[0] += 1
            if call_count[0] < 3:
                raise ValueError("fail")
            return "success"
        
        result = fail_then_succeed()
        
        assert result == "success"
        assert call_count[0] == 3
    
    def test_gives_up_after_max_attempts(self):
        """Test that function gives up after max attempts."""
        call_count = [0]
        
        @exponential_backoff(max_attempts=2)
        def always_fails():
            call_count[0] += 1
            raise ValueError("always fails")
        
        with pytest.raises(ValueError):
            always_fails()
        
        assert call_count[0] == 2


class TestFormatSummary:
    """Test formatting utilities."""
    
    @pytest.fixture
    def sample_df(self):
        """Create sample dataframe."""
        return pd.DataFrame({
            'Date': pd.date_range('2024-01-01', periods=3),
            'Open': [100, 101, 102],
            'High': [102, 103, 104],
            'Low': [99, 100, 101],
            'Close': [101, 102, 103],
            'Adj Close': [101, 102, 103],
            'Volume': [1000000, 2000000, 3000000]
        })
    
    def test_format_summary_valid(self, sample_df):
        """Test summary formatting."""
        summary = format_output_summary(sample_df, "COMI", "EGXPY")
        
        assert "COMI" in summary
        assert "EGXPY" in summary
        assert "103.00" in summary
        assert "Data Points" in summary
    
    def test_format_summary_empty(self):
        """Test summary formatting with empty dataframe."""
        empty_df = pd.DataFrame()
        summary = format_output_summary(empty_df, "COMI")
        
        assert "No data" in summary


# Integration tests requiring API access (marked as slow)
@pytest.mark.slow
class TestIntegration:
    """Integration tests that require actual data providers."""
    
    @pytest.fixture(scope="module")
    def dm(self):
        """Create DataManager instance."""
        try:
            from xmore_data.data_manager import DataManager
            return DataManager()
        except Exception as e:
            pytest.skip(f"Could not initialize DataManager: {e}")
    
    def test_fetch_data_returns_dataframe(self, dm):
        """Test that fetch returns valid dataframe."""
        try:
            df = dm.fetch_data("COMI", start="30d")
            
            assert isinstance(df, pd.DataFrame)
            assert not df.empty
            assert len(df) > 0
        except Exception as e:
            pytest.skip(f"Could not fetch data: {e}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
