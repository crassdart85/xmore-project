'use strict';

/**
 * Xmore Time Machine — Backtest Simulation Engine
 *
 * Replays historical trade_recommendations day-by-day using actual prices
 * to simulate what a portfolio would have returned.
 *
 * Adapts to actual DB schema:
 *   - confidence: integer 0-100 (mapped to 0.0-1.0 internally)
 *   - close_price: entry price at recommendation time
 *   - was_correct, actual_next_day_return, actual_5day_return: outcome fields
 *   - action: BUY/SELL/HOLD/WATCH (uppercase)
 */

// ─── Constants ───────────────────────────────────────────────
const MAX_POSITIONS = 10;
const CASH_RESERVE_PCT = 0.10;        // Keep 10% cash
const MAX_SINGLE_POSITION_PCT = 0.25; // No stock > 25% of portfolio
const DEFAULT_HOLD_DAYS = 10;         // Exit after N days if no signal resolves

// ─── Main entry point ────────────────────────────────────────
async function runBacktest(db, isPostgres, amount, startDate) {
    const startStr = toDateStr(startDate);
    const endStr = toDateStr(new Date());

    // 1) Pre-fetch all needed data in bulk
    const [recommendations, pricesMap, stockNames] = await Promise.all([
        fetchRecommendations(db, isPostgres, startStr, endStr),
        fetchPricesMap(db, isPostgres, startStr, endStr),
        fetchStockNames(db, isPostgres)
    ]);

    if (!recommendations.length) {
        return { error: 'no_data', message: 'No recommendations found in this date range.' };
    }

    // Group recs by date for day-by-day replay
    const recsByDate = {};
    for (const rec of recommendations) {
        const d = toDateStr(rec.recommendation_date);
        if (!recsByDate[d]) recsByDate[d] = [];
        recsByDate[d].push(rec);
    }

    // Build sorted list of all trading days from prices
    const tradingDays = buildTradingDays(pricesMap, startStr, endStr);

    if (!tradingDays.length) {
        return { error: 'no_data', message: 'No price data available for this period.' };
    }

    // 2) Run day-by-day simulation
    let cash = amount;
    const holdings = {};   // symbol -> { shares, buyPrice, buyDate, rec }
    const closedTrades = [];
    const equityCurve = [];
    let peakValue = amount;
    let maxDrawdownPct = 0;
    let maxDrawdownDate = startStr;

    // Fetch EGX30 benchmark data
    const egx30Prices = pricesMap['EGX30'] || pricesMap['EGX30.CA'] || pricesMap['^EGX30'] || null;
    const egx30Start = egx30Prices ? getClosestPrice(egx30Prices, startStr) : null;

    for (const day of tradingDays) {
        // --- CHECK EXITS ---
        const symbolsToRemove = [];
        for (const [symbol, pos] of Object.entries(holdings)) {
            const todayPrice = getPrice(pricesMap, symbol, day);
            if (!todayPrice) continue;

            let shouldSell = false;
            let sellReason = '';

            // Check if rec outcome is known (was_correct)
            if (pos.rec.was_correct !== null && pos.rec.was_correct !== undefined) {
                shouldSell = true;
                sellReason = pos.rec.was_correct ? 'target_hit' : 'stop_loss';
            }
            // Check stop_loss hit
            else if (pos.rec.stop_loss_price && todayPrice <= pos.rec.stop_loss_price) {
                shouldSell = true;
                sellReason = 'stop_loss';
            }
            // Check target hit
            else if (pos.rec.target_price && todayPrice >= pos.rec.target_price) {
                shouldSell = true;
                sellReason = 'target_hit';
            }
            // Time-based exit: hold too long
            else if (daysBetween(pos.buyDate, day) >= DEFAULT_HOLD_DAYS) {
                shouldSell = true;
                sellReason = 'time_exit';
            }

            if (shouldSell) {
                const proceeds = pos.shares * todayPrice;
                cash += proceeds;
                const returnPct = ((todayPrice - pos.buyPrice) / pos.buyPrice) * 100;
                const profitEgp = proceeds - (pos.shares * pos.buyPrice);

                closedTrades.push({
                    stock_symbol: symbol,
                    stock_name_en: stockNames[symbol]?.name_en || symbol,
                    stock_name_ar: stockNames[symbol]?.name_ar || symbol,
                    action: pos.rec.action,
                    buy_date: pos.buyDate,
                    sell_date: day,
                    buy_price: round2(pos.buyPrice),
                    sell_price: round2(todayPrice),
                    return_pct: round2(returnPct),
                    profit_egp: round2(profitEgp),
                    consensus_score: pos.rec.confidence / 100,
                    holding_days: daysBetween(pos.buyDate, day),
                    reason: sellReason
                });

                symbolsToRemove.push(symbol);
            }
        }
        for (const s of symbolsToRemove) delete holdings[s];

        // --- CHECK NEW ENTRIES ---
        const todayRecs = recsByDate[day] || [];
        // Filter to buy/strong_buy signals, sort by confidence desc
        const buyRecs = todayRecs
            .filter(r => r.action === 'BUY' || r.action === 'STRONG_BUY')
            .sort((a, b) => (b.confidence || 0) - (a.confidence || 0));

        for (const rec of buyRecs) {
            if (Object.keys(holdings).length >= MAX_POSITIONS) break;
            if (holdings[rec.symbol]) continue; // Already holding

            const totalValue = cash + calcHoldingsValue(holdings, pricesMap, day);
            const minCash = totalValue * CASH_RESERVE_PCT;
            if (cash <= minCash) break;

            const confidenceNorm = (rec.confidence || 50) / 100;
            let allocPct;
            if (confidenceNorm >= 0.75) allocPct = 0.20;
            else if (confidenceNorm >= 0.50) allocPct = 0.15;
            else allocPct = 0.10;

            // Enforce single position cap
            allocPct = Math.min(allocPct, MAX_SINGLE_POSITION_PCT);

            let positionSize = totalValue * allocPct;
            const availableCash = cash - minCash;
            positionSize = Math.min(positionSize, availableCash);

            const entryPrice = rec.close_price || getPrice(pricesMap, rec.symbol, day);
            if (!entryPrice || entryPrice <= 0) continue;

            const shares = Math.floor(positionSize / entryPrice);
            if (shares <= 0) continue;

            const cost = shares * entryPrice;
            cash -= cost;

            holdings[rec.symbol] = {
                shares,
                buyPrice: entryPrice,
                buyDate: day,
                rec
            };
        }

        // --- DAILY SNAPSHOT ---
        const holdingsValue = calcHoldingsValue(holdings, pricesMap, day);
        const totalValue = cash + holdingsValue;

        // Track drawdown
        if (totalValue > peakValue) peakValue = totalValue;
        const dd = ((totalValue - peakValue) / peakValue) * 100;
        if (dd < maxDrawdownPct) {
            maxDrawdownPct = dd;
            maxDrawdownDate = day;
        }

        // EGX30 benchmark value
        let egx30Value = null;
        if (egx30Prices && egx30Start) {
            const egx30Today = getClosestPrice(egx30Prices, day);
            if (egx30Today && egx30Start > 0) {
                egx30Value = round2(amount * (egx30Today / egx30Start));
            }
        }

        equityCurve.push({
            date: day,
            value: round2(totalValue),
            egx30_value: egx30Value
        });
    }

    // Close remaining positions at latest prices
    for (const [symbol, pos] of Object.entries(holdings)) {
        const lastDay = tradingDays[tradingDays.length - 1];
        const lastPrice = getPrice(pricesMap, symbol, lastDay) || pos.buyPrice;
        const proceeds = pos.shares * lastPrice;
        cash += proceeds;
        const returnPct = ((lastPrice - pos.buyPrice) / pos.buyPrice) * 100;

        closedTrades.push({
            stock_symbol: symbol,
            stock_name_en: stockNames[symbol]?.name_en || symbol,
            stock_name_ar: stockNames[symbol]?.name_ar || symbol,
            action: pos.rec.action,
            buy_date: pos.buyDate,
            sell_date: endStr,
            buy_price: round2(pos.buyPrice),
            sell_price: round2(lastPrice),
            return_pct: round2(returnPct),
            profit_egp: round2(proceeds - pos.shares * pos.buyPrice),
            consensus_score: pos.rec.confidence / 100,
            holding_days: daysBetween(pos.buyDate, endStr),
            reason: 'still_open'
        });
    }

    // 3) Compute result metrics
    const finalValue = equityCurve.length > 0
        ? equityCurve[equityCurve.length - 1].value
        : amount;

    const totalReturnPct = ((finalValue - amount) / amount) * 100;
    const totalReturnEgp = finalValue - amount;
    const durationDays = tradingDays.length;

    // Annualized return
    const yearFraction = durationDays / 252; // Trading days in a year
    const annualizedReturn = yearFraction > 0
        ? (Math.pow(finalValue / amount, 1 / yearFraction) - 1) * 100
        : 0;

    // Benchmark
    const lastEqx30 = equityCurve.length > 0 ? equityCurve[equityCurve.length - 1].egx30_value : null;
    const egx30ReturnPct = lastEqx30 ? ((lastEqx30 - amount) / amount) * 100 : null;
    const alphaPct = egx30ReturnPct !== null ? totalReturnPct - egx30ReturnPct : null;
    const alphaEgp = lastEqx30 !== null ? finalValue - lastEqx30 : null;

    // Win/loss stats
    const winningTrades = closedTrades.filter(t => t.return_pct > 0);
    const losingTrades = closedTrades.filter(t => t.return_pct <= 0);
    const winRate = closedTrades.length > 0
        ? (winningTrades.length / closedTrades.length) * 100
        : 0;
    const avgHoldingDays = closedTrades.length > 0
        ? closedTrades.reduce((s, t) => s + t.holding_days, 0) / closedTrades.length
        : 0;

    // Sharpe ratio (daily returns, annualized)
    const dailyReturns = [];
    for (let i = 1; i < equityCurve.length; i++) {
        const prev = equityCurve[i - 1].value;
        if (prev > 0) {
            dailyReturns.push((equityCurve[i].value - prev) / prev);
        }
    }
    const avgDailyReturn = dailyReturns.length > 0
        ? dailyReturns.reduce((s, r) => s + r, 0) / dailyReturns.length
        : 0;
    const stdDailyReturn = dailyReturns.length > 1
        ? Math.sqrt(dailyReturns.reduce((s, r) => s + (r - avgDailyReturn) ** 2, 0) / (dailyReturns.length - 1))
        : 0;
    const sharpeRatio = stdDailyReturn > 0
        ? round2((avgDailyReturn / stdDailyReturn) * Math.sqrt(252))
        : 0;

    // Top/worst trades
    const sortedByReturn = [...closedTrades].sort((a, b) => b.return_pct - a.return_pct);
    const topTrades = sortedByReturn.slice(0, 5);
    const worstTrades = sortedByReturn.slice(-5).reverse();

    // Monthly breakdown
    const monthlyBreakdown = buildMonthlyBreakdown(equityCurve);

    // Allocation timeline
    const allocationTimeline = buildAllocationTimeline(closedTrades, stockNames);

    // Duration display
    const durationDisplay = formatDuration(startDate, new Date());

    return {
        simulation: {
            input_amount: amount,
            start_date: startStr,
            end_date: endStr,
            duration_days: durationDays,
            duration_display: durationDisplay,

            final_value: round2(finalValue),
            total_return_pct: round2(totalReturnPct),
            total_return_egp: round2(totalReturnEgp),

            annualized_return_pct: round2(annualizedReturn),

            benchmark: {
                egx30_return_pct: egx30ReturnPct !== null ? round2(egx30ReturnPct) : null,
                egx30_final_value: lastEqx30 !== null ? round2(lastEqx30) : null,
                alpha_pct: alphaPct !== null ? round2(alphaPct) : null,
                alpha_egp: alphaEgp !== null ? round2(alphaEgp) : null
            },

            risk_metrics: {
                max_drawdown_pct: round2(maxDrawdownPct),
                max_drawdown_date: maxDrawdownDate,
                sharpe_ratio: sharpeRatio,
                win_rate_pct: round2(winRate),
                avg_holding_days: round2(avgHoldingDays),
                total_trades: closedTrades.length,
                winning_trades: winningTrades.length,
                losing_trades: losingTrades.length
            },

            equity_curve: equityCurve,
            top_trades: topTrades,
            worst_trades: worstTrades,
            monthly_breakdown: monthlyBreakdown,
            allocation_timeline: allocationTimeline
        }
    };
}

