'use strict';

/**
 * Forecast Engine — Pure JavaScript Monte Carlo / GBM
 * ====================================================
 * Replaces engines/timemachine_forecast.py for production compatibility.
 * No Python dependency. Uses DB prices (PostgreSQL / SQLite) with optional
 * yahoo-finance2 npm package fallback for symbols not yet in the DB.
 */

const TRADING_DAYS_YEAR = 252;
const N_SIMULATIONS = 5000;
const MIN_PRICES = 60;
const LOOKBACK_YEARS = 5;

const SCENARIO_DRIFT_ADJ = { base: 0.0, bull: 0.02, bear: -0.02 };

// EGX30 constituents for auto-select mode (mirrors timemachine_forecast.py)
const EGX30_FORECAST_SYMBOLS = [
    'COMI.CA', 'HRHO.CA', 'SWDY.CA', 'TMGH.CA', 'EKHO.CA',
    'EFIH.CA', 'ORWE.CA', 'PHDC.CA', 'ABUK.CA', 'CLHO.CA',
    'ESRS.CA', 'ETEL.CA', 'JUFO.CA', 'ALCN.CA', 'OCDI.CA',
    'HELI.CA', 'AMOC.CA', 'EAST.CA', 'CCAP.CA', 'EGAL.CA',
    'ELEC.CA', 'FWRY.CA', 'GBCO.CA', 'ISPH.CA', 'MFPC.CA',
    'PHAR.CA', 'SKPC.CA', 'SPIN.CA', 'SUGR.CA', 'TALM.CA',
];

const STOCK_NAMES = {
    'COMI.CA': ['Commercial International Bank', 'البنك التجاري الدولي'],
    'HRHO.CA': ['Hermes Holding', 'هيرميس القابضة'],
    'SWDY.CA': ['Elsewedy Electric', 'السويدي إلكتريك'],
    'TMGH.CA': ['Talaat Moustafa Group', 'مجموعة طلعت مصطفى'],
    'EKHO.CA': ['Egyptian Kuwaiti Holding', 'المصرية الكويتية القابضة'],
    'EFIH.CA': ['EFG Hermes Holding', 'إي إف جي هيرميس'],
    'ORWE.CA': ['Oriental Weavers', 'السجاد الشرقي'],
    'PHDC.CA': ['Palm Hills Development', 'بالم هيلز للتعمير'],
    'ABUK.CA': ['Abu Qir Fertilizers', 'أبو قير للأسمدة'],
    'CLHO.CA': ['Cleopatra Hospital', 'مستشفى كليوباترا'],
    'ESRS.CA': ['Ezz Steel', 'حديد عز'],
    'ETEL.CA': ['Telecom Egypt', 'المصرية للاتصالات'],
    'JUFO.CA': ['Juhayna Food Industries', 'جهينة للصناعات الغذائية'],
    'ALCN.CA': ['Alexandria Container', 'الإسكندرية للحاويات والبضائع'],
    'OCDI.CA': ['Orascom Development', 'أوراسكوم للتنمية'],
    'HELI.CA': ['Heliopolis Housing', 'مصر الجديدة للإسكان'],
    'AMOC.CA': ['Alexandria Mineral Oils', 'الإسكندرية للزيوت المعدنية'],
    'EAST.CA': ['Eastern Company', 'الشركة الشرقية للدخان'],
    'CCAP.CA': ['Citadel Capital', 'القلعة القابضة'],
    'EGAL.CA': ['Edita Food Industries', 'إيديتا للصناعات الغذائية'],
    'ELEC.CA': ['El Sewedy Electric', 'الكابلات الكهربائية'],
    'FWRY.CA': ['Fawry for Banking', 'فوري للمدفوعات'],
    'GBCO.CA': ['SODIC', 'سوديك'],
    'ISPH.CA': ['Ibnsina Pharma', 'ابن سينا فارما'],
    'MFPC.CA': ['Misr Fertilizers', 'مصر للأسمدة'],
    'PHAR.CA': ['Pharos Holding', 'فاروس القابضة'],
    'SKPC.CA': ['Sidi Kerir Petrochemicals', 'سيدي كرير للبتروكيماويات'],
    'SPIN.CA': ['Spinneys Egypt', 'سبينيز مصر'],
    'SUGR.CA': ['Delta Sugar', 'الدلتا للسكر'],
    'TALM.CA': ['Taaleem Management', 'تعليم لإدارة المدارس'],
};

