"""
Main Agent Execution Script — 3-Layer Consensus Pipeline.

Flow:
  1. Fetch price data + sentiment for each stock
  2. Run 4 signal agents → structured AgentSignal dicts (Layer 1)
  3. Run Consensus Engine (Bull/Bear + Risk gating) (Layers 2 & 3)
  4. Store individual predictions + consensus results to database
"""

import os
import json
import pandas as pd
from datetime import datetime, timedelta
import config
from database import get_connection
from sentiment import get_latest_sentiment
import sys
import traceback
import logging

logger = logging.getLogger(__name__)

# Import agents
try:
    from agents.agent_rsi import RSIAgent
    from agents.agent_ma import MAAgent
    from agents.agent_volume import VolumeAgent
    from agents.agent_ml import MLAgent
    from agents.consensus_engine import run_consensus
    print("✅ All agents imported successfully (including Consensus Engine)")
except Exception as e:
    print(f"❌ Failed to import agents: {e}")
    traceback.print_exc()
    sys.exit(1)


def _compute_market_data(df):
    """
    Derive market-level metrics from price DataFrame for the Risk Agent.
    Returns dict with volume_20d_avg, volatility_20d, price, drawdowns, 52w range.
    """
    if df is None or len(df) < 5:
        return None

    market = {}
    market['price'] = float(df['close'].iloc[-1])

    # 20-day average volume
    if 'volume' in df.columns and len(df) >= 20:
        market['volume_20d_avg'] = float(df['volume'].tail(20).mean())
    else:
        market['volume_20d_avg'] = float(df['volume'].mean()) if 'volume' in df.columns else None

    # 20-day daily volatility (std of log returns)
    if len(df) >= 21:
        returns = df['close'].pct_change().dropna().tail(20)
        market['volatility_20d'] = float(returns.std()) if len(returns) > 0 else None
    else:
        market['volatility_20d'] = None

    # 5-day drawdown
    if len(df) >= 6:
        price_5d_ago = float(df['close'].iloc[-6])
        market['drawdown_5d'] = (market['price'] - price_5d_ago) / price_5d_ago if price_5d_ago > 0 else 0
    else:
        market['drawdown_5d'] = 0

    # 20-day drawdown
    if len(df) >= 21:
        price_20d_ago = float(df['close'].iloc[-21])
        market['drawdown_20d'] = (market['price'] - price_20d_ago) / price_20d_ago if price_20d_ago > 0 else 0
    else:
        market['drawdown_20d'] = 0

    # 52-week range position
    if len(df) >= 252:
        low_52w = float(df['close'].tail(252).min())
        high_52w = float(df['close'].tail(252).max())
    else:
        low_52w = float(df['close'].min())
        high_52w = float(df['close'].max())

    if high_52w > low_52w:
        market['range_52w_position'] = (market['price'] - low_52w) / (high_52w - low_52w)
    else:
        market['range_52w_position'] = 0.5

    return market