// ─── Data Fetching ───────────────────────────────────────────

function queryAll(db, isPostgres, sql, params) {
    return new Promise((resolve, reject) => {
        if (!isPostgres) {
            sql = sql.replace(/\$\d+\b/g, '?');
        }
        db.all(sql, params, (err, rows) => {
            if (err) reject(err);
            else resolve(rows || []);
        });
    });
}

async function fetchRecommendations(db, isPostgres, startStr, endStr) {
    // Fetch all buy/strong_buy recs in the date range (any user — public feature)
    // De-duplicate by symbol+date, keeping highest confidence
    const sql = isPostgres
        ? `SELECT DISTINCT ON (symbol, recommendation_date)
             symbol, recommendation_date, action, confidence, conviction,
             close_price, stop_loss_price, target_price,
             was_correct, actual_next_day_return, actual_5day_return,
             agents_agreeing, agents_total, reasons, reasons_ar
           FROM trade_recommendations
           WHERE recommendation_date >= $1 AND recommendation_date <= $2
             AND action IN ('BUY', 'STRONG_BUY')
           ORDER BY symbol, recommendation_date, confidence DESC`
        : `SELECT t1.*
           FROM trade_recommendations t1
           INNER JOIN (
             SELECT symbol, recommendation_date, MAX(confidence) AS max_conf
             FROM trade_recommendations
             WHERE recommendation_date >= $1 AND recommendation_date <= $2
               AND action IN ('BUY', 'STRONG_BUY')
             GROUP BY symbol, recommendation_date
           ) t2 ON t1.symbol = t2.symbol
                AND t1.recommendation_date = t2.recommendation_date
                AND t1.confidence = t2.max_conf`;

    try {
        return await queryAll(db, isPostgres, sql, [startStr, endStr]);
    } catch (err) {
        console.error('fetchRecommendations error:', err);
        return [];
    }
}

