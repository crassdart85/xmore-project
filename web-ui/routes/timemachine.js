const express = require('express');
const router = express.Router();
const { spawn } = require('child_process');
const path = require('path');

// Simple in-memory cache (TTL: 1 hour)
const cache = new Map();
const CACHE_TTL = 60 * 60 * 1000; // 1 hour
const MAX_CACHE_SIZE = 50;

function getCacheKey(amount, startDate) {
    return `${amount}_${startDate}`;
}

// POST /api/timemachine/simulate
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

        // Evict old cache entries (keep max 50)
        if (cache.size > MAX_CACHE_SIZE) {
            const oldestKey = cache.keys().next().value;
            cache.delete(oldestKey);
        }

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

module.exports = router;
