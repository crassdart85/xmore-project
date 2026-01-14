const express = require('express');
const sqlite3 = require('sqlite3').verbose();
const cors = require('cors');
const path = require('path');

const app = express();
const PORT = process.env.PORT || 3000;

// Middleware
app.use(cors());
app.use(express.json());
app.use(express.static(path.join(__dirname, 'public')));

// Database connection
const dbPath = path.join(__dirname, '..', 'stocks.db');
const db = new sqlite3.Database(dbPath, sqlite3.OPEN_READONLY, (err) => {
  if (err) {
    console.error('❌ Database connection failed:', err);
  } else {
    console.log('✅ Connected to database');
  }
});

// ============================================
// API ENDPOINTS
// ============================================

// 1. Get latest predictions
app.get('/api/predictions', (req, res) => {
  console.log('Received request for /api/predictions');
  const query = `
    SELECT symbol, agent_name, prediction, prediction_date, target_date
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
      res.json(rows);
    }
  });
});

// 2. Get agent performance (accuracy)
app.get('/api/performance', (req, res) => {
  const query = `
    SELECT 
      agent_name,
      COUNT(*) as total_predictions,
      SUM(CASE WHEN was_correct = 1 THEN 1 ELSE 0 END) as correct_predictions,
      ROUND(AVG(CASE WHEN was_correct = 1 THEN 1.0 ELSE 0.0 END) * 100, 1) as accuracy
    FROM evaluations
    GROUP BY agent_name
  `;
  
  db.all(query, [], (err, rows) => {
    if (err) {
      res.status(500).json({ error: err.message });
    } else {
      res.json(rows);
    }
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
      res.json(rows);
    }
  });
});

// 4. Get system stats
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
      if (!err) {
        stats[key] = row.count || row.date;
      }
      completed++;
      if (completed === Object.keys(queries).length) {
        res.json(stats);
      }
    });
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

app.listen(PORT, () => {
  console.log(`🚀 Server running at http://localhost:${PORT}`);
  console.log(`📊 Dashboard: http://localhost:${PORT}`);
});