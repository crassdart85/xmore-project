"""
Professional Trading Metrics Calculator

All metrics are computed from existing tables:
- trade_recommendations (for signal-level accuracy)
- user_positions (for trade-level P&L)

Supports:
- Global, per-agent, per-stock, per-sector slicing
- Rolling 30/60/90-day windows
- Live-only filtering (excludes backtest data)
"""

import math
import os
from database import get_connection

DATABASE_URL = os.getenv('DATABASE_URL')


# ─── SQL HELPERS ───────────────────────────────────────────────

def _ph(index):
    """Return placeholder for parameterized query."""
    return '%s' if DATABASE_URL else '?'


def _query(cursor, sql, params=None):
    """Execute query and return list of dicts."""
    cursor.execute(sql, params or [])
    columns = [desc[0] for desc in cursor.description] if cursor.description else []
    rows = cursor.fetchall()
    result = []
    for row in rows:
        if isinstance(row, dict):
            result.append(row)
        else:
            result.append(dict(zip(columns, row)))
    return result


# ─── CORE METRICS QUERY ───────────────────────────────────────

def get_performance_summary(
    user_id: int = None,
    days: int = 90,
    live_only: bool = True,
    action_filter: str = None,
    symbol_filter: str = None,
    sector_filter: str = None
) -> dict:
    """
    Comprehensive performance summary.
    Returns all professional metrics in one call.
    """
    with get_connection() as conn:
        cursor = conn.cursor()

        conditions = ["tr.was_correct IS NOT NULL"]
        params = []

        if user_id:
            conditions.append(f"tr.user_id = {_ph(1)}")
            params.append(user_id)

        if live_only:
            if DATABASE_URL:
                conditions.append("tr.is_live = TRUE")
            else:
                conditions.append("(tr.is_live = 1 OR tr.is_live IS NULL)")

        if days:
            if DATABASE_URL:
                conditions.append(f"tr.recommendation_date >= CURRENT_DATE - {_ph(len(params)+1)}::integer")
            else:
                conditions.append(f"tr.recommendation_date >= date('now', '-' || {_ph(len(params)+1)} || ' days')")
            params.append(days)

        if action_filter:
            conditions.append(f"tr.action = {_ph(len(params)+1)}")
            params.append(action_filter.upper())

        if symbol_filter:
            conditions.append(f"tr.symbol = {_ph(len(params)+1)}")
            params.append(symbol_filter.upper())

        where = " AND ".join(conditions)

        sql = f"""
            SELECT
                tr.action, tr.signal, tr.confidence, tr.conviction,
                tr.actual_next_day_return AS return_1d,
                tr.actual_5day_return AS return_5d,
                tr.benchmark_1d_return AS bench_1d,
                tr.benchmark_5d_return AS bench_5d,
                tr.alpha_1d, tr.alpha_5d,
                tr.was_correct,
                tr.recommendation_date,
                tr.symbol
            FROM trade_recommendations tr
            WHERE {where}
            ORDER BY tr.recommendation_date ASC
        """

        try:
            rows = _query(cursor, sql, params)
        except Exception:
            return empty_metrics()

        if not rows:
            return empty_metrics()

        # Extract return series
        returns_1d = [float(r["return_1d"]) for r in rows if r.get("return_1d") is not None]
        returns_5d = [float(r["return_5d"]) for r in rows if r.get("return_5d") is not None]
        bench_1d = [float(r["bench_1d"]) for r in rows if r.get("bench_1d") is not None]
        alphas_1d = [float(r["alpha_1d"]) for r in rows if r.get("alpha_1d") is not None]
        correct = [r["was_correct"] for r in rows if r.get("was_correct") is not None]

        return {
            # Core counts
            "total_predictions": len(rows),
            "resolved": len(correct),
            "period_days": days,
            "live_only": live_only,

            # Win/Loss
            "wins": sum(1 for c in correct if c),
            "losses": sum(1 for c in correct if not c),
            "win_rate": round(sum(1 for c in correct if c) / len(correct) * 100, 1) if correct else 0,

            # Returns
            "avg_return_1d": round(avg(returns_1d), 3),
            "avg_return_5d": round(avg(returns_5d), 3),
            "cumulative_return": round(cumulative_return(returns_1d), 2),
            "best_trade": round(max(returns_1d), 2) if returns_1d else 0,
            "worst_trade": round(min(returns_1d), 2) if returns_1d else 0,

            # Benchmark Comparison
            "avg_benchmark_1d": round(avg(bench_1d), 3),
            "avg_alpha_1d": round(avg(alphas_1d), 3),
            "cumulative_alpha": round(sum(alphas_1d), 2) if alphas_1d else 0,
            "beat_benchmark_pct": round(
                sum(1 for a in alphas_1d if a > 0) / len(alphas_1d) * 100, 1
            ) if alphas_1d else 0,

            # Risk Metrics
            "sharpe_ratio": round(sharpe_ratio(returns_1d), 2),
            "sortino_ratio": round(sortino_ratio(returns_1d), 2),
            "max_drawdown": round(max_drawdown(returns_1d), 2),
            "volatility": round(stddev(returns_1d), 3),
            "profit_factor": round(profit_factor(returns_1d), 2),

            # Metadata
            "first_prediction": str(rows[0]["recommendation_date"]),
            "last_prediction": str(rows[-1]["recommendation_date"]),
            "live_trade_count": len(rows),
            "meets_minimum": len(rows) >= 100,
        }


