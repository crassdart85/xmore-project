"""
CLI interface for Xmore data layer.

Usage examples:
    python main.py --symbol COMI --interval 1d
    python main.py --symbols COMI SWDY HRHO --summary
    python main.py --benchmark --export csv
    python main.py --egx30 --export excel
    python main.py --cache-stats
    python main.py --refresh --symbol COMI
"""

import argparse
import sys
from pathlib import Path
from datetime import datetime
import pandas as pd

try:
    from .data_manager import DataManager
    from .utils import format_output_summary, get_logger
    from .config import Config
except ImportError:
    # Support direct script execution: python xmore_data/main.py ...
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from xmore_data.data_manager import DataManager
    from xmore_data.utils import format_output_summary, get_logger
    from xmore_data.config import Config

logger = get_logger(__name__)


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Xmore Data Layer - EGX Market Data Fetcher",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Fetch single symbol
  python main.py --symbol COMI --interval 1d

  # Fetch multiple symbols
  python main.py --symbols COMI SWDY HRHO

  # Fetch entire EGX30
  python main.py --egx30

  # Fetch with custom date range
  python main.py --symbol COMI --start 2024-01-01 --end 2024-12-31

  # Relative date ranges
  python main.py --symbol COMI --start 90d --end today

  # Export to CSV
  python main.py --symbol COMI --export csv

  # Export to Excel
  python main.py --symbols COMI SWDY HRHO --export excel

  # Show data summary
  python main.py --symbol COMI --summary

  # Force refresh cache
  python main.py --symbol COMI --refresh

  # View cache statistics
  python main.py --cache-stats
        """
    )
    
    # Symbol arguments
    symbol_group = parser.add_argument_group('Symbol Selection')
    symbol_group.add_argument(
        '--symbol',
        type=str,
        help='Single stock symbol (e.g., COMI, SWDY)'
    )
    symbol_group.add_argument(
        '--symbols',
        nargs='+',
        help='Multiple stock symbols (e.g., COMI SWDY HRHO)'
    )
    symbol_group.add_argument(
        '--egx30',
        action='store_true',
        help='Fetch all EGX30 symbols'
    )
    symbol_group.add_argument(
        '--benchmark',
        action='store_true',
        help='Fetch EGX index (^CASE) for benchmarking'
    )
    
    # Data parameters
    data_group = parser.add_argument_group('Data Parameters')
    data_group.add_argument(
        '--interval',
        type=str,
        default='1d',
        choices=['1m', '5m', '15m', '1h', '1d', '1w', '1mo'],
        help='Time interval (default: 1d)'
    )
    data_group.add_argument(
        '--start',
        type=str,
        help='Start date (YYYY-MM-DD) or relative (90d, 1y, 6mo, 4w) - default: 90d'
    )
    data_group.add_argument(
        '--end',
        type=str,
        help='End date (YYYY-MM-DD) - default: today'
    )
    
    # Cache & refresh
    cache_group = parser.add_argument_group('Cache & Refresh')
    cache_group.add_argument(
        '--refresh',
        action='store_true',
        help='Force refresh (bypass cache)'
    )
    cache_group.add_argument(
        '--cache-stats',
        action='store_true',
        help='Show cache statistics'
    )
    cache_group.add_argument(
        '--clear-cache',
        action='store_true',
        help='Clear all cache files'
    )
    
    # Output options
    output_group = parser.add_argument_group('Output Options')
    output_group.add_argument(
        '--summary',
        action='store_true',
        help='Print data summary'
    )
    output_group.add_argument(
        '--export',
        type=str,
        choices=['csv', 'excel', 'json'],
        help='Export to file (CSV, Excel, or JSON)'
    )
    output_group.add_argument(
        '--output-dir',
        type=str,
        default='./data_exports',
        help='Output directory for exports (default: ./data_exports)'
    )
    
    args = parser.parse_args()
    
    # Initialize data manager
    try:
        dm = DataManager(use_cache=not args.refresh)
        logger.info(f"Available providers: {', '.join(dm.provider_info)}")
    except Exception as e:
        logger.error(f"Failed to initialize DataManager: {e}")
        sys.exit(1)
    
    # Handle cache stat command
    if args.cache_stats:
        stats = dm.get_cache_stats()
        print("\n" + "="*60)
        print("📊 Cache Statistics")
        print("="*60)
        for key, value in stats.items():
            print(f"{key:.<40} {value}")
        print("="*60 + "\n")
        return
    
    # Handle clear cache command
    if args.clear_cache:
        dm.clear_cache()
        print("✓ Cache cleared\n")
        return
    
    # Validate that we have a symbol selection
    if not any([args.symbol, args.symbols, args.egx30, args.benchmark]):
        parser.print_help()
        logger.error("Please select symbols with --symbol, --symbols, --egx30, or --benchmark")
        sys.exit(1)
    
    # Prepare output directory
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Handle different symbol selections
    try:
        if args.benchmark:
            logger.info("Fetching EGX index (benchmark)")
            data = {'EGX_INDEX': dm.fetch_index(args.start, args.end, args.refresh)}
            
        elif args.egx30:
            logger.info("Fetching all EGX30 symbols")
            data = dm.fetch_egx30(args.interval, args.start, args.end, args.refresh)
            
        elif args.symbols:
            logger.info(f"Fetching {len(args.symbols)} symbols")
            data = dm.fetch_multiple(args.symbols, args.interval, args.start, args.end, args.refresh)
            
        else:  # args.symbol
            logger.info(f"Fetching {args.symbol}")
            df = dm.fetch_data(args.symbol, args.interval, args.start, args.end, args.refresh)
            data = {args.symbol: df}
    
    except Exception as e:
        logger.error(f"Failed to fetch data: {e}")
        sys.exit(1)
    
    # Print summaries
    if args.summary or (args.symbol and not args.export):
        print("\n")
        for symbol, df in data.items():
            if df is not None and not df.empty:
                print(format_output_summary(df, symbol))
            else:
                print(f"⚠️  No data for {symbol}\n")
    
    # Export to file
    if args.export:
        _export_data(data, args.export, output_dir)
    
    print(f"✓ Complete. Available providers: {', '.join(dm.provider_info)}\n")


def _export_data(data: dict, export_format: str, output_dir: Path) -> None:
    """
    Export data to file.
    
    Args:
        data: Dict mapping symbol to DataFrame
        export_format: csv, excel, or json
        output_dir: Output directory
    """
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    if export_format == 'csv':
        for symbol, df in data.items():
            if df is not None and not df.empty:
                filename = output_dir / f"{symbol}_{timestamp}.csv"
                df.to_csv(filename, index=False)
                logger.info(f"Exported {symbol} → {filename}")
    
    elif export_format == 'excel':
        # Combine all dataframes into single Excel file with multiple sheets
        filename = output_dir / f"market_data_{timestamp}.xlsx"
        with pd.ExcelWriter(filename, engine='openpyxl') as writer:
            for symbol, df in data.items():
                if df is not None and not df.empty:
                    # Limit sheet name to 31 chars (Excel limit)
                    sheet_name = symbol[:31]
                    df.to_excel(writer, sheet_name=sheet_name, index=False)
                    logger.info(f"Exported {symbol} to Excel sheet")
        logger.info(f"All data → {filename}")
    
    elif export_format == 'json':
        for symbol, df in data.items():
            if df is not None and not df.empty:
                filename = output_dir / f"{symbol}_{timestamp}.json"
                df.to_json(filename, orient='records', date_format='iso', indent=2)
                logger.info(f"Exported {symbol} → {filename}")


if __name__ == '__main__':
    main()
