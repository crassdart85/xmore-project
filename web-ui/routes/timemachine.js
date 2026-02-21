'use strict';
const express = require('express');
const router = express.Router();
const { spawn } = require('child_process');
const path = require('path');
const { simulateStock, autoSelectBest } = require('../services/forecastEngine');

// Simple in-memory cache (TTL: 1 hour)
const cache = new Map();
const CACHE_TTL = 60 * 60 * 1000; // 1 hour
const MAX_CACHE_SIZE = 50;

// DB reference set via attachDb() called from server.js
let _db = null;
let _isPostgres = false;

function attachDb(db, isPostgres) {
    _db = db;
    _isPostgres = !!isPostgres;
}

function getCacheKey(amount, startDate) {
    return `past_${amount}_${startDate}`;
}

function getForecastCacheKey(symbol, amount, horizon, scenario) {
    return `forecast_${symbol}_${amount}_${horizon}_${scenario}`;
}

function evictCache() {
    if (cache.size > MAX_CACHE_SIZE) {
        cache.delete(cache.keys().next().value);
    }
}

// POST /api/timemachine/simulate  (past simulation — Python engine)
router.post('/simulate', async (req, res) => {
    try {
        const { amount, start_date } = req.body;

        // Validation
        if (!amount || !start_date) {
            return res.status(400).json({
                error: true,
                message_en: 'Amount and start date are required.',
                message_ar: 'المبلغ وتاريخ البداية مطلوبان.'
            });
        }
        const numAmount = parseFloat(amount);
        if (isNaN(numAmount) || numAmount < 5000 || numAmount > 10000000) {
            return res.status(400).json({
                error: true,
                message_en: 'Amount must be between 5,000 and 10,000,000 EGP.',
                message_ar: 'المبلغ يجب أن يكون بين ٥٬٠٠٠ و ١٠٬٠٠٠٬٠٠٠ جنيه.'
            });
        }
        const startDate = new Date(start_date);
        const now = new Date();
        if (isNaN(startDate.getTime()) || startDate >= now) {
            return res.status(400).json({
                error: true,
                message_en: 'Start date must be a valid past date.',
                message_ar: 'تاريخ البداية يجب أن يكون في الماضي.'
            });
        }
        // Reject dates more than 2 years ago
        const twoYearsAgo = new Date();
        twoYearsAgo.setFullYear(twoYearsAgo.getFullYear() - 2);
        if (startDate < twoYearsAgo) {
            return res.status(400).json({
                error: true,
                message_en: 'Start date cannot be more than 2 years ago.',
                message_ar: 'تاريخ البداية لا يمكن أن يكون أكثر من سنتين في الماضي.'
            });
        }

        // Check in-memory cache
        const cacheKey = getCacheKey(numAmount, start_date);
        const cached = cache.get(cacheKey);
        if (cached && (Date.now() - cached.timestamp < CACHE_TTL)) {
            return res.json(cached.data);
        }

        // Run Python simulation via child_process
        const inputJson = JSON.stringify({ amount: numAmount, start_date });
        const pythonScript = path.resolve(__dirname, '../../engines/timemachine.py');
        const projectRoot = path.resolve(__dirname, '../../');

        // Use python on Windows, python3 on Unix
        const pythonCmd = process.platform === 'win32' ? 'python' : 'python3';

        const result = await new Promise((resolve, reject) => {
            const proc = spawn(pythonCmd, [pythonScript, inputJson], {
                cwd: projectRoot,
                timeout: 120000, // 2 minute timeout
                env: { ...process.env, PYTHONIOENCODING: 'utf-8' }
            });

            let stdout = '';
            let stderr = '';

            proc.stdout.on('data', (data) => { stdout += data.toString(); });
            proc.stderr.on('data', (data) => { stderr += data.toString(); });

            proc.on('close', (code) => {
                if (stderr) {
                    console.log('Time Machine Python log:', stderr.substring(0, 1000));
                }
                if (code !== 0 && !stdout) {
                    reject(new Error(stderr || 'Python process failed'));
                    return;
                }
                try {
                    const parsed = JSON.parse(stdout);
                    resolve(parsed);
                } catch (e) {
                    reject(new Error('Invalid JSON from Python: ' + stdout.substring(0, 200)));
                }
            });

            proc.on('error', (err) => {
                reject(new Error('Failed to spawn Python: ' + err.message));
            });
        });

        // Check if Python returned an error
        if (result.error) {
            return res.status(422).json(result);
        }

        // Cache the successful result (in-memory only — no DB)
        cache.set(cacheKey, { data: result, timestamp: Date.now() });
        evictCache();

        return res.json(result);

    } catch (err) {
        console.error('Time Machine error:', err.message);
        return res.status(500).json({
            error: true,
            message_en: 'Simulation failed. The market data might be temporarily unavailable. Please try again.',
            message_ar: 'فشلت المحاكاة. بيانات السوق قد تكون غير متاحة مؤقتاً. يرجى المحاولة مرة أخرى.'
        });
    }
});

// POST /api/timemachine/forecast
// Monte Carlo / GBM probabilistic forecast — pure JavaScript engine (no Python dependency).
router.post('/forecast', async (req, res) => {
    try {
        const { symbol, investment_amount, horizon, scenario } = req.body;

        // symbol is optional — omitting triggers auto-select across all EGX30 stocks
        const isAuto = !symbol || symbol === 'auto';
        const sym = isAuto ? 'auto' : String(symbol).trim().toUpperCase();

        const amount = parseFloat(investment_amount);
        if (isNaN(amount) || amount < 1000 || amount > 100_000_000) {
            return res.status(400).json({ ok: false, error: 'investment_amount must be between 1,000 and 100,000,000' });
        }

        const horizonDays = parseInt(horizon, 10);
        if (isNaN(horizonDays) || horizonDays < 5 || horizonDays > 1825) {
            return res.status(400).json({ ok: false, error: 'horizon must be between 5 and 1825 days' });
        }

        const sc = (scenario || 'base').toLowerCase();
        if (!['base', 'bull', 'bear'].includes(sc)) {
            return res.status(400).json({ ok: false, error: 'scenario must be base, bull, or bear' });
        }

        // Cache check
        const cacheKey = getForecastCacheKey(sym, amount, horizonDays, sc);
        const cached = cache.get(cacheKey);
        if (cached && (Date.now() - cached.timestamp < CACHE_TTL)) {
            return res.json(cached.data);
        }

        // Run pure-JS forecast engine (no Python spawn required)
        const result = isAuto
            ? await autoSelectBest(amount, horizonDays, sc, _db)
            : await simulateStock(sym.endsWith('.CA') ? sym : `${sym}.CA`, amount, horizonDays, sc, _db);

        if (!result.ok) {
            return res.status(422).json(result);
        }

        // Cache successful result
        cache.set(cacheKey, { data: result, timestamp: Date.now() });
        evictCache();

        return res.json(result);

    } catch (err) {
        console.error('Forecast error:', err.stack || err.message);
        return res.status(500).json({
            ok: false,
            error: 'Forecast simulation failed. Please try again.',
        });
    }
});

module.exports = { router, attachDb };