def _store_consensus(conn, stock, today, consensus_result):
    """Store consensus result in consensus_results table."""
    cursor = conn.cursor()

    # Serialize JSON fields
    bull_json = json.dumps(consensus_result.get('bull_case', {}))
    bear_json = json.dumps(consensus_result.get('bear_case', {}))
    risk_json = json.dumps(consensus_result.get('risk_assessment', {}))
    signals_json = json.dumps(consensus_result.get('agent_signals', []))
    chain_json = json.dumps(consensus_result.get('reasoning_chain', []))
    display_json = json.dumps(consensus_result.get('display', {}))

    if os.getenv('DATABASE_URL'):
        cursor.execute("""
            INSERT INTO consensus_results
            (symbol, prediction_date, final_signal, conviction, confidence,
             risk_adjusted, agent_agreement, agents_agreeing, agents_total,
             majority_direction, bull_score, bear_score, risk_action, risk_score,
             bull_case_json, bear_case_json, risk_assessment_json,
             agent_signals_json, reasoning_chain_json, display_json)
            VALUES (%s, %s, %s, %s, %s,
                    %s, %s, %s, %s,
                    %s, %s, %s, %s, %s,
                    %s, %s, %s,
                    %s, %s, %s)
            ON CONFLICT (symbol, prediction_date)
            DO UPDATE SET
                final_signal = EXCLUDED.final_signal,
                conviction = EXCLUDED.conviction,
                confidence = EXCLUDED.confidence,
                risk_adjusted = EXCLUDED.risk_adjusted,
                agent_agreement = EXCLUDED.agent_agreement,
                agents_agreeing = EXCLUDED.agents_agreeing,
                agents_total = EXCLUDED.agents_total,
                majority_direction = EXCLUDED.majority_direction,
                bull_score = EXCLUDED.bull_score,
                bear_score = EXCLUDED.bear_score,
                risk_action = EXCLUDED.risk_action,
                risk_score = EXCLUDED.risk_score,
                bull_case_json = EXCLUDED.bull_case_json,
                bear_case_json = EXCLUDED.bear_case_json,
                risk_assessment_json = EXCLUDED.risk_assessment_json,
                agent_signals_json = EXCLUDED.agent_signals_json,
                reasoning_chain_json = EXCLUDED.reasoning_chain_json,
                display_json = EXCLUDED.display_json
        """, (
            stock, today,
            consensus_result.get('final_signal', 'HOLD'),
            consensus_result.get('conviction', 'LOW'),
            consensus_result.get('confidence', 0),
            consensus_result.get('risk_adjusted', False),
            consensus_result.get('agent_agreement', 0),
            consensus_result.get('agents_agreeing', 0),
            consensus_result.get('agents_total', 0),
            consensus_result.get('majority_direction', 'HOLD'),
            consensus_result.get('bull_score', 0),
            consensus_result.get('bear_score', 0),
            consensus_result.get('risk_action', 'PASS'),
            consensus_result.get('risk_score', 0),
            bull_json, bear_json, risk_json,
            signals_json, chain_json, display_json
        ))
    else:
        cursor.execute("""
            INSERT OR REPLACE INTO consensus_results
            (symbol, prediction_date, final_signal, conviction, confidence,
             risk_adjusted, agent_agreement, agents_agreeing, agents_total,
             majority_direction, bull_score, bear_score, risk_action, risk_score,
             bull_case_json, bear_case_json, risk_assessment_json,
             agent_signals_json, reasoning_chain_json, display_json)
            VALUES (?, ?, ?, ?, ?,
                    ?, ?, ?, ?,
                    ?, ?, ?, ?, ?,
                    ?, ?, ?,
                    ?, ?, ?)
        """, (
            stock, today,
            consensus_result.get('final_signal', 'HOLD'),
            consensus_result.get('conviction', 'LOW'),
            consensus_result.get('confidence', 0),
            1 if consensus_result.get('risk_adjusted', False) else 0,
            consensus_result.get('agent_agreement', 0),
            consensus_result.get('agents_agreeing', 0),
            consensus_result.get('agents_total', 0),
            consensus_result.get('majority_direction', 'HOLD'),
            consensus_result.get('bull_score', 0),
            consensus_result.get('bear_score', 0),
            consensus_result.get('risk_action', 'PASS'),
            consensus_result.get('risk_score', 0),
            bull_json, bear_json, risk_json,
            signals_json, chain_json, display_json
        ))


