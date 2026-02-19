"""
Time Machine Forecast Engine — Monte Carlo / GBM
=================================================
Vectorized 5,000-path Geometric Brownian Motion simulation for
probabilistic price forecasting of individual EGX stocks.

Called by Node.js:
    python engines/timemachine_forecast.py '<json_payload>'

Output: single JSON line to stdout.

Environment variables:
    DATABASE_URL       — PostgreSQL connection string (production)
    MC_SIMULATIONS     — number of Monte Carlo paths (default: 5000)
"""

import sys
import json
import os
import warnings
import logging
from datetime import date, timedelta

import numpy as np

warnings.filterwarnings('ignore')
logging.basicConfig(level=logging.WARNING, stream=sys.stderr)
logger = logging.getLogger(__name__)

# ── Constants ────────────────────────────────────────────────────────────────

N_SIMULATIONS = int(os.getenv('MC_SIMULATIONS', '5000'))
TRADING_DAYS_YEAR = 252
SCENARIO_DRIFT_ADJ = {
    'base': 0.0,
    'bull': 0.02,
    'bear': -0.02,
}

# EGX30 constituents for auto-selection mode
EGX30_FORECAST_SYMBOLS = [
    'COMI.CA', 'HRHO.CA', 'SWDY.CA', 'TMGH.CA', 'EKHO.CA',
    'EFIH.CA', 'ORWE.CA', 'PHDC.CA', 'ABUK.CA', 'CLHO.CA',
    'ESRS.CA', 'ETEL.CA', 'JUFO.CA', 'MNHD.CA', 'OCDI.CA',
    'HELI.CA', 'AMOC.CA', 'AUTO.CA', 'CCAP.CA', 'EGAL.CA',
    'ELEC.CA', 'FWRY.CA', 'GBCO.CA', 'ISPH.CA', 'MFPC.CA',
    'PHAR.CA', 'SKPC.CA', 'SPIN.CA', 'SUGR.CA', 'TALM.CA',
]

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

# ── Data Fetching ─────────────────────────────────────────────────────────────

def _prices_from_db(symbol: str, lookback_years: int = 5) -> list:
    """Fetch daily close prices from the local prices table."""
    try:
        db_url = os.getenv('DATABASE_URL')
        cutoff = (date.today() - timedelta(days=lookback_years * 365)).isoformat()

        if db_url:
            import psycopg2
            conn = psycopg2.connect(db_url)
            cur = conn.cursor()
            cur.execute(
                "SELECT close FROM prices WHERE symbol = %s "
                "AND date >= %s AND close IS NOT NULL ORDER BY date",
                (symbol, cutoff),
            )
        else:
            import sqlite3
            db_path = 'stocks.db'
            try:
                from config import DATABASE_PATH
                db_path = DATABASE_PATH
            except ImportError:
                pass
            conn = sqlite3.connect(db_path)
            cur = conn.cursor()
            cur.execute(
                "SELECT close FROM prices WHERE symbol = ? "
                "AND date >= ? AND close IS NOT NULL ORDER BY date",
                (symbol, cutoff),
            )

        rows = cur.fetchall()
        conn.close()
        return [float(r[0]) for r in rows if r[0] is not None]
    except Exception as exc:
        logger.warning("DB fetch failed for %s: %s", symbol, exc)
        return []


def _prices_from_yfinance(symbol: str, lookback_years: int = 5) -> list:
    """Fallback: download historical closes from Yahoo Finance."""
    try:
        import yfinance as yf
        ticker = symbol if '.' in symbol else f"{symbol}.CA"
        end = date.today()
        start = end - timedelta(days=lookback_years * 365 + 90)
        df = yf.download(ticker, start=start.isoformat(), end=end.isoformat(),
                         progress=False, auto_adjust=True)
        if df is None or df.empty:
            return []
        # Handle multi-index columns (yfinance >= 0.2.x)
        if hasattr(df.columns, 'levels'):
            close_col = next(
                (c for c in df.columns if c[0].lower() == 'close'),
                None
            )
            if close_col is None:
                return []
            closes = df[close_col].dropna()
        else:
            closes = df['Close'].dropna()
        return [float(v) for v in closes.values]
    except Exception as exc:
        logger.warning("yfinance fetch failed for %s: %s", symbol, exc)
        return []


def get_prices(symbol: str, lookback_years: int = 5) -> list:
    """Return historical close prices: DB first, yfinance fallback."""
    prices = _prices_from_db(symbol, lookback_years)
    if len(prices) >= 60:
        return prices
    yf_prices = _prices_from_yfinance(symbol, lookback_years)
    return yf_prices if len(yf_prices) > len(prices) else prices


# ── GBM Parameter Estimation ─────────────────────────────────────────────────