// ── Utilities ──────────────────────────────────────────────────────────────────

// Box-Muller transform for standard normal samples
function randomNormal() {
    let u;
    do { u = Math.random(); } while (u === 0);
    return Math.sqrt(-2 * Math.log(u)) * Math.cos(2 * Math.PI * Math.random());
}

// Promisify the unified db.all(query, params, cb) interface
function dbAll(db, query, params) {
    return new Promise((resolve, reject) => {
        db.all(query, params, (err, rows) => {
            if (err) reject(err);
            else resolve(rows || []);
        });
    });
}

function cutoffDateStr(years) {
    const d = new Date();
    d.setFullYear(d.getFullYear() - years);
    return d.toISOString().split('T')[0];
}

// ── Price Data ─────────────────────────────────────────────────────────────────

async function getPricesFromDb(symbol, db) {
    if (!db) return [];
    try {
        const cutoff = cutoffDateStr(LOOKBACK_YEARS);
        const isPostgres = db._isPostgres;
        const query = isPostgres
            ? 'SELECT close FROM prices WHERE symbol = $1 AND date >= $2 AND close IS NOT NULL ORDER BY date'
            : 'SELECT close FROM prices WHERE symbol = ? AND date >= ? AND close IS NOT NULL ORDER BY date';
        const rows = await dbAll(db, query, [symbol, cutoff]);
        return rows.map(r => parseFloat(r.close)).filter(v => !isNaN(v) && v > 0);
    } catch { return []; }
}

// Batch fetch for multiple symbols in a single query (auto-select optimisation)
async function batchPricesFromDb(symbols, db) {
    if (!db || symbols.length === 0) return {};
    try {
        const cutoff = cutoffDateStr(LOOKBACK_YEARS);
        const isPostgres = db._isPostgres;
        let query, params;
        if (isPostgres) {
            query = 'SELECT symbol, close FROM prices WHERE symbol = ANY($1) AND date >= $2 AND close IS NOT NULL ORDER BY symbol, date';
            params = [symbols, cutoff];
        } else {
            const ph = symbols.map(() => '?').join(',');
            query = `SELECT symbol, close FROM prices WHERE symbol IN (${ph}) AND date >= ? AND close IS NOT NULL ORDER BY symbol, date`;
            params = [...symbols, cutoff];
        }
        const rows = await dbAll(db, query, params);
        const result = {};
        for (const row of rows) {
            const v = parseFloat(row.close);
            if (!isNaN(v) && v > 0) {
                if (!result[row.symbol]) result[row.symbol] = [];
                result[row.symbol].push(v);
            }
        }
        return result;
    } catch { return {}; }
}

// Optional yahoo-finance2 fallback (gracefully skipped if package not installed)
async function getPricesFromYahoo(symbol) {
    try {
        const yf = require('yahoo-finance2').default;
        const end = new Date();
        const start = new Date();
        start.setFullYear(start.getFullYear() - 3);
        start.setDate(start.getDate() - 60);
        const rows = await yf.historical(symbol, {
            period1: start.toISOString().split('T')[0],
            period2: end.toISOString().split('T')[0],
            interval: '1d',
        });
        return rows.map(r => parseFloat(r.adjClose || r.close)).filter(v => !isNaN(v) && v > 0);
    } catch { return []; }
}

async function getPrices(symbol, db) {
    const dbPrices = await getPricesFromDb(symbol, db);
    if (dbPrices.length >= MIN_PRICES) return dbPrices;
    const yPrices = await getPricesFromYahoo(symbol);
    return yPrices.length > dbPrices.length ? yPrices : dbPrices;
}

// ── GBM Mathematics ────────────────────────────────────────────────────────────

