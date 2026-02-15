"""
Xmore Data Layer - Production-ready data ingestion for EGX market data.

Main exports:
    DataManager: Core orchestration class
    MarketDataCache: Caching layer
    Config: Configuration management
"""

from .data_manager import (
    DataManager,
    fetch_egx_data,
    fetch_multiple_symbols,
    get_egx30_index,
)
from .cache import MarketDataCache
from .config import Config

__version__ = "1.0.0"
__all__ = [
    'DataManager',
    'MarketDataCache',
    'Config',
    'fetch_egx_data',
    'fetch_multiple_symbols',
    'get_egx30_index',
]
