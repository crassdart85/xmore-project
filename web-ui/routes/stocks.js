/**
 * Xmore — Stocks Route
 * GET /api/stocks — returns all active EGX 30 stocks
 */

const express = require('express');
const router = express.Router();

let db = null;

function attachDb(_db) {
    db = _db;
}

// GET /api/stocks — public, returns all active EGX 30 stocks
router.get('/stocks', (req, res) => {
    const isPostgres = db && db._isPostgres;
    console.log('DEBUG: /api/stocks hit. isPostgres:', isPostgres, 'Querying DB...');
    const query = `
    SELECT id, symbol, name_en, name_ar, sector_en, sector_ar
    FROM egx30_stocks
    WHERE is_active = ${isPostgres ? 'TRUE' : '1'}
    ORDER BY symbol
  `;

    if (!db || !db.all) {
        console.error('DEBUG: DB object missing or invalid');
        return res.status(500).json({ error: 'Database not initialized' });
    }

    db.all(query, [], (err, rows) => {
        if (err) {
            if (err.message && (err.message.includes('does not exist') || err.message.includes('no such table'))) {
                return res.json({ stocks: [] });
            }
            return res.status(500).json({ error: err.message });
        }
        res.json({ stocks: rows || [] });
    });
});

module.exports = { router, attachDb };
