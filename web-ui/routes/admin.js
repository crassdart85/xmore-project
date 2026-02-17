const express = require('express');
const fs = require('fs');
const path = require('path');
const multer = require('multer');
const { PDFParse } = require('pdf-parse');
const { createWorker } = require('tesseract.js');
const { requireAdminSecret } = require('../middleware/admin');

const router = express.Router();

let db;
let isPostgres = false;

const uploadDir = path.join(__dirname, '..', 'uploads', 'market_reports');

function attachDb(database, pg) {
    db = database;
    isPostgres = pg;
}

function ph(n) {
    return isPostgres ? `$${n}` : '?';
}

function normalizeSql(query) {
    if (isPostgres) return query;
    return query.replace(/\$\d+\b/g, '?');
}

function dbAll(query, params = []) {
    return new Promise((resolve, reject) => {
        db.all(normalizeSql(query), params, (err, rows) => {
            if (err) reject(err);
            else resolve(rows || []);
        });
    });
}

function dbGet(query, params = []) {
    return new Promise((resolve, reject) => {
        db.get(normalizeSql(query), params, (err, row) => {
            if (err) reject(err);
            else resolve(row || null);
        });
    });
}

function dbRun(query, params = []) {
    return new Promise((resolve, reject) => {
        if (isPostgres) {
            db.run(normalizeSql(query), params, (err, result) => {
                if (err) reject(err);
                else resolve(result || null);
            });
            return;
        }

        db.run(normalizeSql(query), params, function onRun(err) {
            if (err) reject(err);
            else resolve({ lastID: this.lastID, changes: this.changes });
        });
    });
}

function isMissingTableError(err) {
    return !!(err && err.message && (
        err.message.includes('does not exist') ||
        err.message.includes('no such table') ||
        err.message.includes('no such column')
    ));
}

function ensureUploadDir() {
    fs.mkdirSync(uploadDir, { recursive: true });
}

const storage = multer.diskStorage({
    destination: (_req, _file, cb) => {
        try {
            ensureUploadDir();
            cb(null, uploadDir);
        } catch (err) {
            cb(err);
        }
    },
    filename: (_req, file, cb) => {
        const ext = path.extname(file.originalname || '').toLowerCase();
        const base = path
            .basename(file.originalname || 'report', ext)
            .replace(/[^a-zA-Z0-9._-]/g, '_');
        cb(null, `${Date.now()}_${base}${ext || '.pdf'}`);
    }
});

const ALLOWED_EXTENSIONS = new Set(['.pdf', '.png', '.jpg', '.jpeg', '.webp', '.bmp', '.tiff', '.tif']);
const IMAGE_EXTENSIONS = new Set(['.png', '.jpg', '.jpeg', '.webp', '.bmp', '.tiff', '.tif']);

function allowedFileFilter(_req, file, cb) {
    const ext = path.extname(file.originalname || '').toLowerCase();
    if (ALLOWED_EXTENSIONS.has(ext)) {
        cb(null, true);
        return;
    }
    cb(new Error('Only PDF and image files (PNG, JPG, WEBP, BMP, TIFF) are allowed'));
}

const upload = multer({
    storage,
    fileFilter: allowedFileFilter,
    limits: { fileSize: 25 * 1024 * 1024 }
});

router.use(requireAdminSecret);

const ARABIC_RE = /[\u0600-\u06FF]/g;
const LATIN_RE = /[A-Za-z]/g;
const SENTENCE_SPLIT_RE = /(?<=[.!?\u061f])\s+/;

function detectLanguage(text) {
    if (!text) return 'EN';
    const arCount = (text.match(ARABIC_RE) || []).length;
    const enCount = (text.match(LATIN_RE) || []).length;
    return arCount > enCount ? 'AR' : 'EN';
}

const TICKER_RE = /\b[A-Z]{2,5}(?:\.CA)?\b/g;
const BULLISH_RE = /\b(buy|long|bullish|upside|outperform|go(?:ing)?\s+up|rise|rally|upgrade|accumulate|overweight|strong|growth|positive|gain|recover)\b/gi;
const BEARISH_RE = /\b(sell|short|bearish|downside|underperform|go(?:ing)?\s+down|fall|decline|downgrade|reduce|underweight|weak|loss|drop|risk|negative|warning)\b/gi;
const TOPIC_RE = /\b(earnings|revenue|profit|dividend|merger|acquisition|IPO|interest\s+rate|inflation|GDP|oil|sector|market|index|EGX|banking|real\s+estate|pharma|tech|telecom|construction|food|chemicals|retail)\b/gi;

