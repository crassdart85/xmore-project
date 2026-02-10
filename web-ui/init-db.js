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

    // Table 11: Sentiment Scores (Aggregated)
    await pool.query(`
      CREATE TABLE IF NOT EXISTS sentiment_scores (
        id SERIAL PRIMARY KEY,
        symbol TEXT NOT NULL,
        date DATE NOT NULL,
        avg_sentiment REAL,
        sentiment_label TEXT,
        article_count INTEGER DEFAULT 0,
        positive_count INTEGER DEFAULT 0,
        negative_count INTEGER DEFAULT 0,
        neutral_count INTEGER DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(symbol, date)
      )
    `);
    await pool.query('CREATE INDEX IF NOT EXISTS idx_sentiment_symbol_date ON sentiment_scores(symbol, date)');

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

    // Table 7: Consensus Results (3-Layer Pipeline Output)
    await pool.query(`
      CREATE TABLE IF NOT EXISTS consensus_results (
        id SERIAL PRIMARY KEY,
        symbol TEXT NOT NULL,
        prediction_date DATE NOT NULL,

        -- Final output
        final_signal TEXT NOT NULL,
        conviction TEXT,
        confidence REAL,
        risk_adjusted BOOLEAN DEFAULT FALSE,

        -- Agreement
        agent_agreement REAL,
        agents_agreeing INTEGER,
        agents_total INTEGER,
        majority_direction TEXT,

        -- Bull / Bear scores
        bull_score INTEGER,
        bear_score INTEGER,

        -- Risk
        risk_action TEXT,
        risk_score INTEGER,

        -- Full data (JSON)
        bull_case_json TEXT,
        bear_case_json TEXT,
        risk_assessment_json TEXT,
        agent_signals_json TEXT,
        reasoning_chain_json TEXT,
        display_json TEXT,

        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(symbol, prediction_date)
      )
    `);

    // Add reasoning column to predictions if it doesn't exist
    try {
      await pool.query('ALTER TABLE predictions ADD COLUMN IF NOT EXISTS reasoning TEXT');
      console.log('✅ Added reasoning column to predictions');
    } catch (err) {
      // Column may already exist, that's fine
    }

    // ============================================
    // AUTH & WATCHLIST TABLES
    // ============================================

    // Table 8: Users
    console.log('📊 Creating users table...');
    await pool.query(`
      CREATE TABLE IF NOT EXISTS users (
        id SERIAL PRIMARY KEY,
        email VARCHAR(255) NOT NULL,
        email_lower VARCHAR(255) NOT NULL UNIQUE,
        password_hash VARCHAR(255) NOT NULL,
        display_name VARCHAR(100),
        preferred_language VARCHAR(5) DEFAULT 'en',
        is_active BOOLEAN DEFAULT TRUE,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        last_login_at TIMESTAMP
      )
    `);

    // Table 9: EGX 30 Stocks reference
    console.log('📊 Creating egx30_stocks table...');
    await pool.query(`
      CREATE TABLE IF NOT EXISTS egx30_stocks (
        id SERIAL PRIMARY KEY,
        symbol VARCHAR(20) NOT NULL UNIQUE,
        name_en VARCHAR(200) NOT NULL,
        name_ar VARCHAR(200) NOT NULL,
        sector_en VARCHAR(100),
        sector_ar VARCHAR(100),
        is_active BOOLEAN DEFAULT TRUE,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
      )
    `);

    // Table 10: User Watchlist
    console.log('📊 Creating user_watchlist table...');
    await pool.query(`
      CREATE TABLE IF NOT EXISTS user_watchlist (
        id SERIAL PRIMARY KEY,
        user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        stock_id INTEGER NOT NULL REFERENCES egx30_stocks(id) ON DELETE CASCADE,
        added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(user_id, stock_id)
      )
    `);

    // Table 12: User Positions
    console.log('📊 Creating user_positions table...');
    await pool.query(`
      CREATE TABLE IF NOT EXISTS user_positions (
        id SERIAL PRIMARY KEY,
        user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        symbol TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'OPEN',
        entry_date DATE NOT NULL,
        entry_price REAL,
        exit_date DATE,
        exit_price REAL,
        return_pct REAL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
      )
    `);
    await pool.query("CREATE UNIQUE INDEX IF NOT EXISTS idx_unique_open_position ON user_positions(user_id, symbol) WHERE status = 'OPEN'");
    await pool.query("CREATE INDEX IF NOT EXISTS idx_positions_user ON user_positions(user_id)");

    // Table 13: Trade Recommendations
    console.log('📊 Creating trade_recommendations table...');
    await pool.query(`
      CREATE TABLE IF NOT EXISTS trade_recommendations (
        id SERIAL PRIMARY KEY,
        user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        symbol TEXT NOT NULL,
        recommendation_date DATE NOT NULL,
        action TEXT NOT NULL,
        signal TEXT NOT NULL,
        confidence INTEGER NOT NULL,
        conviction TEXT,
        risk_action TEXT,
        priority REAL,
        close_price REAL,
        stop_loss_pct REAL,
        target_pct REAL,
        stop_loss_price REAL,
        target_price REAL,
        risk_reward_ratio REAL,
        reasons TEXT,
        reasons_ar TEXT,
        bull_score INTEGER,
        bear_score INTEGER,
        agents_agreeing INTEGER,
        agents_total INTEGER,
        risk_flags TEXT,
        actual_next_day_return REAL,
        actual_5day_return REAL,
        was_correct BOOLEAN,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(user_id, symbol, recommendation_date)
      )
    `);
    await pool.query("CREATE INDEX IF NOT EXISTS idx_trade_rec_user_date ON trade_recommendations(user_id, recommendation_date DESC)");

    // Seed EGX 30 stocks
    console.log('🌱 Seeding EGX 30 stocks...');
    await pool.query(`
      INSERT INTO egx30_stocks (symbol, name_en, name_ar, sector_en, sector_ar) VALUES
      ('COMI.CA', 'Commercial International Bank', 'البنك التجاري الدولي', 'Banking', 'البنوك'),
      ('HRHO.CA', 'Hermes Holding', 'القابضة المصرية الكويتية (هيرميس)', 'Financial Services', 'الخدمات المالية'),
      ('TMGH.CA', 'Talaat Moustafa Group', 'مجموعة طلعت مصطفى', 'Real Estate', 'العقارات'),
      ('SWDY.CA', 'Elsewedy Electric', 'السويدي إليكتريك', 'Industrials', 'الصناعات'),
      ('EAST.CA', 'Eastern Company', 'الشرقية (إيسترن كومباني)', 'Consumer Staples', 'السلع الأساسية'),
      ('ETEL.CA', 'Telecom Egypt', 'المصرية للاتصالات', 'Telecom', 'الاتصالات'),
      ('ABUK.CA', 'Abu Qir Fertilizers', 'أبو قير للأسمدة', 'Materials', 'المواد'),
      ('ORWE.CA', 'Oriental Weavers', 'السجاد الشرقية (أوريانتال ويفرز)', 'Consumer Discretionary', 'السلع الاستهلاكية'),
      ('EFIH.CA', 'EFG Hermes', 'إي إف جي هيرميس', 'Financial Services', 'الخدمات المالية'),
      ('OCDI.CA', 'Orascom Development', 'أوراسكوم للتنمية', 'Real Estate', 'العقارات'),
      ('PHDC.CA', 'Palm Hills Development', 'بالم هيلز للتعمير', 'Real Estate', 'العقارات'),
      ('MNHD.CA', 'Madinet Nasr Housing', 'مدينة نصر للإسكان', 'Real Estate', 'العقارات'),
      ('CLHO.CA', 'Cleopatra Hospital', 'مستشفى كليوباترا', 'Healthcare', 'الرعاية الصحية'),
      ('EKHO.CA', 'Ezz Steel', 'حديد عز', 'Materials', 'المواد'),
      ('AMOC.CA', 'Alexandria Mineral Oils', 'الإسكندرية للزيوت المعدنية', 'Energy', 'الطاقة'),
      ('ESRS.CA', 'Ezz Steel (Rebars)', 'عز الدخيلة للصلب', 'Materials', 'المواد'),
      ('HELI.CA', 'Heliopolis Housing', 'مصر الجديدة للإسكان', 'Real Estate', 'العقارات'),
      ('GBCO.CA', 'GB Auto', 'جي بي أوتو', 'Consumer Discretionary', 'السلع الاستهلاكية'),
      ('CCAP.CA', 'Citadel Capital (Qalaa)', 'القلعة (سيتاديل كابيتال)', 'Financial Services', 'الخدمات المالية'),
      ('JUFO.CA', 'Juhayna Food', 'جهينة', 'Consumer Staples', 'السلع الأساسية'),
      ('SKPC.CA', 'Sidi Kerir Petrochemicals', 'سيدي كرير للبتروكيماويات', 'Materials', 'المواد'),
      ('ORAS.CA', 'Orascom Construction', 'أوراسكوم للإنشاءات', 'Industrials', 'الصناعات'),
      ('FWRY.CA', 'Fawry', 'فوري', 'Technology', 'التكنولوجيا'),
      ('EKHOA.CA', 'Ezz Aldekhela', 'عز الدخيلة', 'Materials', 'المواد'),
      ('BINV.CA', 'Beltone Financial', 'بلتون المالية القابضة', 'Financial Services', 'الخدمات المالية'),
      ('EIOD.CA', 'E-Finance', 'إي فاينانس', 'Technology', 'التكنولوجيا'),
      ('TALM.CA', 'Talem Medical', 'تاليم الطبية', 'Healthcare', 'الرعاية الصحية'),
      ('ADIB.CA', 'Abu Dhabi Islamic Bank Egypt', 'مصرف أبوظبي الإسلامي – مصر', 'Banking', 'البنوك'),
      ('DMCR.CA', 'Dice Medical & Scientific', 'دايس الطبية والعلمية', 'Healthcare', 'الرعاية الصحية'),
      ('ASCM.CA', 'Arabian Cement', 'الأسمنت العربية', 'Materials', 'المواد')
      ON CONFLICT (symbol) DO UPDATE SET
        name_en = EXCLUDED.name_en,
        name_ar = EXCLUDED.name_ar,
        sector_en = EXCLUDED.sector_en,
        sector_ar = EXCLUDED.sector_ar,
        is_active = TRUE,
        updated_at = CURRENT_TIMESTAMP
    `);
    console.log('✅ EGX 30 stocks seeded');

    // Create indexes
    console.log('📊 Creating indexes...');
    await pool.query('CREATE INDEX IF NOT EXISTS idx_prices_symbol_date ON prices(symbol, date)');
    await pool.query('CREATE INDEX IF NOT EXISTS idx_news_symbol_date ON news(symbol, date)');
    await pool.query('CREATE INDEX IF NOT EXISTS idx_predictions_symbol ON predictions(symbol, prediction_date)');
    await pool.query('CREATE INDEX IF NOT EXISTS idx_predictions_date ON predictions(prediction_date)');
    await pool.query('CREATE INDEX IF NOT EXISTS idx_consensus_symbol ON consensus_results(symbol, prediction_date)');
    await pool.query('CREATE INDEX IF NOT EXISTS idx_consensus_date ON consensus_results(prediction_date)');
    await pool.query('CREATE INDEX IF NOT EXISTS idx_users_email_lower ON users(email_lower)');
    await pool.query('CREATE INDEX IF NOT EXISTS idx_watchlist_user ON user_watchlist(user_id)');

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