function computeGbmParams(prices) {
    const logRet = [];
    for (let i = 1; i < prices.length; i++) {
        if (prices[i] > 0 && prices[i - 1] > 0) {
            logRet.push(Math.log(prices[i] / prices[i - 1]));
        }
    }
    if (logRet.length < 10) return null;
    const mean = logRet.reduce((a, b) => a + b, 0) / logRet.length;
    const variance = logRet.reduce((a, b) => a + (b - mean) ** 2, 0) / (logRet.length - 1);
    return {
        mu: mean * TRADING_DAYS_YEAR,
        sigma: Math.sqrt(variance * TRADING_DAYS_YEAR),
        lastPrice: prices[prices.length - 1],
    };
}

function runMonteCarlo(S0, mu, sigma, horizonDays, scenario, amount) {
    const muUsed = mu + (SCENARIO_DRIFT_ADJ[scenario] || 0);
    const dt = horizonDays / TRADING_DAYS_YEAR;
    const shares = amount / S0;
    const logDrift = (muUsed - 0.5 * sigma * sigma) * dt;
    const logDiffusion = sigma * Math.sqrt(dt);
    const tv = [];
    for (let i = 0; i < N_SIMULATIONS; i++) {
        tv.push(shares * S0 * Math.exp(logDrift + logDiffusion * randomNormal()));
    }
    return { terminalValues: tv, muUsed };
}

// ── Statistics ─────────────────────────────────────────────────────────────────

function percentile(sorted, p) {
    const idx = (p / 100) * (sorted.length - 1);
    const lo = Math.floor(idx), hi = Math.ceil(idx);
    return sorted[lo] + (sorted[hi] - sorted[lo]) * (idx - lo);
}

function buildHistogram(values, bins = 30) {
    const min = Math.min(...values), max = Math.max(...values);
    const step = (max - min) / bins || 1;
    const counts = new Array(bins).fill(0);
    const edges = Array.from({ length: bins + 1 }, (_, i) => +((min + i * step).toFixed(2)));
    for (const v of values) {
        const idx = Math.min(bins - 1, Math.floor((v - min) / step));
        if (idx >= 0) counts[idx]++;
    }
    return { counts, edges };
}

function buildBandData(amount, muUsed, sigma, horizonDays) {
    const Z_05 = -1.6449, Z_50 = 0.0, Z_95 = 1.6449;
    const step = Math.max(1, Math.floor(horizonDays / 252));
    const pt = (dt, z) => +(amount * Math.exp((muUsed - 0.5 * sigma * sigma) * dt + sigma * Math.sqrt(dt) * z)).toFixed(2);
    const band = [{ day: 0, worst: amount, median: amount, best: amount }];
    for (let t = step; t <= horizonDays; t += step) {
        const dt = t / TRADING_DAYS_YEAR;
        band.push({ day: t, worst: pt(dt, Z_05), median: pt(dt, Z_50), best: pt(dt, Z_95) });
    }
    if (band[band.length - 1].day !== horizonDays) {
        const dt = horizonDays / TRADING_DAYS_YEAR;
        band.push({ day: horizonDays, worst: pt(dt, Z_05), median: pt(dt, Z_50), best: pt(dt, Z_95) });
    }
    return band;
}

// ── Result Builder ─────────────────────────────────────────────────────────────

function buildResult(symbol, amount, horizonDays, scenario, prices, params, terminalValues, muUsed) {
    const { mu, sigma, lastPrice: S0 } = params;
    const sorted = [...terminalValues].sort((a, b) => a - b);
    const expected = terminalValues.reduce((a, b) => a + b, 0) / terminalValues.length;
    const probPositive = terminalValues.filter(v => v > amount).length / terminalValues.length * 100;
    return {
        ok: true,
        symbol,
        investment_amount: amount,
        last_price: +S0.toFixed(4),
        shares: +(amount / S0).toFixed(6),
        horizon_days: horizonDays,
        scenario,
        simulations_count: N_SIMULATIONS,
        drift_annual_pct: +(mu * 100).toFixed(2),
        drift_used_pct: +(muUsed * 100).toFixed(2),
        volatility_annual_pct: +(sigma * 100).toFixed(2),
        data_points: prices.length,
        expected_value: +expected.toFixed(2),
        expected_return_pct: +((expected / amount - 1) * 100).toFixed(2),
        median_value: +percentile(sorted, 50).toFixed(2),
        median_return_pct: +((percentile(sorted, 50) / amount - 1) * 100).toFixed(2),
        worst_case_value: +percentile(sorted, 5).toFixed(2),
        best_case_value: +percentile(sorted, 95).toFixed(2),
        quartile_25: +percentile(sorted, 25).toFixed(2),
        quartile_75: +percentile(sorted, 75).toFixed(2),
        probability_positive: +probPositive.toFixed(1),
        histogram: buildHistogram(terminalValues),
        band_data: buildBandData(amount, muUsed, sigma, horizonDays),
    };
}

