"""
Example: Integrating xmore_data with signal generation and backtesting.

This demonstrates how to use the data layer in real workflows:
1. Fetch data
2. Generate signals
3. Evaluate performance
4. Benchmark against EGX30
"""

import sys
from pathlib import Path
from datetime import datetime, timedelta
import pandas as pd

# Add xmore_data to path
sys.path.insert(0, str(Path(__file__).parent))

from xmore_data import DataManager


def example_1_basic_fetch():
    """Example 1: Fetch and inspect data."""
    print("\n" + "="*70)
    print("EXAMPLE 1: BASIC DATA FETCH")
    print("="*70)
    
    dm = DataManager()
    
    # Fetch COMI (Commercial International Bank) last 90 days
    print("\nFetching COMI (Commercial International Bank)...")
    df = dm.fetch_data("COMI", interval="1d", start="90d")
    
    print(f"\n✓ Fetched {len(df)} trading days")
    print(f"  Date range: {df['Date'].min().date()} to {df['Date'].max().date()}")
    print(f"  Latest close: EGP {df['Close'].iloc[-1]:.2f}")
    print(f"  Daily change: {(df['Close'].iloc[-1] / df['Close'].iloc[-2] - 1) * 100:.2f}%")
    print(f"\nFirst 5 rows:")
    print(df.head())


def example_2_multiple_symbols():
    """Example 2: Fetch multiple symbols for portfolio analysis."""
    print("\n" + "="*70)
    print("EXAMPLE 2: MULTIPLE SYMBOL FETCH (Portfolio)")
    print("="*70)
    
    dm = DataManager()
    
    # Fetch top 5 EGX stocks
    portfolio = ["COMI", "SWDY", "HRHO", "ETEL", "ECAP"]
    print(f"\nFetching portfolio: {', '.join(portfolio)}")
    
    data = dm.fetch_multiple(portfolio, interval="1d", start="90d")
    
    # Analyze portfolio
    print("\nPortfolio Analysis:")
    print("-" * 70)
    print(f"{'Symbol':<10} {'Close':<12} {'1d Change':<15} {'90d Change':<15}")
    print("-" * 70)
    
    for symbol, df in data.items():
        if df is not None and len(df) > 1:
            latest = df['Close'].iloc[-1]
            prev = df['Close'].iloc[-2]
            first = df['Close'].iloc[0]
            
            change_1d = (latest / prev - 1) * 100
            change_90d = (latest / first - 1) * 100
            
            print(f"{symbol:<10} EGP {latest:<10.2f} {change_1d:>+7.2f}% {change_90d:>+14.2f}%")


def example_3_benchmark_analysis():
    """Example 3: Analyze performance vs EGX30 benchmark."""
    print("\n" + "="*70)
    print("EXAMPLE 3: BENCHMARK ANALYSIS vs EGX30")
    print("="*70)
    
    dm = DataManager()
    
    # Fetch test symbols and index
    symbols = ["COMI", "SWDY", "HRHO"]
    print(f"\nFetching {symbols} and EGX index...")
    
    # Get index for benchmark
    index_df = dm.fetch_index(start="90d")
    
    # Fetch stocks
    stock_data = dm.fetch_multiple(symbols, start="90d")
    
    # Calculate returns
    print("\nReturn Analysis (vs EGX Index):")
    print("-" * 70)
    print(f"{'Symbol':<10} {'Total Return':<15} {'vs EGX':<15} {'Outperformance':<15}")
    print("-" * 70)
    
    if index_df is not None and len(index_df) > 0:
        index_return = (index_df['Close'].iloc[-1] / index_df['Close'].iloc[0] - 1) * 100
        
        for symbol, df in stock_data.items():
            if df is not None and len(df) > 0:
                stock_return = (df['Close'].iloc[-1] / df['Close'].iloc[0] - 1) * 100
                outperformance = stock_return - index_return
                
                outperf_str = f"+{outperformance:.2f}%" if outperformance > 0 else f"{outperformance:.2f}%"
                print(f"{symbol:<10} {stock_return:>+7.2f}% {index_return:>+14.2f}% {outperf_str:>14}")


def example_4_signal_generation():
    """Example 4: Generate simple signals (Bullish/Bearish/Neutral)."""
    print("\n" + "="*70)
    print("EXAMPLE 4: SIMPLE SIGNAL GENERATION")
    print("="*70)
    
    dm = DataManager()
    
    symbol = "COMI"
    print(f"\nGenerating signals for {symbol}...")
    
    df = dm.fetch_data(symbol, start="90d")
    
    # Calculate simple moving averages
    df['SMA_20'] = df['Close'].rolling(window=20).mean()
    df['SMA_50'] = df['Close'].rolling(window=50).mean()
    
    # Generate signals: SMA20 > SMA50 = Bullish
    df['Signal'] = df.apply(
        lambda row: 'BULLISH' if row['SMA_20'] > row['SMA_50'] 
                   else ('BEARISH' if row['SMA_20'] < row['SMA_50'] 
                   else 'NEUTRAL'),
        axis=1
    )
    
    # Show last 10 days with signals
    print(f"\nLast 10 days - {symbol}:")
    print("-" * 100)
    print(f"{'Date':<12} {'Close':<10} {'SMA20':<10} {'SMA50':<10} {'Signal':<10} {'vs Previous':<15}")
    print("-" * 100)
    
    for i in range(-10, 0):
        row = df.iloc[i]
        if pd.notna(row['SMA_20']) and pd.notna(row['SMA_50']):
            prev_signal = df.iloc[i-1]['Signal'] if i > -len(df) else ""
            status = "→" if row['Signal'] == prev_signal else ("↑" if row['Signal'] == 'BULLISH' else "↓")
            
            print(f"{str(row['Date'].date()):<12} {row['Close']:<10.2f} {row['SMA_20']:<10.2f} "
                  f"{row['SMA_50']:<10.2f} {row['Signal']:<10} {status:<15}")
    
    # Summary
    latest_signal = df.iloc[-1]['Signal']
    print(f"\n✓ Latest Signal: {latest_signal}")


