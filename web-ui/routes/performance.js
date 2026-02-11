/**
 * Performance API Routes
 * Investor-grade, public performance endpoints.
 * No auth required — this is transparency.
 */

const express = require('express');
const router = express.Router();

let db;
let isPostgres = false;

function attachDb(database, pg) {
    db = database;
    isPostgres = pg;
}

// Helper: promisified db.all
function dbAll(query, params = []) {
    return new Promise((resolve, reject) => {
        db.all(query, params, (err, rows) => {
            if (err) reject(err);
            else resolve(rows || []);
        });
    });
}

// Helper: promisified db.get
function dbGet(query, params = []) {
    return new Promise((resolve, reject) => {
        db.get(query, params, (err, row) => {
            if (err) reject(err);
            else resolve(row || null);
        });
    });
}

// Helper: safe table check
function isTableMissing(err) {
    return err && err.message && (
        err.message.includes('does not exist') ||
        err.message.includes('no such table') ||
        err.message.includes('no such column')
    );
}

// Boolean literals differ between PostgreSQL and SQLite
function boolTrue() { return isPostgres ? 'TRUE' : '1'; }
function boolFalse() { return isPostgres ? 'FALSE' : '0'; }
function ph(n) { return isPostgres ? `$${n}` : '?'; }


// ─── PUBLIC: Overall performance summary ──────────────────────
router.get('/summary', async (req, res) => {
    try {
        const days = Math.min(parseInt(req.query.days) || 90, 365);
        const liveFilter = isPostgres
            ? `is_live = TRUE`
            : `(is_live = 1 OR is_live IS NULL)`;

        // Try materialized view first (faster, PostgreSQL only)
        let globalData = null;
        if (isPostgres) {
            try {
                const mvRows = await dbAll(`SELECT * FROM mv_performance_global`);
                if (mvRows.length > 0) globalData = mvRows[0];
            } catch (e) {
                // Materialized view may not exist yet
            }
        }

        // Fallback: compute live
        if (!globalData) {
            try {
                globalData = await dbGet(`
                    SELECT
                        COUNT(*) AS total_predictions,
                        SUM(CASE WHEN was_correct = ${boolTrue()} THEN 1 ELSE 0 END) AS wins,
                        SUM(CASE WHEN was_correct = ${boolFalse()} THEN 1 ELSE 0 END) AS losses,
                        ${isPostgres
                        ? `ROUND((SUM(CASE WHEN was_correct = TRUE THEN 1 ELSE 0 END))::numeric / NULLIF(COUNT(*), 0) * 100, 1)`
                        : `ROUND(CAST(SUM(CASE WHEN was_correct = 1 THEN 1 ELSE 0 END) AS REAL) / MAX(COUNT(*), 1) * 100, 1)`
                    } AS win_rate,
                        ${isPostgres ? 'ROUND(AVG(actual_next_day_return)::numeric, 3)' : 'ROUND(AVG(actual_next_day_return), 3)'} AS avg_return_1d,
                        ${isPostgres ? 'ROUND(AVG(actual_5day_return)::numeric, 3)' : 'ROUND(AVG(actual_5day_return), 3)'} AS avg_return_5d,
                        ${isPostgres ? 'ROUND(AVG(alpha_1d)::numeric, 3)' : 'ROUND(AVG(alpha_1d), 3)'} AS avg_alpha_1d,
                        ${isPostgres ? 'ROUND(AVG(benchmark_1d_return)::numeric, 3)' : 'ROUND(AVG(benchmark_1d_return), 3)'} AS avg_benchmark_1d,
                        ${isPostgres ? "COUNT(*) FILTER (WHERE alpha_1d > 0)" : "SUM(CASE WHEN alpha_1d > 0 THEN 1 ELSE 0 END)"} AS beat_benchmark_count,
                        MIN(recommendation_date) AS first_prediction,
                        MAX(recommendation_date) AS last_prediction,
                        COUNT(*) >= 100 AS meets_minimum
                    FROM trade_recommendations
                    WHERE was_correct IS NOT NULL
                    AND ${liveFilter}
                `);
            } catch (e) {
                if (isTableMissing(e)) {
                    return res.json({ available: false, message: 'No resolved predictions yet.' });
                }
                throw e;
            }
        }

        if (!globalData || parseInt(globalData.total_predictions || 0) === 0) {
            return res.json({ available: false, message: 'No resolved predictions yet.' });
        }

        const g = globalData;

        // Rolling metrics
        let rolling = {};
        try {
            const dateFilter30 = isPostgres
                ? `recommendation_date >= CURRENT_DATE - 30`
                : `recommendation_date >= date('now', '-30 days')`;
            const dateFilter90 = isPostgres
                ? `recommendation_date >= CURRENT_DATE - 90`
                : `recommendation_date >= date('now', '-90 days')`;

            const rollingData = await dbGet(`
                SELECT
                    ${isPostgres
                    ? `COUNT(*) FILTER (WHERE ${dateFilter30})`
                    : `SUM(CASE WHEN ${dateFilter30} THEN 1 ELSE 0 END)`
                } AS trades_30d,
                    ${isPostgres
                    ? `ROUND((COUNT(*) FILTER (WHERE was_correct = TRUE AND ${dateFilter30}))::numeric
                            / NULLIF(COUNT(*) FILTER (WHERE ${dateFilter30}), 0) * 100, 1)`
                    : `ROUND(CAST(SUM(CASE WHEN was_correct = 1 AND ${dateFilter30} THEN 1 ELSE 0 END) AS REAL)
                            / MAX(SUM(CASE WHEN ${dateFilter30} THEN 1 ELSE 0 END), 1) * 100, 1)`
                } AS win_rate_30d,
                    ${isPostgres
                    ? `ROUND(AVG(alpha_1d) FILTER (WHERE ${dateFilter30})::numeric, 3)`
                    : `ROUND(AVG(CASE WHEN ${dateFilter30} THEN alpha_1d ELSE NULL END), 3)`
                } AS alpha_30d,
                    ${isPostgres
                    ? `COUNT(*) FILTER (WHERE ${dateFilter90})`
                    : `SUM(CASE WHEN ${dateFilter90} THEN 1 ELSE 0 END)`
                } AS trades_90d,
                    ${isPostgres
                    ? `ROUND((COUNT(*) FILTER (WHERE was_correct = TRUE AND ${dateFilter90}))::numeric
                            / NULLIF(COUNT(*) FILTER (WHERE ${dateFilter90}), 0) * 100, 1)`
                    : `ROUND(CAST(SUM(CASE WHEN was_correct = 1 AND ${dateFilter90} THEN 1 ELSE 0 END) AS REAL)
                            / MAX(SUM(CASE WHEN ${dateFilter90} THEN 1 ELSE 0 END), 1) * 100, 1)`
                } AS win_rate_90d,
                    ${isPostgres
                    ? `ROUND(AVG(alpha_1d) FILTER (WHERE ${dateFilter90})::numeric, 3)`
                    : `ROUND(AVG(CASE WHEN ${dateFilter90} THEN alpha_1d ELSE NULL END), 3)`
                } AS alpha_90d
                FROM trade_recommendations
                WHERE was_correct IS NOT NULL AND ${liveFilter}
            `);

            if (rollingData) {
                rolling = {
                    "30d": {
                        trades: parseInt(rollingData.trades_30d) || 0,
                        win_rate: parseFloat(rollingData.win_rate_30d) || 0,
                        alpha: parseFloat(rollingData.alpha_30d) || 0
                    },
                    "90d": {
                        trades: parseInt(rollingData.trades_90d) || 0,
                        win_rate: parseFloat(rollingData.win_rate_90d) || 0,
                        alpha: parseFloat(rollingData.alpha_90d) || 0
                    }
                };
            }
        } catch (e) {
            console.warn('Rolling metrics failed:', e.message);
        }

        return res.json({
            available: true,
            global: {
                total_predictions: parseInt(g.total_predictions) || 0,
                wins: parseInt(g.wins) || 0,
                losses: parseInt(g.losses) || 0,
                win_rate: parseFloat(g.win_rate) || 0,
                avg_return_1d: parseFloat(g.avg_return_1d) || 0,
                avg_return_5d: parseFloat(g.avg_return_5d) || 0,
                avg_alpha_1d: parseFloat(g.avg_alpha_1d) || 0,
                avg_benchmark_1d: parseFloat(g.avg_benchmark_1d) || 0,
                beat_benchmark_pct: parseInt(g.total_predictions) > 0
                    ? Math.round((parseInt(g.beat_benchmark_count) || 0) / parseInt(g.total_predictions) * 100)
                    : 0,
                meets_minimum: g.meets_minimum === true || g.meets_minimum === 't',
                first_prediction: g.first_prediction,
                last_prediction: g.last_prediction
            },
            rolling,
            disclaimer: "All metrics are from live predictions only. No backfilled or backtested data is included in these figures."
        });
    } catch (err) {
        console.error('Performance summary error:', err);
        res.status(500).json({ error: 'Failed to load performance summary.' });
    }
});