async function fetchPricesMap(db, isPostgres, startStr, endStr) {
    const sql = `SELECT symbol, date, close FROM prices
                 WHERE date >= $1 AND date <= $2
                 ORDER BY symbol, date`;
    try {
        const rows = await queryAll(db, isPostgres, sql, [startStr, endStr]);
        const map = {};
        for (const row of rows) {
            const sym = row.symbol;
            if (!map[sym]) map[sym] = {};
            map[sym][toDateStr(row.date)] = row.close;
        }
        return map;
    } catch (err) {
        console.error('fetchPricesMap error:', err);
        return {};
    }
}

async function fetchStockNames(db, isPostgres) {
    try {
        const rows = await queryAll(db, isPostgres,
            'SELECT symbol, name_en, name_ar FROM egx30_stocks', []);
        const map = {};
        for (const r of rows) {
            map[r.symbol] = { name_en: r.name_en, name_ar: r.name_ar };
        }
        return map;
    } catch (err) {
        console.error('fetchStockNames error:', err);
        return {};
    }
}

// ─── Helpers ─────────────────────────────────────────────────

function toDateStr(d) {
    if (!d) return '';
    if (typeof d === 'string') {
        // Handle ISO strings and plain date strings
        return d.substring(0, 10);
    }
    const y = d.getFullYear();
    const m = String(d.getMonth() + 1).padStart(2, '0');
    const day = String(d.getDate()).padStart(2, '0');
    return `${y}-${m}-${day}`;
}