// ── Public API ─────────────────────────────────────────────────────────────────

async function simulateStock(symbol, amount, horizonDays, scenario, db) {
    const prices = await getPrices(symbol, db);
    if (prices.length < MIN_PRICES) {
        return { ok: false, error: `Insufficient historical data for ${symbol} (need >= ${MIN_PRICES} days, found ${prices.length})` };
    }
    const params = computeGbmParams(prices);
    if (!params) return { ok: false, error: `Could not compute GBM parameters for ${symbol}` };
    const { terminalValues, muUsed } = runMonteCarlo(params.lastPrice, params.mu, params.sigma, horizonDays, scenario, amount);
    return buildResult(symbol, amount, horizonDays, scenario, prices, params, terminalValues, muUsed);
}

async function autoSelectBest(amount, horizonDays, scenario, db) {
    // Step 1: one batch DB query for all 30 EGX30 stocks
    const dbPrices = await batchPricesFromDb(EGX30_FORECAST_SYMBOLS, db);

    // Step 2: yahoo-finance2 fallback for any DB misses (parallel)
    const allPrices = { ...dbPrices };
    const missing = EGX30_FORECAST_SYMBOLS.filter(s => (allPrices[s] || []).length < MIN_PRICES);
    if (missing.length > 0) {
        const fetched = await Promise.allSettled(missing.map(sym =>
            getPricesFromYahoo(sym).then(prices => ({ sym, prices }))
        ));
        for (const r of fetched) {
            if (r.status === 'fulfilled' && r.value.prices.length >= MIN_PRICES) {
                allPrices[r.value.sym] = r.value.prices;
            }
        }
    }

    // Step 3: run MC for each available stock
    const ranked = [];
    for (const sym of EGX30_FORECAST_SYMBOLS) {
        const prices = allPrices[sym];
        if (!prices || prices.length < MIN_PRICES) continue;
        try {
            const params = computeGbmParams(prices);
            if (!params) continue;
            const { terminalValues, muUsed } = runMonteCarlo(params.lastPrice, params.mu, params.sigma, horizonDays, scenario, amount);
            const expected = terminalValues.reduce((a, b) => a + b, 0) / terminalValues.length;
            const probPos = terminalValues.filter(v => v > amount).length / terminalValues.length * 100;
            const expRetPct = (expected / amount - 1) * 100;
            const score = (probPos / 100) * (1 + Math.max(expRetPct, 0) / 100);
            ranked.push({ sym, prices, params, terminalValues, muUsed, probPos, expRetPct, score });
        } catch { /* skip bad symbol */ }
    }

    if (ranked.length === 0) {
        return { ok: false, error: 'Could not fetch price data for any EGX30 stock. Market data may be temporarily unavailable.' };
    }

    ranked.sort((a, b) => b.score - a.score);
    const w = ranked[0];
    const result = buildResult(w.sym, amount, horizonDays, scenario, w.prices, w.params, w.terminalValues, w.muUsed);
    const names = STOCK_NAMES[w.sym] || [w.sym.replace('.CA', ''), w.sym.replace('.CA', '')];

    const top5 = ranked.slice(0, 5).map(r => {
        const n = STOCK_NAMES[r.sym] || [r.sym.replace('.CA', ''), r.sym.replace('.CA', '')];
        return {
            symbol: r.sym.replace('.CA', ''),
            name_en: n[0], name_ar: n[1],
            score: +r.score.toFixed(4),
            probability_positive: +r.probPos.toFixed(1),
            expected_return_pct: +r.expRetPct.toFixed(2),
            volatility_annual_pct: +(r.params.sigma * 100).toFixed(2),
        };
    });

    return { ...result, auto_selected: true, auto_symbol_name_en: names[0], auto_symbol_name_ar: names[1], auto_ranking: top5 };
}

module.exports = { simulateStock, autoSelectBest };