def compute_gbm_params(prices: list):
    """
    Compute annualized drift (μ) and volatility (σ) from log returns.
    Returns (mu_annual, sigma_annual, last_price).
    """
    p = np.array(prices, dtype=np.float64)
    log_ret = np.log(p[1:] / p[:-1])
    mu_annual = float(np.mean(log_ret) * TRADING_DAYS_YEAR)
    sigma_annual = float(np.std(log_ret, ddof=1) * np.sqrt(TRADING_DAYS_YEAR))
    return mu_annual, sigma_annual, float(p[-1])


# ── Monte Carlo Simulation ────────────────────────────────────────────────────

def run_monte_carlo(
    S0: float,
    mu: float,
    sigma: float,
    horizon_days: int,
    scenario: str = 'base',
    sentiment_score: float = 0.0,
    n_sims: int = N_SIMULATIONS,
):
    """
    Vectorized single-step GBM terminal distribution.
    S(T) = S0 * exp( (μ_adj - 0.5σ²)T + σ√T·Z ),  Z ~ N(0,1)
    Returns (terminal_prices, mu_used).
    """
    drift_adj = SCENARIO_DRIFT_ADJ.get(scenario, 0.0) + sentiment_score * 0.01
    mu_used = mu + drift_adj
    dt = horizon_days / TRADING_DAYS_YEAR

    Z = np.random.standard_normal(n_sims)
    log_terminal = (mu_used - 0.5 * sigma ** 2) * dt + sigma * np.sqrt(dt) * Z
    terminal_prices = S0 * np.exp(log_terminal)
    return terminal_prices, mu_used


