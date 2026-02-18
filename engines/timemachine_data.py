"""
Time Machine Data Fetcher
Fetches historical OHLCV from Yahoo Finance for a given date range.
Called by timemachine.py orchestrator. All data stays in-memory — nothing is
written to the database.

EGX stocks use .CA suffix on Yahoo Finance (e.g. COMI.CA, HRHO.CA).
"""

import logging
from datetime import datetime, timedelta

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


def fetch_historical_prices(start_date: str, end_date: str) -> dict:
    """
    Fetch OHLCV data from Yahoo Finance for all EGX30 stocks + EGX30 index.

    Args:
        start_date: "YYYY-MM-DD"
        end_date: "YYYY-MM-DD"

    Returns:
        {
          "COMI.CA": [
            {"date": "2025-06-15", "open": 62.0, "high": 63.5, "low": 61.8, "close": 63.2, "volume": 1500000},
            ...
          ],
          "^EGX30": [...],
          ...
        }
    """
    try:
        import yfinance as yf
    except ImportError:
        logger.error("yfinance not installed")
        return {}

    all_symbols = EGX30_SYMBOLS + ['^EGX30']

    # Add 60 days buffer before start_date so TA indicators have warmup data
    buffer_start = (datetime.strptime(start_date, '%Y-%m-%d') - timedelta(days=60)).strftime('%Y-%m-%d')

    logger.info(f"Fetching {len(all_symbols)} symbols from {buffer_start} to {end_date}")

    try:
        data = yf.download(
            tickers=all_symbols,
            start=buffer_start,
            end=end_date,
            interval='1d',
            group_by='ticker',
            auto_adjust=True,
            progress=False,
            threads=True
        )
    except Exception as e:
        logger.error(f"yfinance download failed: {e}")
        return {}

    if data is None or data.empty:
        logger.warning("yfinance returned empty data")
        return {}

    result = {}
    for symbol in all_symbols:
        try:
            if len(all_symbols) > 1:
                df = data[symbol].dropna(subset=['Close'])
            else:
                df = data.dropna(subset=['Close'])

            rows = []
            for idx, row in df.iterrows():
                rows.append({
                    'date': idx.strftime('%Y-%m-%d'),
                    'open': round(float(row['Open']), 2),
                    'high': round(float(row['High']), 2),
                    'low': round(float(row['Low']), 2),
                    'close': round(float(row['Close']), 2),
                    'volume': int(row['Volume']) if row['Volume'] > 0 else 0
                })
            if rows:
                result[symbol] = rows
                logger.info(f"  {symbol}: {len(rows)} days")
        except Exception as e:
            # Skip symbols that fail — some EGX stocks may not have full history
            logger.debug(f"  {symbol}: skipped ({e})")

    logger.info(f"Fetched data for {len(result)} symbols")
    return result


def get_stock_name(symbol: str, lang: str = 'en') -> str:
    """Get human-readable stock name."""
    names = STOCK_NAMES.get(symbol)
    if not names:
        return symbol.replace('.CA', '')
    return names[1] if lang == 'ar' else names[0]