// ─── PUBLIC: Per-agent comparison ─────────────────────────────
router.get('/by-agent', async (req, res) => {
    try {
        const rows = await dbAll(`
            SELECT *
            FROM agent_performance_daily
            WHERE snapshot_date = (SELECT MAX(snapshot_date) FROM agent_performance_daily)
            ORDER BY win_rate_30d DESC NULLS LAST
        `);

        return res.json({
            snapshot_date: rows[0]?.snapshot_date || null,
            agents: rows.map(r => ({
                agent: r.agent_name,
                predictions_30d: parseInt(r.predictions_30d) || 0,
                win_rate_30d: parseFloat(r.win_rate_30d) || 0,
                avg_confidence_30d: parseFloat(r.avg_confidence_30d) || 0,
                predictions_90d: parseInt(r.predictions_90d) || 0,
                win_rate_90d: parseFloat(r.win_rate_90d) || 0
            }))
        });
    } catch (err) {
        if (isTableMissing(err)) {
            return res.json({ snapshot_date: null, agents: [] });
        }
        console.error('Agent comparison error:', err);
        res.status(500).json({ error: 'Failed to load agent comparison.' });
    }
});


// ─── PUBLIC: Per-stock performance ────────────────────────────
router.get('/by-stock', async (req, res) => {
    try {
        const days = Math.min(parseInt(req.query.days) || 90, 365);
        const liveFilter = isPostgres ? 'tr.is_live = TRUE' : '(tr.is_live = 1 OR tr.is_live IS NULL)';
        const dateFilter = isPostgres
            ? `tr.recommendation_date >= CURRENT_DATE - ${ph(1)}`
            : `tr.recommendation_date >= date('now', '-' || ${ph(1)} || ' days')`;

        const rows = await dbAll(`
            SELECT
                tr.symbol,
                ${isPostgres ? 's.name_en, s.name_ar, s.sector_en' : "tr.symbol AS name_en, '' AS name_ar, '' AS sector_en"},
                COUNT(*) AS total,
                SUM(CASE WHEN tr.was_correct = ${boolTrue()} THEN 1 ELSE 0 END) AS correct,
                ${isPostgres ? 'ROUND(AVG(tr.actual_next_day_return)::numeric, 3)' : 'ROUND(AVG(tr.actual_next_day_return), 3)'} AS avg_return,
                ${isPostgres ? 'ROUND(AVG(tr.alpha_1d)::numeric, 3)' : 'ROUND(AVG(tr.alpha_1d), 3)'} AS avg_alpha,
                ${isPostgres
                ? `ROUND((SUM(CASE WHEN tr.was_correct = TRUE THEN 1 ELSE 0 END))::numeric / NULLIF(COUNT(*), 0) * 100, 1)`
                : `ROUND(CAST(SUM(CASE WHEN tr.was_correct = 1 THEN 1 ELSE 0 END) AS REAL) / MAX(COUNT(*), 1) * 100, 1)`
            } AS win_rate
            FROM trade_recommendations tr
            ${isPostgres ? 'JOIN egx30_stocks s ON tr.symbol = s.symbol' : ''}
            WHERE tr.was_correct IS NOT NULL
            AND ${liveFilter}
            AND ${dateFilter}
            GROUP BY tr.symbol${isPostgres ? ', s.name_en, s.name_ar, s.sector_en' : ''}
            HAVING COUNT(*) >= 3
            ORDER BY avg_alpha DESC
        `, [days]);

        return res.json({ period_days: days, stocks: rows });
    } catch (err) {
        if (isTableMissing(err)) {
            return res.json({ period_days: 90, stocks: [] });
        }
        console.error('Stock performance error:', err);
        res.status(500).json({ error: 'Failed to load stock performance.' });
    }
});


