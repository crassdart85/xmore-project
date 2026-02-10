console.log('=== SERVER.JS STARTING ===');
const express = require('express');
const cors = require('cors');
const path = require('path');

const app = express();
const PORT = process.env.PORT || 3000;

// Middleware
app.use(cors());
app.use(express.json());
app.use(express.static(path.join(__dirname, 'public')));

// ============================================
// DATABASE CONNECTION (PostgreSQL or SQLite)
// ============================================

const DATABASE_URL = process.env.DATABASE_URL;

let db;

if (DATABASE_URL) {
  // Production: PostgreSQL
  const { Pool } = require('pg');
  const pool = new Pool({ connectionString: DATABASE_URL, ssl: { rejectUnauthorized: false } });

  db = {
    all: (query, params, callback) => {
      pool.query(query, params)
        .then(result => callback(null, result.rows))
        .catch(err => callback(err));
    },
    get: (query, params, callback) => {
      pool.query(query, params)
        .then(result => callback(null, result.rows[0] || null))
        .catch(err => callback(err));
    }
  };

  pool.query('SELECT 1')
    .then(() => console.log('✅ Connected to PostgreSQL database'))
    .catch(err => console.error('❌ PostgreSQL connection failed:', err));

} else {
  // Local: SQLite
  try {
    const sqlite3 = require('sqlite3').verbose();
    const dbPath = path.join(__dirname, '..', 'stocks.db');
    const sqliteDb = new sqlite3.Database(dbPath, sqlite3.OPEN_READONLY, (err) => {
      if (err) {
        console.error('❌ Database connection failed:', err);
      } else {
        console.log('✅ Connected to SQLite database');
      }
    });

    db = {
      all: (query, params, callback) => sqliteDb.all(query, params, callback),
      get: (query, params, callback) => sqliteDb.get(query, params, callback)
    };
  } catch (err) {
    console.warn('⚠️  SQLite not available (this is normal on Render). Using PostgreSQL only.');
    // Create a dummy db object that will fail gracefully
    db = {
      all: (query, params, callback) => callback(new Error('No database configured')),
      get: (query, params, callback) => callback(new Error('No database configured'))
    };
  }
}

// ============================================
// API ENDPOINTS
// ============================================

// 1. Get latest predictions
app.get('/api/predictions', (req, res) => {
  console.log('Received request for /api/predictions');
  const query = `
    SELECT symbol, agent_name, prediction, confidence, metadata, prediction_date, target_date
    FROM predictions
    WHERE prediction_date = (SELECT MAX(prediction_date) FROM predictions)
    ORDER BY symbol, agent_name
  `;

  console.log('Executing query for /api/predictions');
  db.all(query, [], (err, rows) => {
    if (err) {
      console.error('Error executing query for /api/predictions:', err);
      res.status(500).json({ error: err.message });
    } else {
      console.log('Successfully executed query for /api/predictions');
      res.json({
        disclaimer: 'Xmore is an information and analytics tool, not a licensed investment advisor. This is not financial advice. Past performance does not guarantee future results.',
        predictions: rows || []
      });
    }
  });
});

// 2. Get agent performance (accuracy)
app.get('/api/performance', (req, res) => {
  // Use different boolean syntax for PostgreSQL vs SQLite
  const boolTrue = DATABASE_URL ? 'true' : '1';
  const query = `
    SELECT
      agent_name,
      COUNT(*) as total_predictions,
      SUM(CASE WHEN was_correct = ${boolTrue} THEN 1 ELSE 0 END) as correct_predictions,
      ROUND(AVG(CASE WHEN was_correct = ${boolTrue} THEN 1.0 ELSE 0.0 END) * 100, 1) as accuracy
    FROM evaluations
    GROUP BY agent_name
  `;

  db.all(query, [], (err, rows) => {
    if (err) {
      // Table might not exist yet (PostgreSQL: "does not exist", SQLite: "no such table")
      if (err.message && (err.message.includes('does not exist') || err.message.includes('no such table'))) {
        res.json([]);
      } else {
        res.status(500).json({ error: err.message });
      }
    } else {
      res.json(rows || []);
    }
  });
});