function round2(n) {
    return Math.round(n * 100) / 100;
}

function daysBetween(dateStrA, dateStrB) {
    const a = new Date(dateStrA);
    const b = new Date(dateStrB);
    return Math.round((b - a) / (1000 * 60 * 60 * 24));
}

function buildTradingDays(pricesMap, startStr, endStr) {
    const daySet = new Set();
    for (const symbol of Object.keys(pricesMap)) {
        for (const d of Object.keys(pricesMap[symbol])) {
            if (d >= startStr && d <= endStr) daySet.add(d);
        }
    }
    return [...daySet].sort();
}

function getPrice(pricesMap, symbol, day) {
    return pricesMap[symbol]?.[day] || null;
}

function getClosestPrice(symbolPrices, day) {
    if (symbolPrices[day]) return symbolPrices[day];
    // Find nearest prior day
    const days = Object.keys(symbolPrices).sort();
    let closest = null;
    for (const d of days) {
        if (d <= day) closest = symbolPrices[d];
        else break;
    }
    return closest;
}

function calcHoldingsValue(holdings, pricesMap, day) {
    let val = 0;
    for (const [symbol, pos] of Object.entries(holdings)) {
        const price = getPrice(pricesMap, symbol, day) || pos.buyPrice;
        val += pos.shares * price;
    }
    return val;
}

