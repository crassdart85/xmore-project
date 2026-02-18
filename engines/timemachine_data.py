"""
Time Machine Data Fetcher
Fetches historical OHLCV for all EGX30 stocks using a multi-source strategy:

  1. yfinance batch (primary — fast, gets ~27/30 stocks)
  2. Direct Yahoo Finance v8/chart API via requests (fallback per-symbol)
  3. EGX30 equal-weight proxy (computed from available stocks — permanent benchmark fix)

All data stays in-memory — nothing is written to the database.
EGX stocks use .CA suffix on Yahoo Finance (e.g. COMI.CA, HRHO.CA).
"""

import logging
import os
import sqlite3
import time
from datetime import datetime, timedelta
from pathlib import Path

logger = logging.getLogger(__name__)

# EGX30 constituents — the main stocks Xmore tracks
EGX30_SYMBOLS = [
    'COMI.CA', 'HRHO.CA', 'SWDY.CA', 'TMGH.CA', 'EKHO.CA',
    'EFIH.CA', 'ORWE.CA', 'PHDC.CA', 'ABUK.CA', 'CLHO.CA',
    'ESRS.CA', 'ETEL.CA', 'JUFO.CA', 'MNHD.CA', 'OCDI.CA',
    'HELI.CA', 'AMOC.CA', 'AUTO.CA', 'CCAP.CA', 'EGAL.CA',
    'ELEC.CA', 'FWRY.CA', 'GBCO.CA', 'ISPH.CA', 'MFPC.CA',
    'PHAR.CA', 'SKPC.CA', 'SPIN.CA', 'SUGR.CA', 'TALM.CA'
]

# Human-readable stock names for the frontend
STOCK_NAMES = {
    'COMI.CA': ('Commercial International Bank', 'البنك التجاري الدولي'),
    'HRHO.CA': ('Hermes Holding', 'هيرميس القابضة'),
    'SWDY.CA': ('Elsewedy Electric', 'السويدي إلكتريك'),
    'TMGH.CA': ('Talaat Moustafa Group', 'مجموعة طلعت مصطفى'),
    'EKHO.CA': ('Egyptian Kuwaiti Holding', 'المصرية الكويتية القابضة'),
    'EFIH.CA': ('EFG Hermes Holding', 'إي إف جي هيرميس'),
    'ORWE.CA': ('Oriental Weavers', 'السجاد الشرقي'),
    'PHDC.CA': ('Palm Hills Development', 'بالم هيلز للتعمير'),
    'ABUK.CA': ('Abu Qir Fertilizers', 'أبو قير للأسمدة'),
    'CLHO.CA': ('Cleopatra Hospital', 'مستشفى كليوباترا'),
    'ESRS.CA': ('Ezz Steel', 'حديد عز'),
    'ETEL.CA': ('Telecom Egypt', 'المصرية للاتصالات'),
    'JUFO.CA': ('Juhayna Food Industries', 'جهينة للصناعات الغذائية'),
    'MNHD.CA': ('Madinet Nasr Housing', 'مدينة نصر للإسكان'),
    'OCDI.CA': ('Orascom Development', 'أوراسكوم للتنمية'),
    'HELI.CA': ('Heliopolis Housing', 'مصر الجديدة للإسكان'),
    'AMOC.CA': ('Alexandria Mineral Oils', 'الإسكندرية للزيوت المعدنية'),
    'AUTO.CA': ('GB Auto', 'جي بي أوتو'),
    'CCAP.CA': ('Citadel Capital', 'القلعة القابضة'),
    'EGAL.CA': ('Edita Food Industries', 'إيديتا للصناعات الغذائية'),
    'ELEC.CA': ('El Sewedy Electric', 'الكابلات الكهربائية'),
    'FWRY.CA': ('Fawry for Banking', 'فوري للمدفوعات'),
    'GBCO.CA': ('SODIC', 'سوديك'),
    'ISPH.CA': ('Ibnsina Pharma', 'ابن سينا فارما'),
    'MFPC.CA': ('Misr Fertilizers', 'مصر للأسمدة'),
    'PHAR.CA': ('Pharos Holding', 'فاروس القابضة'),
    'SKPC.CA': ('Sidi Kerir Petrochemicals', 'سيدي كرير للبتروكيماويات'),
    'SPIN.CA': ('Spinneys Egypt', 'سبينيز مصر'),
    'SUGR.CA': ('Delta Sugar', 'الدلتا للسكر'),
    'TALM.CA': ('Taaleem Management', 'تعليم لإدارة المدارس'),
}