# ─── METRIC CALCULATIONS ──────────────────────────────────────

def sharpe_ratio(returns: list, risk_free_rate: float = 0.0, annualize: bool = True) -> float:
    """
    Sharpe Ratio = (avg_return - risk_free_rate) / stdev(returns)
    Annualized assuming ~252 trading days.
    """
    if len(returns) < 2:
        return 0.0

    mean = avg(returns)
    std = stddev(returns)

    if std == 0:
        return 0.0

    daily_sharpe = (mean - risk_free_rate) / std

    if annualize:
        return daily_sharpe * math.sqrt(252)
    return daily_sharpe


def sortino_ratio(returns: list, risk_free_rate: float = 0.0) -> float:
    """
    Sortino Ratio = (avg_return - risk_free_rate) / downside_deviation
    Only penalizes negative returns (not all volatility).
    """
    if len(returns) < 2:
        return 0.0

    mean = avg(returns)
    downside = [r for r in returns if r < 0]

    if not downside:
        return 99.9  # No losses → excellent

    downside_std = stddev(downside)
    if downside_std == 0:
        return 99.9

    return ((mean - risk_free_rate) / downside_std) * math.sqrt(252)


def max_drawdown(returns: list) -> float:
    """
    Maximum peak-to-trough decline in cumulative returns.
    Returns as negative percentage.
    """
    if not returns:
        return 0.0

    cumulative = []
    running = 0
    for r in returns:
        running += r
        cumulative.append(running)

    peak = cumulative[0]
    max_dd = 0

    for val in cumulative:
        if val > peak:
            peak = val
        dd = val - peak
        if dd < max_dd:
            max_dd = dd

    return max_dd


def profit_factor(returns: list) -> float:
    """
    Profit Factor = sum(wins) / |sum(losses)|
    > 1.0 means profitable, > 2.0 is excellent.
    """
    gains = sum(r for r in returns if r > 0)
    losses = abs(sum(r for r in returns if r < 0))

    if losses == 0:
        return 99.9 if gains > 0 else 0.0

    return gains / losses


def cumulative_return(returns: list) -> float:
    """Cumulative return from a series of percentage returns."""
    if not returns:
        return 0.0

    cumulative = 1.0
    for r in returns:
        cumulative *= (1 + r / 100)

    return (cumulative - 1) * 100


# ─── ROLLING WINDOWS ──────────────────────────────────────────