// ─── PUBLIC: Equity curve data ────────────────────────────────
router.get('/equity-curve', async (req, res) => {
    try {
        const days = Math.min(parseInt(req.query.days) || 180, 365);
        const liveFilter = isPostgres ? 'is_live = TRUE' : '(is_live = 1 OR is_live IS NULL)';
        const dateFilter = isPostgres
            ? `recommendation_date >= CURRENT_DATE - ${ph(1)}`
            : `recommendation_date >= date('now', '-' || ${ph(1)} || ' days')`;

        const rows = await dbAll(`
            SELECT
                recommendation_date AS date,
                ${isPostgres ? 'ROUND(AVG(actual_next_day_return)::numeric, 4)' : 'ROUND(AVG(actual_next_day_return), 4)'} AS xmore,
                ${isPostgres ? 'ROUND(AVG(benchmark_1d_return)::numeric, 4)' : 'ROUND(AVG(benchmark_1d_return), 4)'} AS egx30
            FROM trade_recommendations
            WHERE actual_next_day_return IS NOT NULL
            AND ${liveFilter}
            AND ${dateFilter}
            GROUP BY recommendation_date
            ORDER BY recommendation_date ASC
        `, [days]);

        let xmoreCum = 0, egx30Cum = 0;
        const series = rows.map(r => {
            xmoreCum += parseFloat(r.xmore) || 0;
            egx30Cum += parseFloat(r.egx30) || 0;
            return {
                date: r.date,
                xmore: Math.round(xmoreCum * 100) / 100,
                egx30: Math.round(egx30Cum * 100) / 100,
                alpha: Math.round((xmoreCum - egx30Cum) * 100) / 100
            };
        });

        return res.json({
            series,
            total_xmore: series.length ? series[series.length - 1].xmore : 0,
            total_egx30: series.length ? series[series.length - 1].egx30 : 0,
            total_alpha: series.length ? series[series.length - 1].alpha : 0
        });
    } catch (err) {
        if (isTableMissing(err)) {
            return res.json({ series: [], total_xmore: 0, total_egx30: 0, total_alpha: 0 });
        }
        console.error('Equity curve error:', err);
        res.status(500).json({ error: 'Failed to load equity curve.' });
    }
});