def execute():
    """
    Run the full 3-layer prediction pipeline for all configured stocks.

    Workflow:
    1. Initialize signal agents (RSI, MA, Volume, ML).
    2. For each stock:
       a. Load price history + sentiment
       b. Run all 4 agents → structured AgentSignal dicts
       c. Run Consensus Engine (Bull/Bear + Risk gating)
       d. Store predictions + consensus results
    """
    try:
        print("🚀 Starting 3-Layer Prediction Pipeline...")

        # Create signal agents
        rsi_agent = RSIAgent()
        ma_agent = MAAgent(short_window=config.MA_SHORT_PERIOD, long_window=config.MA_LONG_PERIOD)
        vol_agent = VolumeAgent()
        ml_agent = MLAgent()

        agents = [rsi_agent, ma_agent, vol_agent, ml_agent]
        print(f"✅ Created {len(agents)} signal agents")

        # Define prediction windows
        today = datetime.now().strftime('%Y-%m-%d')
        target = (datetime.now() + timedelta(days=config.PREDICTION_HORIZON_DAYS)).strftime('%Y-%m-%d')
        print(f"📅 Prediction date: {today}")
        print(f"🎯 Target date: {target}")
        print(f"📊 Processing {len(config.ALL_STOCKS)} stocks...")

        # Portfolio-level tracking for risk concentration checks
        portfolio_signals = []
        risk_cfg = getattr(config, 'RISK_CONFIG', None)

        with get_connection() as conn:
            cursor = conn.cursor()

            for stock in config.ALL_STOCKS:
                print(f"\n{'='*50}")
                print(f"  📈 {stock}")
                print(f"{'='*50}")

                # ── Fetch price data ──
                if os.getenv('DATABASE_URL'):
                    cursor.execute(
                        "SELECT date, open, high, low, close, volume FROM prices WHERE symbol=%s ORDER BY date",
                        (stock,)
                    )
                else:
                    cursor.execute(
                        "SELECT date, open, high, low, close, volume FROM prices WHERE symbol=? ORDER BY date",
                        (stock,)
                    )

                rows = cursor.fetchall()
                if os.getenv('DATABASE_URL'):
                    df = pd.DataFrame(rows)
                else:
                    df = pd.DataFrame(rows, columns=['date', 'open', 'high', 'low', 'close', 'volume'])

                print(f"  📊 Loaded {len(df)} price records")

                if len(df) < 50:
                    print(f"  ⚠️  Not enough data ({len(df)} rows), skipping")
                    continue

                # Add symbol column for ML agent
                df['symbol'] = stock

                # ── Fetch sentiment ──
                sentiment = get_latest_sentiment(stock)
                if sentiment:
                    print(f"  💬 Sentiment: {sentiment.get('sentiment_label', 'N/A')} ({sentiment.get('avg_sentiment', 0):.2f})")
                else:
                    print(f"  💬 Sentiment: No data")

                # ── Layer 1: Run signal agents → structured output ──
                agent_signals = []
                cursor = conn.cursor()

                for agent in agents:
                    try:
                        # Use new predict_signal() for structured output
                        signal_dict = agent.predict_signal(df, symbol=stock, sentiment=sentiment)
                        agent_signals.append(signal_dict)

                        prediction = signal_dict.get('prediction', 'HOLD')
                        confidence = signal_dict.get('confidence', 0)
                        reasoning_json = json.dumps(signal_dict.get('reasoning', {}))

                        # Store individual prediction
                        if os.getenv('DATABASE_URL'):
                            cursor.execute("""
                                INSERT INTO predictions
                                (symbol, prediction_date, target_date, agent_name, prediction, confidence, reasoning)
                                VALUES (%s, %s, %s, %s, %s, %s, %s)
                                ON CONFLICT (symbol, prediction_date, target_date, agent_name)
                                DO UPDATE SET prediction = EXCLUDED.prediction,
                                             confidence = EXCLUDED.confidence,
                                             reasoning = EXCLUDED.reasoning
                            """, (stock, today, target, agent.name, prediction, confidence, reasoning_json))
                        else:
                            cursor.execute("""
                                INSERT OR REPLACE INTO predictions
                                (symbol, prediction_date, target_date, agent_name, prediction, confidence, reasoning)
                                VALUES (?, ?, ?, ?, ?, ?, ?)
                            """, (stock, today, target, agent.name, prediction, confidence, reasoning_json))

                        print(f"  🔮 {agent.name}: {prediction} ({confidence:.0f}%)")

                    except Exception as e:
                        print(f"  ❌ {agent.name} error: {e}")
                        traceback.print_exc()

                if not agent_signals:
                    print(f"  ⚠️  No agent signals generated, skipping consensus")
                    continue

                # ── Compute market data for Risk Agent ──
                market_data = _compute_market_data(df)

                # ── Layers 2 & 3: Consensus Engine ──
                consensus_result = run_consensus(
                    symbol=stock,
                    agent_signals=agent_signals,
                    market_data=market_data,
                    sentiment_data=sentiment,
                    portfolio_signals=portfolio_signals,
                    risk_config=risk_cfg
                )

                # Track for portfolio-level risk checks on subsequent stocks
                portfolio_signals.append({
                    "symbol": stock,
                    "signal": consensus_result.get('final_signal', 'HOLD')
                })

                # Store consensus result
                _store_consensus(conn, stock, today, consensus_result)

                # Also store consensus as a "Consensus" prediction
                consensus_signal = consensus_result.get('final_signal', 'HOLD')
                consensus_confidence = consensus_result.get('confidence', 0)

                if os.getenv('DATABASE_URL'):
                    cursor.execute("""
                        INSERT INTO predictions
                        (symbol, prediction_date, target_date, agent_name, prediction, confidence)
                        VALUES (%s, %s, %s, %s, %s, %s)
                        ON CONFLICT (symbol, prediction_date, target_date, agent_name)
                        DO UPDATE SET prediction = EXCLUDED.prediction,
                                     confidence = EXCLUDED.confidence
                    """, (stock, today, target, "Consensus", consensus_signal, consensus_confidence))
                else:
                    cursor.execute("""
                        INSERT OR REPLACE INTO predictions
                        (symbol, prediction_date, target_date, agent_name, prediction, confidence)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, (stock, today, target, "Consensus", consensus_signal, consensus_confidence))

                # Display summary
                bull_s = consensus_result.get('bull_score', 0)
                bear_s = consensus_result.get('bear_score', 0)
                risk_action = consensus_result.get('risk_action', 'PASS')
                conviction = consensus_result.get('conviction', 'LOW')
                agreement = consensus_result.get('agent_agreement', 0)

                print(f"  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
                print(f"  🤝 Consensus: {consensus_signal} ({conviction})")
                print(f"  🐂 Bull: {bull_s}/100  |  🐻 Bear: {bear_s}/100")
                print(f"  👥 Agreement: {agreement:.0%}  |  🛡️ Risk: {risk_action}")
                if consensus_result.get('risk_adjusted'):
                    print(f"  ⚠️  RISK-ADJUSTED (original signal was modified)")

        print(f"\n{'='*50}")
        print(f"✅ Pipeline complete! Processed {len(config.ALL_STOCKS)} stocks.")
        print(f"{'='*50}")

    except Exception as e:
        print(f"\n❌ Error in execute(): {e}")
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    try:
        execute()
    except Exception as e:
        print(f"❌ Fatal error: {e}")
        traceback.print_exc()
        sys.exit(1)