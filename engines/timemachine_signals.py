"""
Time Machine Signal Generator
Takes historical price data and generates what Xmore's agents WOULD HAVE
recommended on each trading day.

This does NOT write to the database. Everything stays in memory.

Uses simplified versions of the same 4 agents:
  1. MA_Crossover — SMA(10) vs SMA(30)
  2. RSI — oversold recovery (RSI 30-50)
  3. Volume_Spike — volume > 1.5x 20-day average
  4. Trend + Momentum — price above SMA(50) + positive 5-day momentum
"""

import logging

logger = logging.getLogger(__name__)

try:
    import numpy as np
    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False


def _mean(arr):
    """Pure Python mean fallback."""
    if not arr:
        return 0
    return sum(arr) / len(arr)


def _std(arr):
    """Pure Python standard deviation fallback."""
    if len(arr) < 2:
        return 0
    m = _mean(arr)
    return (sum((x - m) ** 2 for x in arr) / len(arr)) ** 0.5


def generate_signals_for_period(price_data: dict, start_date: str, end_date: str) -> list:
    """
    For each trading day in [start_date, end_date], run the agent pipeline
    on all available stocks using price history up to that day.

    Returns list of signal dicts for BUY/STRONG_BUY signals only.
    """
    signals = []
    trading_days = _get_trading_days(price_data, start_date, end_date)

    logger.info(f"Generating signals for {len(trading_days)} trading days, {len(price_data) - 1} stocks")

    for day in trading_days:
        for symbol, prices in price_data.items():
            if symbol == '^EGX30':
                continue  # Skip benchmark

            # Get prices up to this day (for indicator calculation)
            hist = [p for p in prices if p['date'] <= day]
            if len(hist) < 50:
                continue  # Need minimum 50 days for SMA(50)

            signal = _run_agents_on_history(symbol, hist, day)
            if signal and signal['action'] in ('buy', 'strong_buy'):
                signals.append(signal)

    logger.info(f"Generated {len(signals)} buy/strong_buy signals")
    return signals


def _run_agents_on_history(symbol: str, hist: list, date: str) -> dict:
    """
    Simplified multi-agent analysis for backtesting.

    Agent 1: MA_Crossover — SMA(10) crosses above SMA(30)
    Agent 2: RSI — RSI(14) between 30-50 (oversold recovery)
    Agent 3: Volume_Spike — Volume > 1.5x 20-day average
    Agent 4: Trend + Momentum — price above SMA(50) + positive 5d momentum

    Consensus: votes / 4 agents. Minimum 0.50 to generate signal.
    """
    closes = [p['close'] for p in hist]
    volumes = [p['volume'] for p in hist]
    current_price = closes[-1]

    if len(closes) < 50:
        return None

    mean_fn = np.mean if HAS_NUMPY else _mean
    votes = 0
    total_agents = 4

    # --- Agent 1: MA Crossover ---
    sma10 = mean_fn(closes[-10:])
    sma30 = mean_fn(closes[-30:])
    sma10_prev = mean_fn(closes[-11:-1])
    sma30_prev = mean_fn(closes[-31:-1])
    ma_buy = (sma10 > sma30) and (sma10_prev <= sma30_prev)  # Fresh crossover
    ma_bullish = sma10 > sma30  # Already above
    if ma_buy:
        votes += 1
    elif ma_bullish:
        votes += 0.5

    # --- Agent 2: RSI ---
    deltas = [closes[i] - closes[i - 1] for i in range(-14, 0)]
    gains = [d for d in deltas if d > 0]
    losses = [-d for d in deltas if d < 0]
    avg_gain = mean_fn(gains) if gains else 0
    avg_loss = mean_fn(losses) if losses else 0.001
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    if 30 <= rsi <= 50:
        votes += 1  # Oversold recovery
    elif rsi < 30:
        votes += 0.75  # Deeply oversold — contrarian buy

    # --- Agent 3: Volume Spike ---
    avg_vol = mean_fn(volumes[-20:]) if len(volumes) >= 20 else mean_fn(volumes)
    if avg_vol > 0 and volumes[-1] > 1.5 * avg_vol:
        votes += 1

    # --- Agent 4: Trend + Momentum (simplified ML proxy) ---
    sma50 = mean_fn(closes[-50:])
    momentum_5d = (closes[-1] - closes[-6]) / closes[-6] if closes[-6] > 0 else 0
    if current_price > sma50 and momentum_5d > 0.01:
        votes += 1
    elif current_price > sma50:
        votes += 0.5

    # --- Consensus ---
    consensus_score = round(votes / total_agents, 2)
    agents_agree = int(round(votes))

    if consensus_score < 0.50:
        return None  # Not enough conviction

    action = 'strong_buy' if consensus_score >= 0.75 else 'buy'

    # Position targets
    stop_loss_pct = 0.05 if action == 'strong_buy' else 0.07
    target_pct = 0.15 if action == 'strong_buy' else 0.10

    return {
        'date': date,
        'stock_symbol': symbol,
        'action': action,
        'consensus_score': consensus_score,
        'agents_agree': agents_agree,
        'entry_price': round(current_price, 2),
        'stop_loss_price': round(current_price * (1 - stop_loss_pct), 2),
        'target_price': round(current_price * (1 + target_pct), 2),
    }


def _get_trading_days(price_data: dict, start_date: str, end_date: str) -> list:
    """Extract sorted unique trading days across all symbols within the date range."""
    days = set()
    for symbol, prices in price_data.items():
        for p in prices:
            if start_date <= p['date'] <= end_date:
                days.add(p['date'])
    return sorted(days)