def get_rolling_metrics(user_id: int = None, windows: list = None) -> dict:
    """
    Returns performance metrics for multiple rolling windows.
    Used for the dashboard sparkline and trend display.
    """
    if windows is None:
        windows = [30, 60, 90]

    results = {}
    for w in windows:
        metrics = get_performance_summary(user_id=user_id, days=w, live_only=True)
        results[f"{w}d"] = {
            "win_rate": metrics["win_rate"],
            "sharpe": metrics["sharpe_ratio"],
            "avg_return": metrics["avg_return_1d"],
            "total_trades": metrics["total_predictions"],
            "max_drawdown": metrics["max_drawdown"],
            "alpha": metrics["avg_alpha_1d"]
        }
    return results


# ─── PER-AGENT METRICS ────────────────────────────────────────

def get_agent_comparison(days: int = 90) -> list:
    """
    Compare all agents' accuracy over the given window.
    Uses agent_performance_daily snapshots.
    """
    with get_connection() as conn:
        cursor = conn.cursor()

        try:
            result = _query(cursor, """
                SELECT
                    agent_name,
                    predictions_30d, correct_30d, win_rate_30d,
                    avg_confidence_30d,
                    predictions_90d, correct_90d, win_rate_90d
                FROM agent_performance_daily
                WHERE snapshot_date = (SELECT MAX(snapshot_date) FROM agent_performance_daily)
                ORDER BY win_rate_30d DESC NULLS LAST
            """)
        except Exception:
            return []

        return [
            {
                "agent": r["agent_name"],
                "predictions_30d": int(r.get("predictions_30d", 0) or 0),
                "win_rate_30d": float(r.get("win_rate_30d", 0) or 0),
                "avg_confidence_30d": float(r.get("avg_confidence_30d", 0) or 0),
                "predictions_90d": int(r.get("predictions_90d", 0) or 0),
                "win_rate_90d": float(r.get("win_rate_90d", 0) or 0),
            }
            for r in result
        ]


# ─── PER-STOCK METRICS ────────────────────────────────────────

def get_stock_performance(days: int = 90) -> list:
    """
    Performance breakdown per stock.
    """
    with get_connection() as conn:
        cursor = conn.cursor()

        if DATABASE_URL:
            live_filter = "tr.is_live = TRUE"
            date_filter = "tr.recommendation_date >= CURRENT_DATE - %s"
        else:
            live_filter = "(tr.is_live = 1 OR tr.is_live IS NULL)"
            date_filter = "tr.recommendation_date >= date('now', '-' || ? || ' days')"

        # Try joining with egx30_stocks for names; fallback if table not available
        try:
            result = _query(cursor, f"""
                SELECT
                    tr.symbol, s.name_en, s.sector_en,
                    COUNT(*) AS total_recs,
                    SUM(CASE WHEN tr.was_correct = {'TRUE' if DATABASE_URL else '1'} THEN 1 ELSE 0 END) AS correct,
                    {'ROUND(AVG(tr.actual_next_day_return)::numeric, 3)' if DATABASE_URL else 'ROUND(AVG(tr.actual_next_day_return), 3)'} AS avg_return,
                    {'ROUND(AVG(tr.alpha_1d)::numeric, 3)' if DATABASE_URL else 'ROUND(AVG(tr.alpha_1d), 3)'} AS avg_alpha,
                    {'ROUND((SUM(CASE WHEN tr.was_correct = TRUE THEN 1 ELSE 0 END))::numeric / NULLIF(COUNT(*), 0) * 100, 1)' if DATABASE_URL else 'ROUND(CAST(SUM(CASE WHEN tr.was_correct = 1 THEN 1 ELSE 0 END) AS REAL) / MAX(COUNT(*), 1) * 100, 1)'} AS win_rate
                FROM trade_recommendations tr
                LEFT JOIN egx30_stocks s ON tr.symbol = s.symbol
                WHERE tr.was_correct IS NOT NULL
                AND {live_filter}
                AND {date_filter}
                GROUP BY tr.symbol, s.name_en, s.sector_en
                HAVING COUNT(*) >= 3
                ORDER BY avg_alpha DESC
            """, [days])
        except Exception:
            result = []

        return [dict(r) for r in result]