# Shared session headers — mimic a real browser to avoid 429 blocks
_HEADERS = {
    'User-Agent': (
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
        'AppleWebKit/537.36 (KHTML, like Gecko) '
        'Chrome/121.0.0.0 Safari/537.36'
    ),
    'Accept': 'application/json',
}

# Local fallback DB path (read-only usage; no writes from this module)
_LOCAL_PRICE_DB = Path(__file__).resolve().parents[1] / 'stocks.db'


# ─── Source 2: Direct Yahoo Finance v8/chart API ──────────────────────────────

def _fetch_yahoo_direct(symbol: str, buffer_start: str, end_date: str) -> list:
    """
    Fallback for symbols that yfinance batch returns 0 rows (e.g. ESRS.CA).
    Calls query1.finance.yahoo.com/v8/finance/chart/ directly with requests.

    Returns list of row dicts (same format as yfinance parser), or [] on failure.
    """
    try:
        import requests
    except ImportError:
        return []

    try:
        p1 = int(datetime.strptime(buffer_start, '%Y-%m-%d').timestamp())
        p2 = int(datetime.strptime(end_date, '%Y-%m-%d').timestamp()) + 86400  # inclusive
        url = (
            f'https://query1.finance.yahoo.com/v8/finance/chart/{symbol}'
            f'?period1={p1}&period2={p2}&interval=1d&events=history'
        )
        resp = requests.get(url, headers=_HEADERS, timeout=15)
        if resp.status_code != 200:
            logger.debug(f"  {symbol} direct API: HTTP {resp.status_code}")
            return []

        payload = resp.json()
        chart = payload.get('chart', {})
        if chart.get('error'):
            logger.debug(f"  {symbol} direct API error: {chart['error']}")
            return []

        result_arr = chart.get('result', [])
        if not result_arr:
            return []

        item = result_arr[0]
        timestamps = item.get('timestamp', [])
        indicators = item.get('indicators', {})
        quotes = indicators.get('quote', [{}])[0]
        adj = indicators.get('adjclose', [{}])
        adj_close = adj[0].get('adjclose', []) if adj else []

        opens = quotes.get('open', [])
        highs = quotes.get('high', [])
        lows = quotes.get('low', [])
        closes = quotes.get('close', [])
        volumes = quotes.get('volume', [])

        rows = []
        for i, ts in enumerate(timestamps):
            # Skip rows where close is None (market holidays / missing data)
            close_val = (adj_close[i] if adj_close and i < len(adj_close) else None) or (closes[i] if i < len(closes) else None)
            if close_val is None:
                continue
            date_str = datetime.utcfromtimestamp(ts).strftime('%Y-%m-%d')
            rows.append({
                'date': date_str,
                'open': round(float(opens[i]) if i < len(opens) and opens[i] else close_val, 2),
                'high': round(float(highs[i]) if i < len(highs) and highs[i] else close_val, 2),
                'low': round(float(lows[i]) if i < len(lows) and lows[i] else close_val, 2),
                'close': round(float(close_val), 2),
                'volume': int(volumes[i]) if i < len(volumes) and volumes[i] else 0,
            })
        return rows

    except Exception as e:
        logger.debug(f"  {symbol} direct API exception: {e}")
        return []


# ─── Source 3: EGX30 equal-weight proxy ───────────────────────────────────────

