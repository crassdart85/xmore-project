"""
Daily Market Briefing Generator.
Pure computation functions — no DB access. Data is passed in, structured dicts returned.
Called from run_agents.py after trade recommendations are generated.
"""

import json
from collections import defaultdict


def generate_market_pulse(consensus_map, prices_map, prev_prices_map, stocks_metadata):
    """
    Compute EGX-wide market direction, breadth, volume context, and top movers.

    Args:
        consensus_map: {symbol: {final_signal, confidence, conviction, bull_score, bear_score, risk_action, ...}}
        prices_map: {symbol: {date, close, volume}}
        prev_prices_map: {symbol: {date, close, volume}}
        stocks_metadata: {symbol: {name_en, name_ar, sector_en, sector_ar}}

    Returns:
        dict with direction, confidence, breadth, volume, top movers.
    """
    if not consensus_map:
        return {
            "direction": "FLAT", "confidence": 0, "stocks_up": 0, "stocks_down": 0,
            "stocks_flat": 0, "breadth_pct": 0, "volume_vs_avg": 1.0,
            "top_gainers": [], "top_losers": []
        }

    stocks_up = 0
    stocks_down = 0
    stocks_flat = 0
    total_confidence = 0

    for symbol, c in consensus_map.items():
        signal = c.get("final_signal", {})
        prediction = signal.get("prediction", "FLAT") if isinstance(signal, dict) else signal
        confidence = signal.get("confidence", 0) if isinstance(signal, dict) else c.get("confidence", 0)
        total_confidence += confidence

        if prediction == "UP":
            stocks_up += 1
        elif prediction == "DOWN":
            stocks_down += 1
        else:
            stocks_flat += 1

    total = len(consensus_map)
    avg_confidence = round(total_confidence / total, 1) if total > 0 else 0

    # Market direction
    if total > 0 and stocks_up / total >= 0.6:
        direction = "BULLISH"
    elif total > 0 and stocks_down / total >= 0.6:
        direction = "BEARISH"
    else:
        direction = "MIXED"

    breadth_pct = round((stocks_up / total) * 100, 1) if total > 0 else 0

    # Volume context: ratio of today's total volume vs previous day
    today_vol = sum(p.get("volume", 0) or 0 for p in prices_map.values())
    prev_vol = sum(p.get("volume", 0) or 0 for p in prev_prices_map.values())
    volume_vs_avg = round(today_vol / prev_vol, 2) if prev_vol > 0 else 1.0

    # Top movers by price change %
    movers = []
    for symbol in consensus_map:
        today = prices_map.get(symbol)
        prev = prev_prices_map.get(symbol)
        meta = stocks_metadata.get(symbol, {})
        if today and prev and prev.get("close") and prev["close"] > 0:
            change_pct = round(((today["close"] - prev["close"]) / prev["close"]) * 100, 2)
            movers.append({
                "symbol": symbol,
                "name_en": meta.get("name_en", symbol),
                "name_ar": meta.get("name_ar", symbol),
                "change_pct": change_pct
            })

    movers.sort(key=lambda m: m["change_pct"], reverse=True)
    top_gainers = movers[:5]
    top_losers = list(reversed(movers[-5:])) if len(movers) >= 5 else list(reversed(movers))

    return {
        "direction": direction,
        "confidence": avg_confidence,
        "stocks_up": stocks_up,
        "stocks_down": stocks_down,
        "stocks_flat": stocks_flat,
        "breadth_pct": breadth_pct,
        "volume_vs_avg": volume_vs_avg,
        "top_gainers": top_gainers,
        "top_losers": top_losers
    }