// 2b. Detailed performance metrics (Phase 1 Task 4)
app.get('/api/performance/detailed', (req, res) => {
  const boolTrue = DATABASE_URL ? 'true' : '1';

  // We'll run multiple queries and combine results
  const results = { overall: {}, per_agent: {}, per_stock: {}, monthly: [] };
  let completed = 0;
  const totalQueries = 4;

  function checkDone() {
    completed++;
    if (completed === totalQueries) {
      res.json(results);
    }
  }

  // 1. Overall metrics
  db.get(`
    SELECT
      COUNT(*) as total_predictions,
      SUM(CASE WHEN was_correct = ${boolTrue} THEN 1 ELSE 0 END) as correct_predictions,
      ROUND(AVG(CASE WHEN was_correct = ${boolTrue} THEN 1.0 ELSE 0.0 END) * 100, 1) as directional_accuracy,
      ROUND(AVG(actual_change_pct), 4) as avg_return_per_signal,
      ROUND(AVG(CASE WHEN prediction = 'UP' AND was_correct = ${boolTrue} THEN 1.0
                       WHEN prediction = 'UP' THEN 0.0 END) * 100, 1) as win_rate_buy,
      ROUND(AVG(CASE WHEN prediction = 'DOWN' AND was_correct = ${boolTrue} THEN 1.0
                       WHEN prediction = 'DOWN' THEN 0.0 END) * 100, 1) as win_rate_sell,
      MIN(actual_change_pct) as max_drawdown
    FROM evaluations
  `, [], (err, row) => {
    if (err || !row) {
      results.overall = {
        directional_accuracy: 0, total_predictions: 0, correct_predictions: 0,
        avg_return_per_signal: 0, win_rate_buy: 0, win_rate_sell: 0, max_drawdown: 0
      };
    } else {
      results.overall = {
        directional_accuracy: row.directional_accuracy || 0,
        total_predictions: row.total_predictions || 0,
        correct_predictions: row.correct_predictions || 0,
        avg_return_per_signal: row.avg_return_per_signal || 0,
        win_rate_buy: row.win_rate_buy || 0,
        win_rate_sell: row.win_rate_sell || 0,
        max_drawdown: row.max_drawdown || 0
      };
    }
    checkDone();
  });

  // 2. Per-agent metrics
  db.all(`
    SELECT
      agent_name,
      COUNT(*) as total,
      SUM(CASE WHEN was_correct = ${boolTrue} THEN 1 ELSE 0 END) as correct,
      ROUND(AVG(CASE WHEN was_correct = ${boolTrue} THEN 1.0 ELSE 0.0 END) * 100, 1) as accuracy
    FROM evaluations
    GROUP BY agent_name
    ORDER BY accuracy DESC
  `, [], (err, rows) => {
    if (!err && rows) {
      rows.forEach(r => {
        results.per_agent[r.agent_name] = {
          accuracy: r.accuracy || 0,
          total: r.total || 0,
          correct: r.correct || 0
        };
      });
    }
    checkDone();
  });

  // 3. Per-stock metrics
  db.all(`
    SELECT
      symbol,
      COUNT(*) as predictions,
      ROUND(AVG(CASE WHEN was_correct = ${boolTrue} THEN 1.0 ELSE 0.0 END) * 100, 1) as accuracy,
      ROUND(AVG(actual_change_pct), 4) as avg_return
    FROM evaluations
    GROUP BY symbol
    ORDER BY accuracy DESC
  `, [], (err, rows) => {
    if (!err && rows) {
      rows.forEach(r => {
        results.per_stock[r.symbol] = {
          accuracy: r.accuracy || 0,
          avg_return: r.avg_return || 0,
          predictions: r.predictions || 0
        };
      });
    }
    checkDone();
  });

  // 4. Monthly breakdown
  const monthExtract = DATABASE_URL
    ? "TO_CHAR(p.prediction_date::date, 'YYYY-MM')"
    : "strftime('%Y-%m', p.prediction_date)";

  db.all(`
    SELECT
      ${monthExtract} as month,
      COUNT(*) as predictions,
      ROUND(AVG(CASE WHEN e.was_correct = ${boolTrue} THEN 1.0 ELSE 0.0 END) * 100, 1) as accuracy,
      ROUND(AVG(e.actual_change_pct), 4) as avg_return
    FROM evaluations e
    JOIN predictions p ON e.prediction_id = p.id
    GROUP BY ${monthExtract}
    ORDER BY month DESC
    LIMIT 12
  `, [], (err, rows) => {
    if (!err && rows) {
      results.monthly = rows.map(r => ({
        month: r.month,
        accuracy: r.accuracy || 0,
        predictions: r.predictions || 0,
        avg_return: r.avg_return || 0
      }));
    }
    checkDone();
  });
});