function buildInsight(text) {
    if (!text) return '';
    const cleaned = text.replace(/\s+/g, ' ').trim();
    if (!cleaned) return '';

    // Extract stock tickers mentioned
    const tickerMatches = [...new Set((cleaned.match(TICKER_RE) || []).filter(t => t.length >= 2 && t.length <= 7))];
    // Filter out common English words that look like tickers
    const stopWords = new Set(['THE', 'AND', 'FOR', 'ARE', 'BUT', 'NOT', 'YOU', 'ALL', 'CAN', 'HER', 'WAS', 'ONE', 'OUR', 'OUT', 'HAS', 'ITS', 'HIS', 'HOW', 'MAY', 'NEW', 'NOW', 'OLD', 'SEE', 'WAY', 'WHO', 'DID', 'GET', 'LET', 'SAY', 'SHE', 'TOO', 'USE', 'PDF', 'PNG', 'JPG', 'EGP', 'USD', 'EUR', 'GBP', 'SAR', 'AED', 'WITH', 'THIS', 'THAT', 'FROM', 'ALSO', 'BEEN', 'WILL', 'EACH', 'THAN', 'THEM', 'THEN', 'SOME', 'HAVE', 'MORE']);
    const tickers = tickerMatches.filter(t => !stopWords.has(t)).slice(0, 6);

    // Count bullish vs bearish signals
    const bullCount = (cleaned.match(BULLISH_RE) || []).length;
    const bearCount = (cleaned.match(BEARISH_RE) || []).length;

    // Extract topics
    const topicMatches = [...new Set((cleaned.match(TOPIC_RE) || []).map(t => t.toLowerCase()))].slice(0, 4);

    // Build the interpretive summary
    const parts = [];

    // What the document is about
    if (tickers.length && topicMatches.length) {
        parts.push(`Discusses ${tickers.join(', ')} in the context of ${topicMatches.join(', ')}`);
    } else if (tickers.length) {
        parts.push(`Covers stocks: ${tickers.join(', ')}`);
    } else if (topicMatches.length) {
        parts.push(`Covers topics: ${topicMatches.join(', ')}`);
    } else {
        // Fall back to first meaningful sentence
        const sentences = cleaned.split(SENTENCE_SPLIT_RE).map(s => s.trim()).filter(Boolean);
        if (sentences.length) {
            parts.push(sentences[0].slice(0, 200));
        } else {
            return cleaned.slice(0, 300);
        }
    }

    // Overall tone
    if (bullCount > 0 || bearCount > 0) {
        const total = bullCount + bearCount;
        if (bullCount > bearCount * 2) {
            parts.push(`Overall tone is bullish (${bullCount}/${total} signals positive)`);
        } else if (bearCount > bullCount * 2) {
            parts.push(`Overall tone is bearish (${bearCount}/${total} signals negative)`);
        } else {
            parts.push(`Mixed outlook (${bullCount} bullish vs ${bearCount} bearish signals)`);
        }
    }

    // Key takeaway from signal sentences
    const sentences = cleaned.split(SENTENCE_SPLIT_RE).map(s => s.trim()).filter(Boolean);
    const SIGNAL_RE = /\b(buy|sell|bullish|bearish|target|upgrade|downgrade|outperform|underperform)\b/i;
    const keySentence = sentences.find(s => SIGNAL_RE.test(s));
    if (keySentence) {
        parts.push(`Key insight: "${keySentence.slice(0, 150)}"`);
    }

    return parts.join('. ').slice(0, 600);
}

async function extractPdf(filePath) {
    const dataBuffer = fs.readFileSync(filePath);
    const pdf = new PDFParse({ data: dataBuffer });
    const result = await pdf.getText();
    const extractedText = (result.text || '').trim();
    const language = detectLanguage(extractedText);
    const summary = buildInsight(extractedText);
    pdf.destroy();
    return { extracted_text: extractedText, language, summary };
}