def build_band_data(amount: float, mu_used: float, sigma: float, horizon_days: int) -> list:
    """
    Generate analytical GBM quantile bands at daily resolution.
    Returns list of {day, worst(p5), median(p50), best(p95)} dicts.
    Capped at 252 data points for response size.
    """
    step = max(1, horizon_days // 252)
    band = [{'day': 0, 'worst': amount, 'median': amount, 'best': amount}]

    z_05 = -1.6449  # scipy.stats.norm.ppf(0.05)
    z_50 = 0.0
    z_95 = 1.6449

    for t in range(step, horizon_days + 1, step):
        dt = t / TRADING_DAYS_YEAR
        log_mu = (mu_used - 0.5 * sigma ** 2) * dt
        log_sig = sigma * np.sqrt(dt)

        band.append({
            'day': t,
            'worst':  round(float(amount * np.exp(log_mu + z_05 * log_sig)), 2),
            'median': round(float(amount * np.exp(log_mu + z_50 * log_sig)), 2),
            'best':   round(float(amount * np.exp(log_mu + z_95 * log_sig)), 2),
        })

    # Always include the terminal point
    if band[-1]['day'] != horizon_days:
        dt = horizon_days / TRADING_DAYS_YEAR
        log_mu = (mu_used - 0.5 * sigma ** 2) * dt
        log_sig = sigma * np.sqrt(dt)
        band.append({
            'day': horizon_days,
            'worst':  round(float(amount * np.exp(log_mu + z_05 * log_sig)), 2),
            'median': round(float(amount * np.exp(log_mu + z_50 * log_sig)), 2),
            'best':   round(float(amount * np.exp(log_mu + z_95 * log_sig)), 2),
        })

    return band


# ── Main Simulation Entry ─────────────────────────────────────────────────────

def simulate(payload: dict) -> dict:
    """Run the full Monte Carlo forecast. Returns a result dict."""
    symbol = str(payload.get('symbol', '')).strip().upper()
    amount = float(payload.get('investment_amount', 10000))
    horizon_days = int(payload.get('horizon', 252))
    scenario = str(payload.get('scenario', 'base')).lower()
    sentiment_score = float(payload.get('sentiment_score', 0.0))

    # Input validation
    if not symbol:
        return {'ok': False, 'error': 'symbol is required'}
    if amount <= 0 or amount > 100_000_000:
        return {'ok': False, 'error': 'amount must be between 1 and 100,000,000'}
    if horizon_days < 5 or horizon_days > 1825:
        return {'ok': False, 'error': 'horizon must be between 5 and 1825 days (max 5 years)'}
    if scenario not in SCENARIO_DRIFT_ADJ:
        return {'ok': False, 'error': f"scenario must be one of: {list(SCENARIO_DRIFT_ADJ.keys())}"}

    prices = get_prices(symbol)
    if len(prices) < 60:
        return {
            'ok': False,
            'error': f'Insufficient historical data for {symbol} '
                     f'(need >= 60 trading days, found {len(prices)})',
        }

    mu, sigma, S0 = compute_gbm_params(prices)

    shares = amount / S0
    terminal_prices, mu_used = run_monte_carlo(
        S0=S0, mu=mu, sigma=sigma,
        horizon_days=horizon_days,
        scenario=scenario,
        sentiment_score=sentiment_score,
        n_sims=N_SIMULATIONS,
    )
    terminal_values = shares * terminal_prices

    # Statistics
    pct = np.percentile(terminal_values, [5, 25, 50, 75, 95])
    expected = float(np.mean(terminal_values))
    prob_pos = float(np.mean(terminal_values > amount)) * 100

    # Histogram (30 bins)
    counts, edges = np.histogram(terminal_values, bins=30)

    # Analytical band (for smooth chart)
    band_data = build_band_data(amount, mu_used, sigma, horizon_days)

    return {
        'ok': True,
        'symbol': symbol,
        'investment_amount': amount,
        'last_price': round(S0, 4),
        'shares': round(shares, 6),
        'horizon_days': horizon_days,
        'scenario': scenario,
        'simulations_count': N_SIMULATIONS,
        'drift_annual_pct': round(mu * 100, 2),
        'drift_used_pct': round(mu_used * 100, 2),
        'volatility_annual_pct': round(sigma * 100, 2),
        'data_points': len(prices),
        # Result statistics
        'expected_value': round(expected, 2),
        'expected_return_pct': round((expected / amount - 1) * 100, 2),
        'median_value': round(float(pct[2]), 2),
        'median_return_pct': round((float(pct[2]) / amount - 1) * 100, 2),
        'worst_case_value': round(float(pct[0]), 2),
        'best_case_value': round(float(pct[4]), 2),
        'quartile_25': round(float(pct[1]), 2),
        'quartile_75': round(float(pct[3]), 2),
        'probability_positive': round(prob_pos, 1),
        # Visualisation data
        'histogram': {
            'counts': counts.tolist(),
            'edges': [round(float(e), 2) for e in edges.tolist()],
        },
        'band_data': band_data,
    }


# ── Auto-selection ────────────────────────────────────────────────────────────

def _batch_prices_yfinance(symbols: list, lookback_years: int = 3) -> dict:
    """
    ONE batch yfinance download for all symbols.
    Returns {symbol: [close, ...]} for symbols with >= 60 data points.
    Much faster than 30 sequential downloads.
    """
    try:
        import yfinance as yf
        end = date.today()
        start = (end - timedelta(days=lookback_years * 365 + 60)).isoformat()

        data = yf.download(
            tickers=symbols,
            start=start,
            end=end.isoformat(),
            interval='1d',
            group_by='ticker',
            auto_adjust=True,
            progress=False,
            threads=True,
        )
        if data is None or data.empty:
            return {}

        result = {}
        for sym in symbols:
            try:
                # With group_by='ticker', columns are multi-index (metric, symbol)
                if len(symbols) == 1:
                    df = data
                    close_col = 'Close'
                else:
                    df = data[sym]
                    close_col = 'Close'

                closes = df[close_col].dropna()
                prices = [float(v) for v in closes.values
                          if v is not None and not np.isnan(float(v))]
                if len(prices) >= 60:
                    result[sym] = prices
            except Exception as e:
                logger.debug("batch parse %s: %s", sym, e)

        return result
    except ImportError:
        logger.warning("yfinance not installed; auto-select limited to DB data")
        return {}
    except Exception as e:
        logger.warning("batch yfinance download failed: %s", e)
        return {}


def auto_select_best(amount: float, horizon_days: int, scenario: str,
                     sentiment_score: float = 0.0) -> dict:
    """
    Fetch prices for all EGX30 stocks in as few network calls as possible,
    run MC on each in numpy (fast), rank by score, return best.

    Strategy:
      1. DB lookup for all 30 symbols (fast, no network)
      2. ONE batch yfinance download for any DB misses
      3. Vectorised MC for each stock (numpy, <100 ms each)
    """
    LOOKBACK = 3  # years

    # ── Step 1: DB lookup (fast) ──────────────────────────────────────────────
    all_prices = {}
    for sym in EGX30_FORECAST_SYMBOLS:
        p = _prices_from_db(sym, LOOKBACK)
        if len(p) >= 60:
            all_prices[sym] = p

    # ── Step 2: One batch yfinance call for DB misses ─────────────────────────
    missing = [s for s in EGX30_FORECAST_SYMBOLS if s not in all_prices]
    if missing:
        logger.info("auto-select: %d DB hits, %d need yfinance batch",
                    len(all_prices), len(missing))
        batch = _batch_prices_yfinance(missing, LOOKBACK)
        all_prices.update(batch)
    else:
        logger.info("auto-select: all %d stocks from DB", len(all_prices))

    if not all_prices:
        return {
            'ok': False,
            'error': 'Could not fetch price data for any EGX30 stock. '
                     'Market data may be temporarily unavailable.',
        }

    # ── Step 3: Vectorised MC for each stock ──────────────────────────────────
    ranked = []
    for sym, prices in all_prices.items():
        try:
            mu, sigma, S0 = compute_gbm_params(prices)
            shares = amount / S0
            terminal_prices, mu_used = run_monte_carlo(
                S0=S0, mu=mu, sigma=sigma,
                horizon_days=horizon_days,
                scenario=scenario,
                sentiment_score=sentiment_score,
            )
            tv = shares * terminal_prices
            expected = float(np.mean(tv))
            prob_pos = float(np.mean(tv > amount)) * 100
            exp_ret_pct = round((expected / amount - 1) * 100, 2)
            score = (prob_pos / 100.0) * (1.0 + max(exp_ret_pct, 0.0) / 100.0)
            ranked.append({
                'sym': sym, 'prices': prices,
                'mu': mu, 'mu_used': mu_used, 'sigma': sigma, 'S0': S0,
                'tv': tv, 'expected': expected,
                'prob_pos': prob_pos, 'exp_ret_pct': exp_ret_pct, 'score': score,
                'pct': np.percentile(tv, [5, 25, 50, 75, 95]),
            })
        except Exception as exc:
            logger.debug("MC skip %s: %s", sym, exc)

    if not ranked:
        return {
            'ok': False,
            'error': 'Monte Carlo failed for all available EGX30 stocks.',
        }

    ranked.sort(key=lambda x: x['score'], reverse=True)
    w = ranked[0]  # winner

    # ── Step 4: Build full result for the winner ──────────────────────────────
    counts, edges = np.histogram(w['tv'], bins=30)
    band_data = build_band_data(amount, w['mu_used'], w['sigma'], horizon_days)
    name_en, name_ar = STOCK_NAMES.get(w['sym'], (w['sym'].replace('.CA', ''),
                                                    w['sym'].replace('.CA', '')))

    top5 = []
    for r in ranked[:5]:
        n_en, n_ar = STOCK_NAMES.get(r['sym'], (r['sym'].replace('.CA', ''),
                                                 r['sym'].replace('.CA', '')))
        top5.append({
            'symbol': r['sym'].replace('.CA', ''),
            'name_en': n_en, 'name_ar': n_ar,
            'score': round(r['score'], 4),
            'probability_positive': round(r['prob_pos'], 1),
            'expected_return_pct': r['exp_ret_pct'],
            'volatility_annual_pct': round(r['sigma'] * 100, 2),
        })

    pct = w['pct']
    return {
        'ok': True,
        'symbol': w['sym'],
        'investment_amount': amount,
        'last_price': round(w['S0'], 4),
        'shares': round(amount / w['S0'], 6),
        'horizon_days': horizon_days,
        'scenario': scenario,
        'simulations_count': N_SIMULATIONS,
        'drift_annual_pct': round(w['mu'] * 100, 2),
        'drift_used_pct': round(w['mu_used'] * 100, 2),
        'volatility_annual_pct': round(w['sigma'] * 100, 2),
        'data_points': len(w['prices']),
        'expected_value': round(w['expected'], 2),
        'expected_return_pct': w['exp_ret_pct'],
        'median_value': round(float(pct[2]), 2),
        'median_return_pct': round((float(pct[2]) / amount - 1) * 100, 2),
        'worst_case_value': round(float(pct[0]), 2),
        'best_case_value': round(float(pct[4]), 2),
        'quartile_25': round(float(pct[1]), 2),
        'quartile_75': round(float(pct[3]), 2),
        'probability_positive': round(w['prob_pos'], 1),
        'histogram': {
            'counts': counts.tolist(),
            'edges': [round(float(e), 2) for e in edges.tolist()],
        },
        'band_data': band_data,
        # Auto-select fields
        'auto_selected': True,
        'auto_symbol_name_en': name_en,
        'auto_symbol_name_ar': name_ar,
        'auto_ranking': top5,
    }


# ── Entry Point ───────────────────────────────────────────────────────────────

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print(json.dumps({'ok': False, 'error': 'Usage: timemachine_forecast.py <json_payload>'}))
        sys.exit(1)

    try:
        payload = json.loads(sys.argv[1])
        if payload.get('auto'):
            result = auto_select_best(
                amount=float(payload.get('investment_amount', 10000)),
                horizon_days=int(payload.get('horizon', 21)),
                scenario=str(payload.get('scenario', 'base')).lower(),
                sentiment_score=float(payload.get('sentiment_score', 0.0)),
            )
        else:
            result = simulate(payload)
        print(json.dumps(result))
    except json.JSONDecodeError as e:
        print(json.dumps({'ok': False, 'error': f'Invalid JSON payload: {e}'}))
        sys.exit(1)
    except Exception as e:
        logger.exception("Unhandled error in forecast engine")
        print(json.dumps({'ok': False, 'error': str(e)}))
        sys.exit(1)