# ─── EQUITY CURVE DATA ────────────────────────────────────────

def get_equity_curve(user_id: int = None, days: int = 180) -> dict:
    """
    Daily cumulative returns for equity curve chart.
    Returns both Xmore and EGX30 series for overlay.
    """
    with get_connection() as conn:
        cursor = conn.cursor()

        conditions = [
            "tr.actual_next_day_return IS NOT NULL"
        ]
        params = []

        if DATABASE_URL:
            conditions.append("tr.is_live = TRUE")
            conditions.append(f"tr.recommendation_date >= CURRENT_DATE - {_ph(1)}::integer")
        else:
            conditions.append("(tr.is_live = 1 OR tr.is_live IS NULL)")
            conditions.append(f"tr.recommendation_date >= date('now', '-' || {_ph(1)} || ' days')")
        params.append(days)

        if user_id:
            conditions.append(f"tr.user_id = {_ph(len(params)+1)}")
            params.append(user_id)

        where = " AND ".join(conditions)

        try:
            if DATABASE_URL:
                daily = _query(cursor, f"""
                    SELECT
                        tr.recommendation_date AS date,
                        ROUND(AVG(tr.actual_next_day_return)::numeric, 4) AS xmore_return,
                        ROUND(AVG(tr.benchmark_1d_return)::numeric, 4) AS benchmark_return
                    FROM trade_recommendations tr
                    WHERE {where}
                    GROUP BY tr.recommendation_date
                    ORDER BY tr.recommendation_date ASC
                """, params)
            else:
                daily = _query(cursor, f"""
                    SELECT
                        tr.recommendation_date AS date,
                        ROUND(AVG(tr.actual_next_day_return), 4) AS xmore_return,
                        ROUND(AVG(tr.benchmark_1d_return), 4) AS benchmark_return
                    FROM trade_recommendations tr
                    WHERE {where}
                    GROUP BY tr.recommendation_date
                    ORDER BY tr.recommendation_date ASC
                """, params)
        except Exception:
            return {"series": [], "total_xmore": 0, "total_egx30": 0, "total_alpha": 0}

        # Build cumulative series
        xmore_cum = 0
        bench_cum = 0
        series = []

        for d in daily:
            xmore_cum += float(d.get("xmore_return", 0) or 0)
            bench_cum += float(d.get("benchmark_return", 0) or 0)
            series.append({
                "date": str(d["date"]),
                "xmore": round(xmore_cum, 2),
                "egx30": round(bench_cum, 2),
                "alpha": round(xmore_cum - bench_cum, 2)
            })

        return {
            "series": series,
            "total_xmore": round(xmore_cum, 2),
            "total_egx30": round(bench_cum, 2),
            "total_alpha": round(xmore_cum - bench_cum, 2)
        }


# ─── HELPERS ──────────────────────────────────────────────────

def avg(lst: list) -> float:
    return sum(lst) / len(lst) if lst else 0.0


def stddev(lst: list) -> float:
    if len(lst) < 2:
        return 0.0
    m = avg(lst)
    return math.sqrt(sum((x - m) ** 2 for x in lst) / (len(lst) - 1))


def empty_metrics() -> dict:
    return {
        "total_predictions": 0, "resolved": 0, "wins": 0, "losses": 0,
        "win_rate": 0, "avg_return_1d": 0, "avg_return_5d": 0,
        "cumulative_return": 0, "sharpe_ratio": 0, "sortino_ratio": 0,
        "max_drawdown": 0, "volatility": 0, "profit_factor": 0,
        "avg_alpha_1d": 0, "avg_benchmark_1d": 0, "cumulative_alpha": 0,
        "beat_benchmark_pct": 0, "best_trade": 0, "worst_trade": 0,
        "meets_minimum": False, "live_trade_count": 0,
        "first_prediction": None, "last_prediction": None,
        "period_days": 0, "live_only": True
    }