// 3. Get latest stock prices
app.get('/api/prices', (req, res) => {
  const query = `
    SELECT symbol, date, close, volume
    FROM prices
    WHERE date = (SELECT MAX(date) FROM prices WHERE symbol = prices.symbol)
    ORDER BY symbol
  `;

  db.all(query, [], (err, rows) => {
    if (err) {
      res.status(500).json({ error: err.message });
    } else {
      res.json(rows || []);
    }
  });
});

// 4. Get latest sentiment scores
app.get('/api/sentiment', (req, res) => {
  // Get the most recent sentiment for each stock
  const query = DATABASE_URL
    ? `SELECT DISTINCT ON (symbol) symbol, date, avg_sentiment, sentiment_label, article_count
       FROM sentiment_scores
       ORDER BY symbol, date DESC`
    : `SELECT s.symbol, s.date, s.avg_sentiment, s.sentiment_label, s.article_count
       FROM sentiment_scores s
       INNER JOIN (
         SELECT symbol, MAX(date) as max_date
         FROM sentiment_scores
         GROUP BY symbol
       ) latest ON s.symbol = latest.symbol AND s.date = latest.max_date
       ORDER BY s.symbol`;

  db.all(query, [], (err, rows) => {
    if (err) {
      // Table might not exist yet
      if (err.message && err.message.includes('no such table')) {
        res.json([]);
      } else {
        res.status(500).json({ error: err.message });
      }
    } else {
      res.json(rows || []);
    }
  });
});

// 5. Get system stats
app.get('/api/stats', (req, res) => {
  const queries = {
    totalPrices: 'SELECT COUNT(*) as count FROM prices',
    totalPredictions: 'SELECT COUNT(*) as count FROM predictions',
    stocksTracked: 'SELECT COUNT(DISTINCT symbol) as count FROM prices',
    latestDate: 'SELECT MAX(date) as date FROM prices'
  };

  const stats = {};
  let completed = 0;

  Object.keys(queries).forEach(key => {
    db.get(queries[key], [], (err, row) => {
      if (!err && row) {
        stats[key] = row.count || row.date;
      }
      completed++;
      if (completed === Object.keys(queries).length) {
        res.json(stats);
      }
    });
  });
});

// 6. Get prediction evaluations (for results comparison)
app.get('/api/evaluations', (req, res) => {
  const boolTrue = DATABASE_URL ? 'true' : '1';
  const query = `
    SELECT
      e.symbol,
      e.agent_name,
      e.prediction,
      e.actual_outcome,
      e.was_correct,
      e.actual_change_pct,
      p.prediction_date,
      p.target_date
    FROM evaluations e
    JOIN predictions p ON e.prediction_id = p.id
    ORDER BY p.target_date DESC, e.symbol, e.agent_name
    LIMIT 100
  `;

  db.all(query, [], (err, rows) => {
    if (err) {
      if (err.message && (err.message.includes('does not exist') || err.message.includes('no such table'))) {
        res.json([]);
      } else {
        res.status(500).json({ error: err.message });
      }
    } else {
      res.json(rows || []);
    }
  });
});

// ============================================
// FRONTEND ROUTE
// ============================================
app.get('*', (req, res) => {
  res.sendFile(path.join(__dirname, 'public', 'index.html'));
});


// ============================================
// START SERVER
// ============================================

console.log(`⏳ Starting server on port ${PORT}...`);
app.listen(PORT, '0.0.0.0', () => {
  console.log(`🚀 Server running on port ${PORT}`);
  console.log(`📊 Dashboard available`);
});