async function extractImage(filePath) {
    const lang = 'eng+ara';
    const worker = await createWorker(lang);
    try {
        const { data } = await worker.recognize(filePath);
        const extractedText = (data.text || '').trim();
        const language = detectLanguage(extractedText);
        const summary = buildInsight(extractedText);
        return { extracted_text: extractedText, language, summary };
    } finally {
        await worker.terminate();
    }
}

async function extractFile(filePath) {
    const ext = path.extname(filePath).toLowerCase();
    if (IMAGE_EXTENSIONS.has(ext)) {
        return extractImage(filePath);
    }
    return extractPdf(filePath);
}

function buildSummary(text, fallbackSummary) {
    if (fallbackSummary && fallbackSummary.trim()) return fallbackSummary.trim();
    if (!text || !text.trim()) return '';
    const cleaned = text.replace(/\s+/g, ' ').trim();
    return cleaned.slice(0, 600);
}

router.get('/system-health', async (_req, res) => {
    try {
        const latestAudit = await dbGet(`
            SELECT id, table_name, record_id, field_changed, changed_at
            FROM prediction_audit_log
            ORDER BY changed_at DESC
            LIMIT 1
        `);

        const latestAgentDaily = await dbGet(`
            SELECT snapshot_date, agent_name, predictions_30d, win_rate_30d, predictions_90d, win_rate_90d
            FROM agent_performance_daily
            ORDER BY snapshot_date DESC, agent_name ASC
            LIMIT 1
        `);

        return res.json({
            audit_log: latestAudit || null,
            agent_performance_daily: latestAgentDaily || null,
            checked_at: new Date().toISOString()
        });
    } catch (err) {
        if (isMissingTableError(err)) {
            return res.json({
                audit_log: null,
                agent_performance_daily: null,
                checked_at: new Date().toISOString()
            });
        }
        console.error('Admin system-health error:', err);
        return res.status(500).json({ error: 'Failed to load admin system health' });
    }
});

router.get('/reports', async (req, res) => {
    try {
        const limitRaw = parseInt(req.query.limit, 10);
        const limit = Number.isFinite(limitRaw) ? Math.min(Math.max(limitRaw, 1), 200) : 100;

        const rows = await dbAll(`
            SELECT
                id,
                filename,
                upload_date,
                language,
                summary,
                CASE
                    WHEN extracted_text IS NULL OR TRIM(extracted_text) = '' THEN 'Pending'
                    ELSE 'Processed'
                END AS status
            FROM market_reports
            ORDER BY upload_date DESC
            LIMIT ${ph(1)}
        `, [limit]);

        return res.json({ reports: rows });
    } catch (err) {
        if (isMissingTableError(err)) {
            return res.json({ reports: [] });
        }
        console.error('Admin reports list error:', err);
        return res.status(500).json({ error: 'Failed to load reports list' });
    }
});

router.post('/reports/upload', upload.single('report'), async (req, res) => {
    if (!req.file) {
        return res.status(400).json({ error: 'A PDF or image file is required (field name: report)' });
    }

    try {
        const ingest = await extractFile(req.file.path);
        const extractedText = typeof ingest.extracted_text === 'string' ? ingest.extracted_text : '';
        const language = String(ingest.language || 'EN').toUpperCase() === 'AR' ? 'AR' : 'EN';
        const summary = buildSummary(extractedText, ingest.summary || '');

        await dbRun(`
            INSERT INTO market_reports (filename, upload_date, extracted_text, language, summary)
            VALUES (${ph(1)}, CURRENT_TIMESTAMP, ${ph(2)}, ${ph(3)}, ${ph(4)})
        `, [req.file.originalname, extractedText, language, summary]);

        return res.status(201).json({
            ok: true,
            filename: req.file.originalname,
            language,
            summary,
            status: extractedText.trim() ? 'Processed' : 'Pending'
        });
    } catch (err) {
        console.error('Admin upload error:', err);
        return res.status(500).json({
            error: 'Failed to process uploaded report',
            details: err.message
        });
    }
});

module.exports = { router, attachDb };
