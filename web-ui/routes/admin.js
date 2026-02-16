const express = require('express');
const fs = require('fs');
const path = require('path');
const multer = require('multer');
const { spawn } = require('child_process');
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

function pdfOnly(_req, file, cb) {
    const ext = path.extname(file.originalname || '').toLowerCase();
    const isPdfMime = file.mimetype === 'application/pdf';
    if (isPdfMime || ext === '.pdf') {
        cb(null, true);
        return;
    }
    cb(new Error('Only PDF files are allowed'));
}

const upload = multer({
    storage,
    fileFilter: pdfOnly,
    limits: { fileSize: 25 * 1024 * 1024 }
});

router.use(requireAdminSecret);

function runIngestScript(filePath) {
    return new Promise((resolve, reject) => {
        const pythonBin = process.env.PYTHON_BIN || 'python';
        const scriptPath = path.resolve(__dirname, '..', '..', 'engines', 'ingest_report.py');
        const child = spawn(pythonBin, [scriptPath, filePath], {
            cwd: path.resolve(__dirname, '..', '..')
        });

        let stdout = '';
        let stderr = '';
        child.stdout.on('data', chunk => { stdout += chunk.toString(); });
        child.stderr.on('data', chunk => { stderr += chunk.toString(); });

        child.on('error', reject);
        child.on('close', code => {
            if (code !== 0) {
                reject(new Error(stderr || `ingest_report.py exited with code ${code}`));
                return;
            }

            try {
                const parsed = JSON.parse(stdout.trim());
                resolve(parsed);
            } catch (_err) {
                reject(new Error('Failed to parse ingest_report.py output'));
            }
        });
    });
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
        return res.status(400).json({ error: 'PDF file is required (field name: report)' });
    }

    try {
        const ingest = await runIngestScript(req.file.path);
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