def generate_sector_breakdown(consensus_map, stocks_metadata):
    """
    Group consensus signals by sector.

    Returns:
        list of dicts, one per sector, with signal distribution and avg scores.
    """
    sectors = defaultdict(lambda: {
        "sector_en": "", "sector_ar": "",
        "up": 0, "down": 0, "flat": 0,
        "confidences": [], "bull_scores": [], "bear_scores": []
    })

    for symbol, c in consensus_map.items():
        meta = stocks_metadata.get(symbol, {})
        sector_en = meta.get("sector_en", "Other")
        sector_ar = meta.get("sector_ar", "أخرى")

        entry = sectors[sector_en]
        entry["sector_en"] = sector_en
        entry["sector_ar"] = sector_ar

        signal = c.get("final_signal", {})
        prediction = signal.get("prediction", "FLAT") if isinstance(signal, dict) else signal
        confidence = signal.get("confidence", 0) if isinstance(signal, dict) else c.get("confidence", 0)

        if prediction == "UP":
            entry["up"] += 1
        elif prediction == "DOWN":
            entry["down"] += 1
        else:
            entry["flat"] += 1

        entry["confidences"].append(confidence)

        bull = c.get("bull_case", {}).get("bull_score", 0) if isinstance(c.get("bull_case"), dict) else c.get("bull_score", 0)
        bear = c.get("bear_case", {}).get("bear_score", 0) if isinstance(c.get("bear_case"), dict) else c.get("bear_score", 0)
        entry["bull_scores"].append(bull)
        entry["bear_scores"].append(bear)

    result = []
    for sector_en, s in sectors.items():
        total = s["up"] + s["down"] + s["flat"]
        avg_conf = round(sum(s["confidences"]) / len(s["confidences"]), 1) if s["confidences"] else 0
        avg_bull = round(sum(s["bull_scores"]) / len(s["bull_scores"]), 1) if s["bull_scores"] else 0
        avg_bear = round(sum(s["bear_scores"]) / len(s["bear_scores"]), 1) if s["bear_scores"] else 0

        if total > 0 and s["up"] / total >= 0.6:
            direction = "BULLISH"
        elif total > 0 and s["down"] / total >= 0.6:
            direction = "BEARISH"
        else:
            direction = "MIXED"

        result.append({
            "sector_en": sector_en,
            "sector_ar": s["sector_ar"],
            "direction": direction,
            "stock_count": total,
            "up": s["up"],
            "down": s["down"],
            "flat": s["flat"],
            "avg_confidence": avg_conf,
            "avg_bull": avg_bull,
            "avg_bear": avg_bear
        })

    result.sort(key=lambda x: x["avg_confidence"], reverse=True)
    return result


def generate_risk_alerts(consensus_map, stocks_metadata):
    """
    Extract stocks with risk flags (FLAG, DOWNGRADE, BLOCK).

    Returns:
        list of alert dicts sorted by severity.
    """
    severity_order = {"BLOCK": 0, "DOWNGRADE": 1, "FLAG": 2}
    alerts = []

    for symbol, c in consensus_map.items():
        risk = c.get("risk_assessment", {}) if isinstance(c.get("risk_assessment"), dict) else {}
        risk_action = risk.get("action") or c.get("risk_action", "PASS")

        if risk_action in ("FLAG", "DOWNGRADE", "BLOCK"):
            meta = stocks_metadata.get(symbol, {})
            alerts.append({
                "symbol": symbol,
                "name_en": meta.get("name_en", symbol),
                "name_ar": meta.get("name_ar", symbol),
                "risk_action": risk_action,
                "risk_score": c.get("risk_score", 0) or risk.get("risk_score", 0),
                "risk_flags": risk.get("risk_flags", []),
                "severity": "HIGH" if risk_action in ("DOWNGRADE", "BLOCK") else "MEDIUM"
            })

    alerts.sort(key=lambda a: severity_order.get(a["risk_action"], 99))
    return alerts