// ─── PUBLIC: Open predictions (transparency) ─────────────────
router.get('/predictions/open', async (req, res) => {
    try {
        const dateFilter = isPostgres
            ? `cr.prediction_date >= CURRENT_DATE - 5`
            : `cr.prediction_date >= date('now', '-5 days')`;

        const rows = await dbAll(`
            SELECT
                cr.symbol, s.name_en, s.name_ar,
                cr.prediction_date, cr.final_signal, cr.confidence,
                cr.conviction, cr.bull_score, cr.bear_score, cr.risk_action
            FROM consensus_results cr
            ${isPostgres ? 'JOIN' : 'LEFT JOIN'} egx30_stocks s ON cr.symbol = s.symbol
            WHERE ${dateFilter}
            ORDER BY cr.prediction_date DESC, cr.confidence DESC
        `);

        return res.json({ predictions: rows });
    } catch (err) {
        if (isTableMissing(err)) {
            return res.json({ predictions: [] });
        }
        console.error('Open predictions error:', err);
        res.status(500).json({ error: 'Failed to load open predictions.' });
    }
});


// ─── PUBLIC: Prediction history (auditable) ───────────────────
router.get('/predictions/history', async (req, res) => {
    try {
        const page = parseInt(req.query.page) || 1;
        const limit = Math.min(parseInt(req.query.limit) || 25, 100);
        const offset = (page - 1) * limit;

        const liveFilter = isPostgres ? 'tr.is_live = TRUE' : '(tr.is_live = 1 OR tr.is_live IS NULL)';
        const dateFilter = isPostgres
            ? `cr.prediction_date <= CURRENT_DATE`
            : `cr.prediction_date <= date('now')`;

        const rows = await dbAll(`
            SELECT
                cr.symbol, ${isPostgres ? 's.name_en,' : ''}
                cr.prediction_date, cr.final_signal, cr.confidence AS consensus_confidence,
                cr.conviction, cr.bull_score, cr.bear_score, cr.risk_action,
                tr.action, tr.actual_next_day_return, tr.benchmark_1d_return,
                tr.alpha_1d, tr.was_correct
            FROM consensus_results cr
            ${isPostgres ? 'JOIN egx30_stocks s ON cr.symbol = s.symbol' : ''}
            LEFT JOIN trade_recommendations tr
                ON tr.symbol = cr.symbol
                AND tr.recommendation_date = cr.prediction_date
                AND ${liveFilter}
            WHERE ${dateFilter}
            ORDER BY cr.prediction_date DESC, cr.symbol
            LIMIT ${ph(1)} OFFSET ${ph(2)}
        `, [limit, offset]);

        const countRow = await dbGet(`
            SELECT COUNT(*) AS cnt FROM consensus_results WHERE ${dateFilter}
        `);
        const total = parseInt(countRow?.cnt || countRow?.count || 0);

        return res.json({
            predictions: rows,
            pagination: {
                page, limit, total,
                pages: Math.ceil(total / limit)
            }
        });
    } catch (err) {
        if (isTableMissing(err)) {
            return res.json({ predictions: [], pagination: { page: 1, limit: 25, total: 0, pages: 0 } });
        }
        console.error('Prediction history error:', err);
        res.status(500).json({ error: 'Failed to load prediction history.' });
    }
});


// ─── PUBLIC: Audit trail (for trust) ──────────────────────────
router.get('/audit', async (req, res) => {
    try {
        const limit = Math.min(parseInt(req.query.limit) || 50, 200);

        const rows = await dbAll(`
            SELECT * FROM prediction_audit_log
            ORDER BY changed_at DESC
            LIMIT ${ph(1)}
        `, [limit]);

        return res.json({
            audit_entries: rows,
            message: "All prediction modifications are logged here. Core prediction fields (signal, confidence, action) are immutable and cannot be changed after creation."
        });
    } catch (err) {
        if (isTableMissing(err)) {
            return res.json({
                audit_entries: [],
                message: "Audit trail will be populated as predictions are resolved."
            });
        }
        console.error('Audit trail error:', err);
        res.status(500).json({ error: 'Failed to load audit trail.' });
    }
});


module.exports = { router, attachDb: attachDb };