function buildMonthlyBreakdown(equityCurve) {
    if (equityCurve.length < 2) return [];
    const months = {};
    let prevValue = equityCurve[0].value;
    let prevEgx = equityCurve[0].egx30_value;

    for (const point of equityCurve) {
        const monthKey = point.date.substring(0, 7); // YYYY-MM
        months[monthKey] = { xmore: point.value, egx30: point.egx30_value };
    }

    const result = [];
    const monthKeys = Object.keys(months).sort();
    let lastXmore = equityCurve[0].value;
    let lastEgx = equityCurve[0].egx30_value;

    for (const mk of monthKeys) {
        const m = months[mk];
        const returnPct = lastXmore > 0 ? ((m.xmore - lastXmore) / lastXmore) * 100 : 0;
        const egxReturnPct = (m.egx30 && lastEgx && lastEgx > 0)
            ? ((m.egx30 - lastEgx) / lastEgx) * 100
            : null;

        result.push({
            month: mk,
            return_pct: round2(returnPct),
            egx30_return_pct: egxReturnPct !== null ? round2(egxReturnPct) : null
        });

        lastXmore = m.xmore;
        lastEgx = m.egx30;
    }

    return result;
}

function buildAllocationTimeline(closedTrades, stockNames) {
    const events = [];
    for (const trade of closedTrades) {
        const agreeing = trade.consensus_score ? Math.round(trade.consensus_score * 4) : '?';
        events.push({
            date: trade.buy_date,
            event: 'BUY',
            stock: trade.stock_symbol,
            amount_egp: round2(trade.buy_price * (trade.profit_egp / (trade.sell_price - trade.buy_price || 1))),
            reason_en: `${trade.action} signal \u2014 confidence ${Math.round(trade.consensus_score * 100)}%`,
            reason_ar: `\u0625\u0634\u0627\u0631\u0629 ${trade.action === 'BUY' ? '\u0634\u0631\u0627\u0621' : '\u0634\u0631\u0627\u0621 \u0642\u0648\u064A'} \u2014 \u062B\u0642\u0629 ${Math.round(trade.consensus_score * 100)}%`
        });
        events.push({
            date: trade.sell_date,
            event: 'SELL',
            stock: trade.stock_symbol,
            return_pct: trade.return_pct,
            reason_en: `Sold \u2014 ${trade.return_pct >= 0 ? 'profit' : 'loss'} ${trade.return_pct >= 0 ? '+' : ''}${trade.return_pct}%`,
            reason_ar: `\u0628\u064A\u0639 \u2014 ${trade.return_pct >= 0 ? '\u0631\u0628\u062D' : '\u062E\u0633\u0627\u0631\u0629'} ${trade.return_pct >= 0 ? '+' : ''}${trade.return_pct}%`
        });
    }
    return events.sort((a, b) => a.date.localeCompare(b.date));
}

function formatDuration(start, end) {
    const diffMs = end - start;
    const totalDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));
    const months = Math.floor(totalDays / 30);
    const days = totalDays % 30;
    const parts = [];
    if (months > 0) parts.push(`${months} month${months !== 1 ? 's' : ''}`);
    if (days > 0 || parts.length === 0) parts.push(`${days} day${days !== 1 ? 's' : ''}`);
    return parts.join(', ');
}

module.exports = { runBacktest };