def example_5_volatility_analysis():
    """Example 5: Calculate volatility and risk metrics."""
    print("\n" + "="*70)
    print("EXAMPLE 5: VOLATILITY & RISK ANALYSIS")
    print("="*70)
    
    dm = DataManager()
    
    symbols = ["COMI", "SWDY", "HRHO"]
    print(f"\nAnalyzing volatility for {symbols}...")
    
    stock_data = dm.fetch_multiple(symbols, start="1y")
    
    print("\nVolatility Metrics:")
    print("-" * 80)
    print(f"{'Symbol':<10} {'Daily Vol':<15} {'Annual Vol':<15} {'Max DD':<15} {'Sharpe*':<15}")
    print("-" * 80)
    print("*Sharpe assumes 5% risk-free rate\n")
    
    for symbol, df in stock_data.items():
        if df is not None and len(df) > 1:
            # Daily returns
            returns = df['Close'].pct_change().dropna()
            
            # Volatility
            daily_vol = returns.std()
            annual_vol = daily_vol * (252 ** 0.5)  # Annualize
            
            # Max Drawdown
            cumulative = (1 + returns).cumprod()
            running_max = cumulative.expanding().max()
            drawdown = (cumulative - running_max) / running_max
            max_dd = drawdown.min()
            
            # Sharpe ratio (simplified: no risk-free rate adjustment)
            annual_return = returns.mean() * 252
            sharpe = (annual_return / annual_vol) if annual_vol > 0 else 0
            
            print(f"{symbol:<10} {daily_vol:<15.4f} {annual_vol:<15.2%} {max_dd:<15.2%} {sharpe:<15.2f}")


def example_6_cache_management():
    """Example 6: Demonstrate caching features."""
    print("\n" + "="*70)
    print("EXAMPLE 6: CACHE MANAGEMENT")
    print("="*70)
    
    dm = DataManager(use_cache=True)
    
    print("\n1. First fetch (cache miss):")
    import time
    start = time.time()
    df1 = dm.fetch_data("COMI", start="90d")
    elapsed1 = time.time() - start
    print(f"   Time: {elapsed1:.3f}s")
    
    print("\n2. Second fetch (cache hit):")
    start = time.time()
    df2 = dm.fetch_data("COMI", start="90d")
    elapsed2 = time.time() - start
    print(f"   Time: {elapsed2:.3f}s")
    print(f"   Speedup: {elapsed1/elapsed2:.1f}x faster")
    
    print("\n3. Cache statistics:")
    stats = dm.get_cache_stats()
    for key, value in stats.items():
        print(f"   {key}: {value}")
    
    print("\n4. Force refresh (bypass cache):")
    start = time.time()
    df3 = dm.fetch_data("COMI", start="90d", force_refresh=True)
    elapsed3 = time.time() - start
    print(f"   Time: {elapsed3:.3f}s")


def example_7_data_validation():
    """Example 7: Show data validation and cleaning."""
    print("\n" + "="*70)
    print("EXAMPLE 7: DATA VALIDATION & QUALITY")
    print("="*70)
    
    dm = DataManager()
    
    symbol = "COMI"
    print(f"\nFetching {symbol} and validating...")
    
    df = dm.fetch_data(symbol, start="30d")
    
    print(f"\n✓ Data Quality Checks:")
    print(f"  - Shape: {df.shape[0]} rows × {df.shape[1]} columns")
    print(f"  - Date Type: {df['Date'].dtype}")
    print(f"  - Date Range: {df['Date'].min().date()} to {df['Date'].max().date()}")
    print(f"  - Missing Values: {df.isnull().sum().sum()}")
    print(f"  - Duplicates: {df.duplicated(subset=['Date']).sum()}")
    print(f"  - Sorted by Date: {df['Date'].is_monotonic_increasing}")
    
    print(f"\n✓ Column Summary:")
    print(df[['Date', 'Open', 'High', 'Low', 'Close', 'Volume']].describe())


def main():
    """Run all examples."""
    print("\n" + "█" * 70)
    print("█" + " " * 68 + "█")
    print("█" + " XMORE DATA LAYER - INTEGRATION EXAMPLES ".center(68) + "█")
    print("█" + " " * 68 + "█")
    print("█" * 70)
    
    try:
        example_1_basic_fetch()
        example_2_multiple_symbols()
        example_3_benchmark_analysis()
        example_4_signal_generation()
        example_5_volatility_analysis()
        example_6_cache_management()
        example_7_data_validation()
        
        print("\n" + "█" * 70)
        print("█" + " ALL EXAMPLES COMPLETED SUCCESSFULLY ".center(68) + "█")
        print("█" * 70 + "\n")
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        print(f"\nDEBUG: Check that:")
        print(f"  1. At least one provider is installed (pip install yfinance)")
        print(f"  2. .env file exists with required configuration")
        print(f"  3. Internet connection is available for API calls")
        raise


if __name__ == "__main__":
    main()
