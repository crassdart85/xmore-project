console.log('=== INIT-DB.JS STARTING ===');
const { Pool } = require('pg');

const DATABASE_URL = process.env.DATABASE_URL;
console.log('DATABASE_URL exists:', !!DATABASE_URL);

if (!DATABASE_URL) {
    console.log('⚠️  No DATABASE_URL found. Skipping database initialization.');
    process.exit(0);
}

// Set a global timeout - exit after 30 seconds no matter what
const TIMEOUT_MS = 30000;
const timeoutId = setTimeout(() => {
    console.error('❌ Database initialization timed out after 30 seconds');
    process.exit(1);
}, TIMEOUT_MS);
timeoutId.unref(); // Don't keep process alive just for timeout

const pool = new Pool({
    connectionString: DATABASE_URL,
    ssl: { rejectUnauthorized: false },
    connectionTimeoutMillis: 10000,  // 10 second connection timeout
    idleTimeoutMillis: 10000
});

async function initializeDatabase() {
    console.log('🔧 Initializing PostgreSQL database...');
    console.log('📍 Connecting to:', DATABASE_URL.replace(/:[^:@]+@/, ':****@')); // Log URL without password

    try {
        // Test connection
        console.log('⏳ Testing database connection...');
        await pool.query('SELECT 1');
        console.log('✅ Connected to PostgreSQL');

        // Create tables
        console.log('📋 Creating tables...');

        // Table 1: Stock Prices
        await pool.query(`
      CREATE TABLE IF NOT EXISTS prices (
        id SERIAL PRIMARY KEY,
        symbol TEXT NOT NULL,
        date DATE NOT NULL,
        open REAL,
        high REAL,
        low REAL,
        close REAL NOT NULL,
        volume INTEGER,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        data_source TEXT DEFAULT 'yahoo_finance',
        UNIQUE(symbol, date)
      )
    `);

        // Table 2: Financial News
        await pool.query(`
      CREATE TABLE IF NOT EXISTS news (
        id SERIAL PRIMARY KEY,
        symbol TEXT NOT NULL,
        date DATE NOT NULL,
        headline TEXT NOT NULL,
        source TEXT,
        url TEXT,
        sentiment_score REAL,
        sentiment_label TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(symbol, headline, date)
      )
    `);

        // Table 3: Predictions
        await pool.query(`
      CREATE TABLE IF NOT EXISTS predictions (
        id SERIAL PRIMARY KEY,
        symbol TEXT NOT NULL,
        prediction_date DATE NOT NULL,
        target_date DATE NOT NULL,
        agent_name TEXT NOT NULL,
        prediction TEXT NOT NULL,
        confidence REAL,
        predicted_change_pct REAL,
        metadata TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(symbol, prediction_date, target_date, agent_name)
      )
    `);

        // Table 4: Evaluations
        await pool.query(`
      CREATE TABLE IF NOT EXISTS evaluations (
        id SERIAL PRIMARY KEY,
        prediction_id INTEGER NOT NULL,
        symbol TEXT NOT NULL,
        agent_name TEXT NOT NULL,
        prediction TEXT NOT NULL,
        actual_outcome TEXT,
        was_correct BOOLEAN,
        actual_change_pct REAL,
        prediction_error REAL,
        evaluated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (prediction_id) REFERENCES predictions(id)
      )
    `);

        // Table 5: Data Quality Log
        await pool.query(`
      CREATE TABLE IF NOT EXISTS data_quality_log (
        id SERIAL PRIMARY KEY,
        date DATE NOT NULL,
        symbol TEXT NOT NULL,
        issue_type TEXT NOT NULL,
        description TEXT,
        severity TEXT,
        resolved BOOLEAN DEFAULT FALSE,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
      )
    `);

        // Table 6: System Log
        await pool.query(`
      CREATE TABLE IF NOT EXISTS system_log (
        id SERIAL PRIMARY KEY,
        script_name TEXT NOT NULL,
        status TEXT NOT NULL,
        message TEXT,
        execution_time_seconds REAL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
      )
    `);

        // Create indexes
        console.log('📊 Creating indexes...');
        await pool.query('CREATE INDEX IF NOT EXISTS idx_prices_symbol_date ON prices(symbol, date)');
        await pool.query('CREATE INDEX IF NOT EXISTS idx_news_symbol_date ON news(symbol, date)');
        await pool.query('CREATE INDEX IF NOT EXISTS idx_predictions_symbol ON predictions(symbol, prediction_date)');
        await pool.query('CREATE INDEX IF NOT EXISTS idx_predictions_date ON predictions(prediction_date)');

        console.log('✅ Database initialized successfully!');

        // Get stats
        const statsQueries = {
            totalPrices: 'SELECT COUNT(*) as count FROM prices',
            totalPredictions: 'SELECT COUNT(*) as count FROM predictions',
            stocksTracked: 'SELECT COUNT(DISTINCT symbol) as count FROM prices',
        };

        console.log('\n📊 Database Statistics:');
        for (const [key, query] of Object.entries(statsQueries)) {
            const result = await pool.query(query);
            console.log(`   ${key}: ${result.rows[0].count}`);
        }

    } catch (error) {
        console.error('❌ Database initialization failed:', error);
        process.exit(1);
    } finally {
        await pool.end();
    }
}

initializeDatabase().then(() => {
    process.exit(0);
}).catch(() => {
    process.exit(1);
});