def _compute_egx30_proxy(price_data: dict, buffer_start: str) -> list:
    """
    Build an equal-weight EGX30 proxy from available component stocks.
    Each stock is normalised to 1.0 at the earliest shared date, then averaged.

    Returns list of {date, open, high, low, close, volume} dicts stored under
    the key '^EGX30' in the caller's result dict.
    """
    # Collect all dates from component stocks (exclude the proxy key itself)
    component_data = {
        sym: price_data[sym]
        for sym in EGX30_SYMBOLS
        if sym in price_data and price_data[sym]
    }

    if not component_data:
        return []

    # Build date → {symbol: close} map
    date_map: dict = {}
    for sym, rows in component_data.items():
        for row in rows:
            date_map.setdefault(row['date'], {})[sym] = row['close']

    if not date_map:
        return []

    sorted_dates = sorted(date_map.keys())

    # Find base date: earliest date where ≥ 50% of component stocks have data
    min_stocks = max(3, len(component_data) // 2)
    base_date = None
    base_prices: dict = {}
    for d in sorted_dates:
        present = {sym: date_map[d][sym] for sym in date_map[d]}
        if len(present) >= min_stocks:
            base_date = d
            base_prices = present
            break

    if not base_date:
        return []

    # Compute proxy value for each date
    proxy_rows = []
    for d in sorted_dates:
        day_prices = date_map[d]
        # Only use stocks that have both a base price and today's price
        ratios = []
        for sym, base_px in base_prices.items():
            if sym in day_prices and base_px > 0:
                ratios.append(day_prices[sym] / base_px)

        if not ratios:
            continue

        avg = sum(ratios) / len(ratios)
        # Scale to a realistic EGX30-like index starting at 30000
        index_val = round(avg * 30000, 2)
        proxy_rows.append({
            'date': d,
            'open': index_val,
            'high': index_val,
            'low': index_val,
            'close': index_val,
            'volume': 0,
        })

    logger.info(f"  EGX30 proxy: {len(proxy_rows)} days from {len(base_prices)} stocks")
    return proxy_rows


def _fetch_from_local_db(symbol: str, buffer_start: str, end_date: str) -> list:
    """
    Read historical OHLCV from local stocks.db as a resilience fallback.
    This is read-only and keeps Time Machine fully ephemeral.
    """
    if not _LOCAL_PRICE_DB.exists():
        return []

    clean = symbol.replace('.CA', '')
    rows_out: list = []
    conn = sqlite3.connect(_LOCAL_PRICE_DB)
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(
            """
            SELECT date, open, high, low, close, volume
            FROM prices
            WHERE symbol IN (?, ?)
              AND date >= ?
              AND date <= ?
            ORDER BY date ASC
            """,
            (clean, symbol, buffer_start, end_date),
        ).fetchall()
    except Exception as e:
        logger.debug(f"  [localdb] {symbol}: query failed ({e})")
        conn.close()
        return []
    finally:
        conn.close()

    for r in rows:
        try:
            close_val = float(r['close'])
            rows_out.append({
                'date': str(r['date']),
                'open': round(float(r['open']) if r['open'] is not None else close_val, 2),
                'high': round(float(r['high']) if r['high'] is not None else close_val, 2),
                'low': round(float(r['low']) if r['low'] is not None else close_val, 2),
                'close': round(close_val, 2),
                'volume': int(r['volume']) if r['volume'] is not None else 0,
            })
        except Exception:
            continue
    return rows_out


def _fetch_from_postgres_db(symbol: str, buffer_start: str, end_date: str) -> list:
    """
    Read historical OHLCV from PostgreSQL prices table (Render/prod fallback).
    """
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        return []

    try:
        import psycopg2
    except ImportError:
        return []

    clean = symbol.replace('.CA', '')
    conn = None
    rows_out: list = []
    try:
        conn = psycopg2.connect(database_url)
        cur = conn.cursor()
        cur.execute(
            """
            SELECT date, open, high, low, close, volume
            FROM prices
            WHERE symbol IN (%s, %s)
              AND date >= %s
              AND date <= %s
            ORDER BY date ASC
            """,
            (clean, symbol, buffer_start, end_date),
        )
        rows = cur.fetchall()
        for r in rows:
            try:
                close_val = float(r[4])
                rows_out.append({
                    'date': str(r[0]),
                    'open': round(float(r[1]) if r[1] is not None else close_val, 2),
                    'high': round(float(r[2]) if r[2] is not None else close_val, 2),
                    'low': round(float(r[3]) if r[3] is not None else close_val, 2),
                    'close': round(close_val, 2),
                    'volume': int(r[5]) if r[5] is not None else 0,
                })
            except Exception:
                continue
    except Exception as e:
        logger.debug(f"  [pgdb] {symbol}: query failed ({e})")
        return []
    finally:
        if conn is not None:
            conn.close()

    return rows_out


def _fetch_from_db_fallback(symbol: str, buffer_start: str, end_date: str) -> list:
    """
    Prefer PostgreSQL (prod) then SQLite (local) as resilient fallback.
    """
    rows = _fetch_from_postgres_db(symbol, buffer_start, end_date)
    if rows:
        return rows
    return _fetch_from_local_db(symbol, buffer_start, end_date)


# ─── Public API ───────────────────────────────────────────────────────────────

def fetch_historical_prices(start_date: str, end_date: str) -> dict:
    """
    Fetch OHLCV data for all EGX30 stocks + EGX30 benchmark.

    Strategy:
      1. yfinance batch download (fast primary source)
      2. Direct Yahoo Finance v8 API per-symbol (fallback for batch failures)
      3. EGX30 equal-weight proxy (computed from step-1+2 data — always present)

    Args:
        start_date: "YYYY-MM-DD"
        end_date: "YYYY-MM-DD"

    Returns:
        {
          "COMI.CA": [{"date": "2025-06-15", "open": 62.0, "high": 63.5,
                       "low": 61.8, "close": 63.2, "volume": 1500000}, ...],
          "^EGX30":  [{"date": "2025-06-15", "close": 30250.0, ...}, ...],
          ...
        }
    """
    try:
        import yfinance as yf
    except ImportError:
        logger.error("yfinance not installed")
        return {}

    # Add 60 days buffer so TA indicators have warmup data
    buffer_start = (
        datetime.strptime(start_date, '%Y-%m-%d') - timedelta(days=60)
    ).strftime('%Y-%m-%d')

    logger.info(
        f"Fetching {len(EGX30_SYMBOLS)} EGX stocks from {buffer_start} to {end_date}"
    )

    # ── Step 1: yfinance batch ────────────────────────────────────────────────
    result: dict = {}
    try:
        data = yf.download(
            tickers=EGX30_SYMBOLS,
            start=buffer_start,
            end=end_date,
            interval='1d',
            group_by='ticker',
            auto_adjust=True,
            progress=False,
            threads=True,
        )
    except Exception as e:
        logger.error(f"yfinance batch download failed: {e}")
        data = None

    if data is not None and not data.empty:
        for symbol in EGX30_SYMBOLS:
            try:
                df = data[symbol].dropna(subset=['Close'])
                rows = []
                for idx, row in df.iterrows():
                    rows.append({
                        'date': idx.strftime('%Y-%m-%d'),
                        'open': round(float(row['Open']), 2),
                        'high': round(float(row['High']), 2),
                        'low': round(float(row['Low']), 2),
                        'close': round(float(row['Close']), 2),
                        'volume': int(row['Volume']) if row['Volume'] > 0 else 0,
                    })
                if rows:
                    result[symbol] = rows
                    logger.info(f"  [batch] {symbol}: {len(rows)} days")
            except Exception as e:
                logger.debug(f"  [batch] {symbol}: failed ({e})")
    else:
        logger.warning("yfinance batch returned no data — will use direct API for all symbols")

    # ── Step 2: direct Yahoo v8 API for symbols that batch missed ────────────
    missing = [s for s in EGX30_SYMBOLS if s not in result]
    if missing:
        logger.info(f"Step 2: Direct Yahoo API fallback for {len(missing)} symbols: {missing}")
        for symbol in missing:
            rows = _fetch_yahoo_direct(symbol, buffer_start, end_date)
            if rows:
                result[symbol] = rows
                logger.info(f"  [direct] {symbol}: {len(rows)} days")
            else:
                logger.debug(f"  [direct] {symbol}: no data (delisted or unavailable)")
            # Small delay to avoid rate-limiting when fetching many symbols
            time.sleep(0.3)

    # ── Step 3: local DB fallback for still-missing symbols ──────────────────
    still_missing = [s for s in EGX30_SYMBOLS if s not in result]
    if still_missing:
        logger.info(f"Step 3: Database fallback for {len(still_missing)} symbols")
        for symbol in still_missing:
            rows = _fetch_from_db_fallback(symbol, buffer_start, end_date)
            if rows:
                result[symbol] = rows
                logger.info(f"  [db] {symbol}: {len(rows)} days")

    # ── Step 4: EGX30 equal-weight proxy ─────────────────────────────────────
    logger.info("Step 4: Building EGX30 equal-weight proxy benchmark...")
    proxy = _compute_egx30_proxy(result, buffer_start)
    if proxy:
        result['^EGX30'] = proxy
    else:
        logger.warning("Could not build EGX30 proxy (not enough component data)")

    logger.info(
        f"Data fetch complete: {len([k for k in result if k != '^EGX30'])} stocks + "
        f"{'EGX30 proxy' if '^EGX30' in result else 'no benchmark'}"
    )
    return result


def get_stock_name(symbol: str, lang: str = 'en') -> str:
    """Get human-readable stock name."""
    names = STOCK_NAMES.get(symbol)
    if not names:
        return symbol.replace('.CA', '')
    return names[1] if lang == 'ar' else names[0]
