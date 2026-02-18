const express = require('express');
const router = express.Router();
const { runBacktest } = require('../services/backtestEngine');

let db;
let isPostgres = false;

function attachDb(database, pg) {
    db = database;
    isPostgres = !!pg;
}

// Helper to promisify db calls
function dbGet(sql, params = []) {
    return new Promise((resolve, reject) => {
        if (!isPostgres) sql = sql.replace(/\$\d+\b/g, '?');
        db.get(sql, params, (err, row) => {
            if (err) reject(err);
            else resolve(row || null);
        });
    });
}

function dbRun(sql, params = []) {
    return new Promise((resolve, reject) => {
        if (!isPostgres) sql = sql.replace(/\$\d+\b/g, '?');
        db.run(sql, params, (err, result) => {
            if (err) reject(err);
            else resolve(result);
        });
    });
}

// ─── POST /api/timemachine/simulate ──────────────────────────
router.post('/simulate', async (req, res) => {
    try {
        const { amount, start_date } = req.body;

        // Validation
        if (!amount || !start_date) {
            return res.status(400).json({ error: 'amount and start_date are required' });
        }
        const numAmount = parseFloat(amount);
        if (isNaN(numAmount) || numAmount < 5000 || numAmount > 10000000) {
            return res.status(400).json({ error: 'Amount must be between 5,000 and 10,000,000 EGP' });
        }
        const startDate = new Date(start_date);
        if (isNaN(startDate.getTime()) || startDate >= new Date()) {
            return res.status(400).json({ error: 'Start date must be a valid past date' });
        }

        // Check cache — reuse if computed today
        const today = new Date().toISOString().split('T')[0];
        try {
            const cached = await dbGet(
                `SELECT simulation_data, created_at FROM backtest_simulations
                 WHERE input_amount = $1 AND start_date = $2`,
                [numAmount, start_date]
            );
            if (cached) {
                const cachedDate = cached.created_at
                    ? new Date(cached.created_at).toISOString().split('T')[0]
                    : null;
                if (cachedDate === today) {
                    const data = typeof cached.simulation_data === 'string'
                        ? JSON.parse(cached.simulation_data)
                        : cached.simulation_data;
                    return res.json(data);
                }
            }
        } catch (cacheErr) {
            // Cache table may not exist yet; ignore
            console.warn('Cache check failed (table may not exist):', cacheErr.message);
        }

        // Run simulation
        const result = await runBacktest(db, isPostgres, numAmount, startDate);

        if (result.error) {
            return res.status(400).json(result);
        }

        // Save to cache (upsert)
        try {
            const sim = result.simulation;
            const upsertSql = isPostgres
                ? `INSERT INTO backtest_simulations
                     (input_amount, start_date, end_date, duration_days, final_value,
                      total_return_pct, annualized_return_pct, egx30_return_pct, alpha_pct,
                      max_drawdown_pct, sharpe_ratio, win_rate_pct, total_trades, simulation_data, created_at)
                   VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14,NOW())
                   ON CONFLICT (input_amount, start_date) DO UPDATE SET
                     end_date = EXCLUDED.end_date,
                     duration_days = EXCLUDED.duration_days,
                     final_value = EXCLUDED.final_value,
                     total_return_pct = EXCLUDED.total_return_pct,
                     annualized_return_pct = EXCLUDED.annualized_return_pct,
                     egx30_return_pct = EXCLUDED.egx30_return_pct,
                     alpha_pct = EXCLUDED.alpha_pct,
                     max_drawdown_pct = EXCLUDED.max_drawdown_pct,
                     sharpe_ratio = EXCLUDED.sharpe_ratio,
                     win_rate_pct = EXCLUDED.win_rate_pct,
                     total_trades = EXCLUDED.total_trades,
                     simulation_data = EXCLUDED.simulation_data,
                     created_at = NOW()`
                : `INSERT OR REPLACE INTO backtest_simulations
                     (input_amount, start_date, end_date, duration_days, final_value,
                      total_return_pct, annualized_return_pct, egx30_return_pct, alpha_pct,
                      max_drawdown_pct, sharpe_ratio, win_rate_pct, total_trades, simulation_data, created_at)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,datetime('now'))`;

            await dbRun(upsertSql, [
                numAmount, start_date, sim.end_date, sim.duration_days, sim.final_value,
                sim.total_return_pct, sim.annualized_return_pct,
                sim.benchmark.egx30_return_pct, sim.benchmark.alpha_pct,
                sim.risk_metrics.max_drawdown_pct, sim.risk_metrics.sharpe_ratio,
                sim.risk_metrics.win_rate_pct, sim.risk_metrics.total_trades,
                JSON.stringify(result)
            ]);
        } catch (saveErr) {
            console.warn('Failed to cache simulation:', saveErr.message);
        }

        return res.json(result);
    } catch (err) {
        console.error('Time Machine error:', err);
        return res.status(500).json({ error: 'Simulation failed. Please try again.' });
    }
});

// ─── GET /api/timemachine/date-range ─────────────────────────
router.get('/date-range', async (req, res) => {
    try {
        const row = await dbGet(
            `SELECT MIN(recommendation_date) AS min_date,
                    MAX(recommendation_date) AS max_date,
                    COUNT(*) AS total_recs
             FROM trade_recommendations`
        );

        if (!row || !row.min_date) {
            return res.json({ min_date: null, max_date: null, total_recs: 0 });
        }

        const minDate = new Date(row.min_date).toISOString().split('T')[0];
        const maxDate = new Date(row.max_date).toISOString().split('T')[0];

        return res.json({
            min_date: minDate,
            max_date: maxDate,
            total_recs: parseInt(row.total_recs) || 0
        });
    } catch (err) {
        // Table may not exist in local SQLite
        if (err.message && (err.message.includes('no such table') || err.message.includes('does not exist'))) {
            return res.json({ min_date: null, max_date: null, total_recs: 0 });
        }
        console.error('Date range error:', err);
        return res.status(500).json({ error: 'Failed to fetch date range' });
    }
});

module.exports = { router, attachDb };