def generate_sentiment_snapshot(sentiment_data, stocks_metadata):
    """
    Aggregate sentiment scores and pick notable movers.

    Args:
        sentiment_data: {symbol: {avg_sentiment, sentiment_label, article_count, ...}}
        stocks_metadata: {symbol: {name_en, name_ar, ...}}

    Returns:
        dict with overall direction, score, counts, and notable list.
    """
    if not sentiment_data:
        return {
            "direction": "NEUTRAL", "avg_score": 0,
            "positive_count": 0, "negative_count": 0, "neutral_count": 0,
            "total_articles": 0, "notable": []
        }

    scores = []
    positive = 0
    negative = 0
    neutral = 0
    total_articles = 0

    for symbol, s in sentiment_data.items():
        label = s.get("sentiment_label", "Neutral")
        avg = s.get("avg_sentiment", 0) or 0
        articles = s.get("article_count", 0) or 0

        scores.append(avg)
        total_articles += articles

        if label and "Bullish" in label:
            positive += 1
        elif label and "Bearish" in label:
            negative += 1
        else:
            neutral += 1

    avg_score = round(sum(scores) / len(scores), 3) if scores else 0

    if avg_score >= 0.15:
        direction = "POSITIVE"
    elif avg_score <= -0.15:
        direction = "NEGATIVE"
    else:
        direction = "NEUTRAL"

    # Notable: top-3 most positive + top-3 most negative
    ranked = []
    for symbol, s in sentiment_data.items():
        meta = stocks_metadata.get(symbol, {})
        ranked.append({
            "symbol": symbol,
            "name_en": meta.get("name_en", symbol),
            "name_ar": meta.get("name_ar", symbol),
            "sentiment_label": s.get("sentiment_label", "Neutral"),
            "avg_sentiment": round(s.get("avg_sentiment", 0) or 0, 3),
            "article_count": s.get("article_count", 0) or 0
        })

    ranked.sort(key=lambda x: x["avg_sentiment"], reverse=True)
    notable = ranked[:3] + ranked[-3:] if len(ranked) > 6 else ranked
    # Deduplicate if list is small
    seen = set()
    unique_notable = []
    for n in notable:
        if n["symbol"] not in seen:
            seen.add(n["symbol"])
            unique_notable.append(n)

    return {
        "direction": direction,
        "avg_score": avg_score,
        "positive_count": positive,
        "negative_count": negative,
        "neutral_count": neutral,
        "total_articles": total_articles,
        "notable": unique_notable
    }


def get_briefing_performance_snippet() -> dict:
    """
    Fetch 30-day rolling performance metrics for inclusion in the daily briefing.
    Returns a lightweight summary suitable for the briefing card.
    
    This function accesses the database, so it CAN fail gracefully if the 
    performance engine hasn't run yet.
    """
    try:
        from engines.performance_metrics import get_performance_summary
        metrics = get_performance_summary(days=30, live_only=True)
        
        if metrics.get("total_predictions", 0) == 0:
            return {
                "available": False,
                "message_en": "Track record in progress — not enough data yet.",
                "message_ar": "السجل قيد التكوين — ليس هناك بيانات كافية بعد."
            }
        
        return {
            "available": True,
            "period": "30d",
            "total_trades": metrics.get("total_predictions", 0),
            "win_rate": metrics.get("win_rate", 0),
            "avg_alpha": metrics.get("avg_alpha_1d", 0),
            "sharpe_ratio": metrics.get("sharpe_ratio", 0),
            "max_drawdown": metrics.get("max_drawdown", 0),
            "meets_minimum": metrics.get("meets_minimum", False),
            "message_en": f"30-day record: {metrics.get('win_rate', 0)}% win rate, {'+' if metrics.get('avg_alpha_1d', 0) > 0 else ''}{metrics.get('avg_alpha_1d', 0)}% avg alpha.",
            "message_ar": f"سجل 30 يوم: نسبة فوز {metrics.get('win_rate', 0)}%، ألفا متوسط {'+' if metrics.get('avg_alpha_1d', 0) > 0 else ''}{metrics.get('avg_alpha_1d', 0)}%."
        }
    except Exception as e:
        return {
            "available": False,
            "message_en": "Track record unavailable.",
            "message_ar": "السجل غير متاح."
        }


def generate_daily_briefing(consensus_map, prices_map, prev_prices_map, stocks_metadata, sentiment_data):
    """
    Orchestrator: build the complete daily briefing from all data sources.

    Returns:
        {
            'market_pulse': {...},
            'sector_breakdown': [...],
            'risk_alerts': [...],
            'sentiment_snapshot': {...},
            'track_record': {...},
            'stocks_processed': int
        }
    """
    market_pulse = generate_market_pulse(consensus_map, prices_map, prev_prices_map, stocks_metadata)
    sector_breakdown = generate_sector_breakdown(consensus_map, stocks_metadata)
    risk_alerts = generate_risk_alerts(consensus_map, stocks_metadata)
    sentiment_snapshot = generate_sentiment_snapshot(sentiment_data, stocks_metadata)
    track_record = get_briefing_performance_snippet()

    return {
        "market_pulse": market_pulse,
        "sector_breakdown": sector_breakdown,
        "risk_alerts": risk_alerts,
        "sentiment_snapshot": sentiment_snapshot,
        "track_record": track_record,
        "stocks_processed": len(consensus_map)
    }

