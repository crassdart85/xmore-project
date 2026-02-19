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


# ── Entry Point ───────────────────────────────────────────────────────────────

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print(json.dumps({'ok': False, 'error': 'Usage: timemachine_forecast.py <json_payload>'}))
        sys.exit(1)

    try:
        payload = json.loads(sys.argv[1])
        result = simulate(payload)
        print(json.dumps(result))
    except json.JSONDecodeError as e:
        print(json.dumps({'ok': False, 'error': f'Invalid JSON payload: {e}'}))
        sys.exit(1)
    except Exception as e:
        logger.exception("Unhandled error in forecast engine")
        print(json.dumps({'ok': False, 'error': str(e)}))
        sys.exit(1)
