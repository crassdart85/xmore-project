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

    // Table: Daily Briefings (one global row per date)
    await pool.query(`
      CREATE TABLE IF NOT EXISTS daily_briefings (
        id SERIAL PRIMARY KEY,
        briefing_date DATE NOT NULL UNIQUE,
        market_pulse_json TEXT,
        sector_breakdown_json TEXT,
        risk_alerts_json TEXT,
        sentiment_snapshot_json TEXT,
        stocks_processed INTEGER,
        generation_time_seconds REAL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
      )
    `);
    await pool.query("CREATE INDEX IF NOT EXISTS idx_briefings_date ON daily_briefings(briefing_date DESC)");

    // Table: Market Intelligence reports (Admin dashboard)
    await pool.query(`
      CREATE TABLE IF NOT EXISTS market_reports (
        id SERIAL PRIMARY KEY,
        filename TEXT NOT NULL,
        upload_date TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        extracted_text TEXT,
        language VARCHAR(2) NOT NULL DEFAULT 'EN',
        summary TEXT,
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        CONSTRAINT chk_market_reports_language CHECK (language IN ('EN', 'AR'))
      )
    `);
    await pool.query('CREATE INDEX IF NOT EXISTS idx_market_reports_upload_date ON market_reports(upload_date DESC)');

    // Seed ALL EGX stocks (~190)
    console.log('🌱 Seeding EGX stocks...');
    await pool.query(`
      INSERT INTO egx30_stocks (symbol, name_en, name_ar, sector_en, sector_ar) VALUES
      -- Banking
      ('COMI.CA', 'Commercial International Bank (CIB)', 'البنك التجاري الدولي', 'Banking', 'البنوك'),
      ('ADIB.CA', 'Abu Dhabi Islamic Bank Egypt', 'مصرف أبوظبي الإسلامي – مصر', 'Banking', 'البنوك'),
      ('QNBE.CA', 'Qatar National Bank Al Ahli', 'بنك قطر الوطني الأهلي', 'Banking', 'البنوك'),
      ('HDBK.CA', 'Housing and Development Bank', 'بنك التعمير والإسكان', 'Banking', 'البنوك'),
      ('CIEB.CA', 'Credit Agricole Egypt', 'بنك كريدي أجريكول مصر', 'Banking', 'البنوك'),
      ('CANA.CA', 'Suez Canal Bank', 'بنك قناة السويس', 'Banking', 'البنوك'),
      ('FAIT.CA', 'Faisal Islamic Bank of Egypt (EGP)', 'بنك فيصل الإسلامي المصري بالجنيه', 'Banking', 'البنوك'),
      ('FAITA.CA', 'Faisal Islamic Bank of Egypt (USD)', 'بنك فيصل الإسلامي المصري بالدولار', 'Banking', 'البنوك'),
      ('EXPA.CA', 'Export Development Bank of Egypt', 'البنك المصري لتنمية الصادرات', 'Banking', 'البنوك'),
      ('SAUD.CA', 'Al Baraka Bank Egypt', 'بنك البركة مصر', 'Banking', 'البنوك'),
      ('UBEE.CA', 'The United Bank', 'المصرف المتحد', 'Banking', 'البنوك'),
      ('EGBE.CA', 'Egyptian Gulf Bank', 'البنك المصري الخليجي', 'Banking', 'البنوك'),
      ('SAIB.CA', 'Societe Arabe Internationale de Banque', 'بنك الشركة المصرفية العربية الدولية', 'Banking', 'البنوك'),
      -- Financial Services
      ('HRHO.CA', 'EFG Hermes Holding', 'المجموعة المالية هيرمس القابضة', 'Financial Services', 'الخدمات المالية'),
      ('EFIH.CA', 'e-Finance for Digital & Financial Investments', 'إي فاينانس للاستثمارات المالية والرقمية', 'Financial Services', 'الخدمات المالية'),
      ('FWRY.CA', 'Fawry for Banking Technology', 'فوري لتكنولوجيا البنوك والمدفوعات', 'Financial Services', 'الخدمات المالية'),
      ('CCAP.CA', 'Qalaa Holdings', 'القلعة القابضة', 'Financial Services', 'الخدمات المالية'),
      ('BINV.CA', 'B Investments Holding', 'بي إنفستمنتس القابضة', 'Financial Services', 'الخدمات المالية'),
      ('CICH.CA', 'CI Capital Holding', 'سي آي كابيتال القابضة', 'Financial Services', 'الخدمات المالية'),
      ('VALU.CA', 'U Consumer Finance', 'يو للتمويل الاستهلاكي', 'Financial Services', 'الخدمات المالية'),
      ('RAYA.CA', 'Raya Holding', 'راية القابضة', 'Financial Services', 'الخدمات المالية'),
      ('CNFN.CA', 'Contact Financial Holding', 'كونتكت المالية القابضة', 'Financial Services', 'الخدمات المالية'),
      ('ACAP.CA', 'A Capital Holding', 'ايه كابيتال القابضة', 'Financial Services', 'الخدمات المالية'),
      ('ATLC.CA', 'Al Tawfeek Leasing', 'التوفيق للتأجير التمويلي', 'Financial Services', 'الخدمات المالية'),
      ('ICLE.CA', 'International Co. for Leasing', 'الدولية للتأجير التمويلي', 'Financial Services', 'الخدمات المالية'),
      ('ANFI.CA', 'Alexandria National Financial Investments', 'الاسكندرية الوطنية للاستثمارات المالية', 'Financial Services', 'الخدمات المالية'),
      ('PRMH.CA', 'Prime Holding', 'برايم القابضة للاستثمارات المالية', 'Financial Services', 'الخدمات المالية'),
      ('GRCA.CA', 'Grand Investment Capital', 'جراند انفستمنت القابضة', 'Financial Services', 'الخدمات المالية'),
      ('ASPI.CA', 'Aspire Capital Holding', 'اسباير كابيتال القابضة', 'Financial Services', 'الخدمات المالية'),
      ('BTFH.CA', 'Beltone Financial Holding', 'بلتون المالية القابضة', 'Financial Services', 'الخدمات المالية'),
      ('OFH.CA', 'Orascom Financial Holding', 'أوراسكوم المالية القابضة', 'Financial Services', 'الخدمات المالية'),
      ('RACC.CA', 'Raya Customer Experience', 'راية لخدمات مراكز الاتصالات', 'Financial Services', 'الخدمات المالية'),
      ('ODIN.CA', 'ODIN Investments', 'أودن للاستثمارات المالية', 'Financial Services', 'الخدمات المالية'),
      -- Real Estate
      ('TMGH.CA', 'Talaat Moustafa Group Holding', 'مجموعة طلعت مصطفى القابضة', 'Real Estate', 'العقارات'),
      ('PHDC.CA', 'Palm Hills Development', 'بالم هيلز للتعمير', 'Real Estate', 'العقارات'),
      ('OCDI.CA', 'SODIC', 'السادس من أكتوبر للتنمية والاستثمار', 'Real Estate', 'العقارات'),
      ('ORHD.CA', 'Orascom Development Egypt', 'أوراسكوم للتنمية مصر', 'Real Estate', 'العقارات'),
      ('EMFD.CA', 'Emaar Misr for Development', 'إعمار مصر للتنمية', 'Real Estate', 'العقارات'),
      ('MNHD.CA', 'Madinet Nasr Housing', 'مدينة نصر للإسكان والتعمير', 'Real Estate', 'العقارات'),
      ('HELI.CA', 'Heliopolis Housing & Development', 'مصر الجديدة للإسكان والتعمير', 'Real Estate', 'العقارات'),
      ('CIRA.CA', 'Cairo for Investment & Real Estate', 'القاهرة للاستثمار والتنمية العقارية', 'Real Estate', 'العقارات'),
      ('ZMID.CA', 'Zahraa El Maadi Investment', 'زهراء المعادي للاستثمار والتعمير', 'Real Estate', 'العقارات'),
      ('ARAB.CA', 'Arab Developers Holding', 'المطورون العرب القابضة', 'Real Estate', 'العقارات'),
      ('GPPL.CA', 'Golden Pyramids Plaza', 'جولدن بيراميدز بلازا', 'Real Estate', 'العقارات'),
      ('ELKA.CA', 'Cairo Housing & Development', 'القاهرة للإسكان والتعمير', 'Real Estate', 'العقارات'),
      ('UNIT.CA', 'United Housing & Development', 'المتحدة للإسكان والتعمير', 'Real Estate', 'العقارات'),
      ('PRDC.CA', 'Pioneers Properties', 'بايونيرز بروبرتيز للتنمية العمرانية', 'Real Estate', 'العقارات'),
      ('ELSH.CA', 'Al Shams Housing', 'الشمس للإسكان والتعمير', 'Real Estate', 'العقارات'),
      ('EHDR.CA', 'Egyptians for Housing', 'المصريين للإسكان والتنمية', 'Real Estate', 'العقارات'),
      ('OBRI.CA', 'El Ebour Real Estate', 'العبور للاستثمار العقاري', 'Real Estate', 'العقارات'),
      ('BONY.CA', 'Bonyan for Development', 'بنيان للتنمية والتجارة', 'Real Estate', 'العقارات'),
      ('TANM.CA', 'Tanmiya Real Estate', 'تنمية للاستثمار العقاري', 'Real Estate', 'العقارات'),
      ('IDRE.CA', 'Ismailia Development & Real Estate', 'الاسماعيلية للتطوير والتنمية العمرانية', 'Real Estate', 'العقارات'),
      ('NHPS.CA', 'National Housing Professional Syndicates', 'الوطنية للإسكان للنقابات المهنية', 'Real Estate', 'العقارات'),
      ('MAAL.CA', 'Marseille Egyptian-Khaleeji Investment', 'مرسيليا المصرية الخليجية للاستثمار العقاري', 'Real Estate', 'العقارات'),
      ('AREH.CA', 'Real Estate Egyptian Consortium', 'المجموعة المصرية العقارية', 'Real Estate', 'العقارات'),
      ('COPR.CA', 'Copper Commercial Investment', 'كوبر للاستثمار التجاري والتطوير العقاري', 'Real Estate', 'العقارات'),
      ('GIHD.CA', 'Gharbia Islamic Housing', 'الغربية الإسلامية للتنمية العمرانية', 'Real Estate', 'العقارات'),
      -- Chemicals & Fertilizers
      ('ABUK.CA', 'Abu Qir Fertilizers', 'أبو قير للأسمدة والصناعات الكيماوية', 'Chemicals', 'الكيماويات'),
      ('MFPC.CA', 'Misr Fertilizers (MOPCO)', 'مصر لإنتاج الأسمدة (موبكو)', 'Chemicals', 'الكيماويات'),
      ('SKPC.CA', 'Sidi Kerir Petrochemicals', 'سيدي كرير للبتروكيماويات', 'Chemicals', 'الكيماويات'),
      ('EGCH.CA', 'Egyptian Chemical Industries (KIMA)', 'الصناعات الكيماوية المصرية (كيما)', 'Chemicals', 'الكيماويات'),
      ('MICH.CA', 'Misr Chemical Industries', 'مصر لصناعة الكيماويات', 'Chemicals', 'الكيماويات'),
      ('KZPC.CA', 'Kafr El Zayat Pesticides', 'كفر الزيات للمبيدات والكيماويات', 'Chemicals', 'الكيماويات'),
      ('SMFR.CA', 'Samad Misr (EGYFERT)', 'سماد مصر', 'Chemicals', 'الكيماويات'),
      ('FERC.CA', 'Ferchem Misr Fertilizers', 'فيركيم مصر للأسمدة والكيماويات', 'Chemicals', 'الكيماويات'),
      -- Industrial & Manufacturing
      ('SWDY.CA', 'Elsewedy Electric', 'السويدي إليكتريك', 'Industrials', 'الصناعات'),
      ('EAST.CA', 'Eastern Company (Tobacco)', 'الشرقية – إيسترن كومباني', 'Consumer Staples', 'السلع الأساسية'),
      ('GBCO.CA', 'GB Corp (Ghabbour Auto)', 'جي بي أوتو', 'Industrials', 'الصناعات'),
      ('ORWE.CA', 'Oriental Weavers Carpets', 'النساجون الشرقيون للسجاد', 'Industrials', 'الصناعات'),
      ('ORAS.CA', 'Orascom Construction', 'أوراسكوم للإنشاءات', 'Industrials', 'الصناعات'),
      ('ESRS.CA', 'Ezz Steel', 'حديد عز', 'Materials', 'المواد'),
      ('EKHOA.CA', 'Ezz Aldekhela Steel', 'عز الدخيلة للصلب', 'Materials', 'المواد'),
      ('EKHO.CA', 'Egypt Kuwait Holding', 'القابضة المصرية الكويتية', 'Industrials', 'الصناعات'),
      ('EGAL.CA', 'Egypt Aluminum', 'مصر للألومنيوم', 'Materials', 'المواد'),
      ('IRON.CA', 'Egyptian Iron & Steel', 'الحديد والصلب المصرية', 'Materials', 'المواد'),
      ('MTIE.CA', 'MM Group for Industry & Trade', 'ام.ام جروب للصناعة والتجارة العالمية', 'Industrials', 'الصناعات'),
      ('ELEC.CA', 'Electro Cable Egypt', 'الكابلات الكهربائية المصرية', 'Industrials', 'الصناعات'),
      ('ACRO.CA', 'Acrow Misr', 'أكرو مصر للشدات والسقالات', 'Industrials', 'الصناعات'),
      ('EFIC.CA', 'Egyptian Financial & Industrial', 'المالية والصناعية المصرية', 'Industrials', 'الصناعات'),
      ('ATQA.CA', 'Misr National Steel (Ataqa)', 'مصر الوطنية للصلب (عتاقة)', 'Materials', 'المواد'),
      ('ALUM.CA', 'Arab Aluminum', 'الألومنيوم العربية', 'Materials', 'المواد'),
      ('ARVA.CA', 'Arab Valves', 'العربية للمحابس', 'Industrials', 'الصناعات'),
      ('GDWA.CA', 'Gadwa Industrial Development', 'جدوى للتنمية الصناعية', 'Industrials', 'الصناعات'),
      ('GSSC.CA', 'General Co. for Silos & Storage', 'العامة للصوامع والتخزين', 'Industrials', 'الصناعات'),
      ('ASCM.CA', 'ASEC Company for Mining (ASCOM)', 'أسيك للتعدين', 'Materials', 'المواد'),
      -- Food & Beverage
      ('JUFO.CA', 'Juhayna Food Industries', 'جهينة للصناعات الغذائية', 'Food & Beverage', 'الأغذية والمشروبات'),
      ('EFID.CA', 'Edita Food Industries', 'إيديتا للصناعات الغذائية', 'Food & Beverage', 'الأغذية والمشروبات'),
      ('DOMT.CA', 'Domty (Arabian Food Industries)', 'دومتي – الصناعات الغذائية العربية', 'Food & Beverage', 'الأغذية والمشروبات'),
      ('POUL.CA', 'Cairo Poultry Company', 'القاهرة للدواجن', 'Food & Beverage', 'الأغذية والمشروبات'),
      ('SUGR.CA', 'Delta Sugar', 'الدلتا للسكر', 'Food & Beverage', 'الأغذية والمشروبات'),
      ('OLFI.CA', 'Obour Land for Food Industries', 'عبور لاند للصناعات الغذائية', 'Food & Beverage', 'الأغذية والمشروبات'),
      ('AJWA.CA', 'AJWA for Food Industries', 'أجواء للصناعات الغذائية', 'Food & Beverage', 'الأغذية والمشروبات'),
      ('AFMC.CA', 'Alexandria Flour Mills', 'مطاحن ومخابز الإسكندرية', 'Food & Beverage', 'الأغذية والمشروبات'),
      ('ADPC.CA', 'Arab Dairy Products (Panda)', 'العربية لمنتجات الألبان (باندا)', 'Food & Beverage', 'الأغذية والمشروبات'),
      ('INFI.CA', 'Ismailia National Food Industries', 'الاسماعيلية الوطنية للصناعات الغذائية', 'Food & Beverage', 'الأغذية والمشروبات'),
      ('MPCO.CA', 'Mansoura Poultry', 'المنصورة للدواجن', 'Food & Beverage', 'الأغذية والمشروبات'),
      ('EPCO.CA', 'Egypt for Poultry', 'المصرية للدواجن', 'Food & Beverage', 'الأغذية والمشروبات'),
      ('WCDF.CA', 'Middle & West Delta Flour Mills', 'مطاحن وسط وغرب الدلتا', 'Food & Beverage', 'الأغذية والمشروبات'),
      ('UEFM.CA', 'Upper Egypt Flour Mills', 'مطاحن مصر العليا', 'Food & Beverage', 'الأغذية والمشروبات'),
      ('EDFM.CA', 'East Delta Flour Mills', 'مطاحن شرق الدلتا', 'Food & Beverage', 'الأغذية والمشروبات'),
      ('SCFM.CA', 'South Cairo & Giza Flour Mills', 'مطاحن ومخابز جنوب القاهرة والجيزة', 'Food & Beverage', 'الأغذية والمشروبات'),
      ('CEFM.CA', 'Middle Egypt Flour Mills', 'مطاحن مصر الوسطى', 'Food & Beverage', 'الأغذية والمشروبات'),
      ('MILS.CA', 'North Cairo Flour Mills', 'مطاحن ومخابز شمال القاهرة', 'Food & Beverage', 'الأغذية والمشروبات'),
      -- Pharmaceuticals
      ('PHAR.CA', 'EIPICO (Egyptian International Pharma)', 'المصرية الدولية للصناعات الدوائية', 'Pharmaceuticals', 'الأدوية'),
      ('ISPH.CA', 'Ibnsina Pharma', 'ابن سينا فارما', 'Pharmaceuticals', 'الأدوية'),
      ('RMDA.CA', 'Rameda Pharma', 'العاشر من رمضان للصناعات الدوائية (راميدا)', 'Pharmaceuticals', 'الأدوية'),
      ('BIOC.CA', 'GlaxoSmithKline Egypt', 'جلاكسو سميثكلاين مصر', 'Pharmaceuticals', 'الأدوية'),
      ('NIPH.CA', 'El-Nile Pharmaceuticals', 'النيل للأدوية والصناعات الكيماوية', 'Pharmaceuticals', 'الأدوية'),
      ('MIPH.CA', 'Minapharm Pharmaceuticals', 'مينا فارم للأدوية', 'Pharmaceuticals', 'الأدوية'),
      ('AXPH.CA', 'Alexandria Pharmaceuticals', 'الإسكندرية للأدوية والصناعات الكيماوية', 'Pharmaceuticals', 'الأدوية'),
      ('CPCI.CA', 'Cairo Pharmaceuticals', 'القاهرة للأدوية والصناعات الكيماوية', 'Pharmaceuticals', 'الأدوية'),
      ('MPCI.CA', 'Memphis Pharmaceuticals', 'ممفيس للأدوية', 'Pharmaceuticals', 'الأدوية'),
      ('OCPH.CA', 'October Pharma', 'أكتوبر فارما', 'Pharmaceuticals', 'الأدوية'),
      ('ADCI.CA', 'Arab Drug Company', 'العربية للأدوية', 'Pharmaceuticals', 'الأدوية'),
      ('SIPC.CA', 'Sabaa International Pharma', 'سبأ الدولية للأدوية', 'Pharmaceuticals', 'الأدوية'),
      ('MCRO.CA', 'Macro Group Pharmaceuticals', 'ماكرو جروب للمستحضرات الطبية', 'Pharmaceuticals', 'الأدوية'),
      -- Telecom & Technology
      ('ETEL.CA', 'Telecom Egypt', 'المصرية للاتصالات', 'Telecom', 'الاتصالات'),
      ('EGSA.CA', 'Egyptian Satellite (NileSat)', 'المصرية للأقمار الصناعية (نايل سات)', 'Telecom', 'الاتصالات'),
      ('MPRC.CA', 'Egyptian Media Production City', 'المصرية لمدينة الإنتاج الإعلامي', 'Technology', 'التكنولوجيا'),
      ('SCTS.CA', 'Suez Canal for Technology', 'قناة السويس لتوطين التكنولوجيا', 'Technology', 'التكنولوجيا'),
      -- Construction & Cement
      ('ARCC.CA', 'Arabian Cement Company', 'الأسمنت العربية', 'Construction', 'البناء والتشييد'),
      ('MCQE.CA', 'Misr Cement (Qena)', 'مصر للأسمنت (قنا)', 'Construction', 'البناء والتشييد'),
      ('SCEM.CA', 'Sinai Cement', 'أسمنت سيناء', 'Construction', 'البناء والتشييد'),
      ('MBSC.CA', 'Misr Beni Suef Cement', 'مصر بني سويف للأسمنت', 'Construction', 'البناء والتشييد'),
      ('SVCE.CA', 'South Valley Cement', 'جنوب الوادي للأسمنت', 'Construction', 'البناء والتشييد'),
      ('ENGC.CA', 'Industrial Engineering (ICON)', 'الصناعات الهندسية للإنشاء والتعمير', 'Construction', 'البناء والتشييد'),
      ('NCCW.CA', 'Nasr Co. for Civil Works', 'النصر للأعمال المدنية', 'Construction', 'البناء والتشييد'),
      ('GGCC.CA', 'Giza General Contracting', 'الجيزة العامة للمقاولات', 'Construction', 'البناء والتشييد'),
      ('UEGC.CA', 'El Saeed Contracting', 'الصعيد العامة للمقاولات', 'Construction', 'البناء والتشييد'),
      -- Energy
      ('AMOC.CA', 'Alexandria Mineral Oils', 'الإسكندرية للزيوت المعدنية', 'Energy', 'الطاقة'),
      ('TAQA.CA', 'TAQA Arabia', 'طاقة عربية', 'Energy', 'الطاقة'),
      ('MOIL.CA', 'Maridive and Oil Services', 'الخدمات الملاحية والبترولية', 'Energy', 'الطاقة'),
      ('EGAS.CA', 'Egypt Gas Company', 'غاز مصر', 'Energy', 'الطاقة'),
      ('ZEOT.CA', 'Extracted Oils & Derivatives', 'الزيوت المستخلصة ومنتجاتها', 'Energy', 'الطاقة'),
      ('NDRL.CA', 'National Drilling Company', 'الحفر الوطنية', 'Energy', 'الطاقة'),
      -- Healthcare
      ('CLHO.CA', 'Cleopatra Hospitals Group', 'مستشفى كليوباترا', 'Healthcare', 'الرعاية الصحية'),
      ('TALM.CA', 'Taaleem Management Services', 'تعليم لخدمات الإدارة', 'Healthcare', 'الرعاية الصحية'),
      ('DMCR.CA', 'Dice Medical & Scientific', 'دايس الطبية والعلمية', 'Healthcare', 'الرعاية الصحية'),
      ('AMES.CA', 'Alexandria New Medical Center', 'الإسكندرية للخدمات الطبية', 'Healthcare', 'الرعاية الصحية'),
      ('NINH.CA', 'Nozha International Hospital', 'مستشفى النزهة الدولي', 'Healthcare', 'الرعاية الصحية'),
      ('PHGC.CA', 'Premium Healthcare Group', 'بريميم هيلثكير جروب', 'Healthcare', 'الرعاية الصحية'),
      ('SPMD.CA', 'Speed Medical', 'سبيد ميديكال', 'Healthcare', 'الرعاية الصحية'),
      -- Hospitality & Tourism
      ('MHOT.CA', 'Misr Hotels', 'مصر للفنادق', 'Hospitality', 'السياحة والفنادق'),
      ('EGTS.CA', 'Egyptian Resorts Company', 'المصرية للمنتجعات السياحية', 'Hospitality', 'السياحة والفنادق'),
      ('PHTV.CA', 'Pyramisa Hotels & Resorts', 'بيراميزا للفنادق والقرى السياحية', 'Hospitality', 'السياحة والفنادق'),
      ('SPHT.CA', 'El Shams Pyramids Hotels', 'الشمس بيراميدز للمنشآت السياحية', 'Hospitality', 'السياحة والفنادق'),
      ('SDTI.CA', 'Sharm Dreams Tourism', 'شارم دريمز للاستثمار السياحي', 'Hospitality', 'السياحة والفنادق'),
      ('MENA.CA', 'Mena Tourism & Real Estate', 'مينا للاستثمار السياحي والعقاري', 'Hospitality', 'السياحة والفنادق'),
      ('RTVC.CA', 'Remco Tourism Villages', 'رمكو لإنشاء القرى السياحية', 'Hospitality', 'السياحة والفنادق'),
      ('ROTO.CA', 'Rowad Tourism', 'رواد السياحة', 'Hospitality', 'السياحة والفنادق'),
      ('MMAT.CA', 'Marsa Alam Tourism', 'مرسى علم للتنمية السياحية', 'Hospitality', 'السياحة والفنادق'),
      ('TRTO.CA', 'Trans Oceans Tours', 'عبر المحيطات للسياحة', 'Hospitality', 'السياحة والفنادق'),
      -- Investment Holdings
      ('OIH.CA', 'Orascom Investment Holding', 'أوراسكوم للاستثمار القابضة', 'Investment', 'الاستثمار'),
      ('AMIA.CA', 'Arab Moltaka Investments', 'الملتقى العربي للاستثمارات', 'Investment', 'الاستثمار'),
      ('NAHO.CA', 'Naeem Holding', 'النعيم القابضة للاستثمارات', 'Investment', 'الاستثمار'),
      ('AIHC.CA', 'Arabia Investments Holding', 'ارابيا انفستمنتس هولدنج', 'Investment', 'الاستثمار'),
      ('KWIN.CA', 'El Kahera El Watania Investment', 'القاهرة الوطنية للاستثمار', 'Investment', 'الاستثمار'),
      ('ICID.CA', 'International Co. for Investment', 'العالمية للاستثمار والتنمية', 'Investment', 'الاستثمار'),
      ('AFDI.CA', 'Al Ahly for Development', 'الأهلي للتنمية والاستثمار', 'Investment', 'الاستثمار'),
      ('SEIG.CA', 'Saudi Egyptian Investment', 'السعودية المصرية للاستثمار', 'Investment', 'الاستثمار'),
      ('AMER.CA', 'Amer Group Holding', 'مجموعة عامر القابضة', 'Investment', 'الاستثمار'),
      -- Agriculture
      ('IFAP.CA', 'International Agricultural Products', 'الدولية للمحاصيل الزراعية', 'Agriculture', 'الزراعة'),
      ('GGRN.CA', 'Go Green Agricultural Investment', 'جو جرين للاستثمار الزراعي', 'Agriculture', 'الزراعة'),
      ('WKOL.CA', 'Wadi Kom Ombo Land Reclamation', 'وادي كوم أمبو لاستصلاح الأراضي', 'Agriculture', 'الزراعة'),
      ('KRDI.CA', 'Al Khair River Agricultural', 'نهر الخير للتنمية والاستثمار الزراعي', 'Agriculture', 'الزراعة'),
      ('AALR.CA', 'General Co. for Land Reclamation', 'العامة لاستصلاح الأراضي', 'Agriculture', 'الزراعة'),
      ('EALR.CA', 'Arab Co. for Land Reclamation', 'العربية لاستصلاح الأراضي', 'Agriculture', 'الزراعة'),
      ('LUTS.CA', 'Lotus Agri Capital', 'لوتس للتنمية والاستثمار الزراعي', 'Agriculture', 'الزراعة'),
      ('ELNA.CA', 'El Nasr Manufacturing Agri Crops', 'النصر لتصنيع الحاصلات الزراعية', 'Agriculture', 'الزراعة'),
      -- Transportation & Logistics
      ('ALCN.CA', 'Alexandria Container & Cargo', 'الإسكندرية لتداول الحاويات والبضائع', 'Transportation', 'النقل واللوجستيات'),
      ('CSAG.CA', 'Canal Shipping Agencies', 'القناة للتوكيلات الملاحية', 'Transportation', 'النقل واللوجستيات'),
      ('ETRS.CA', 'Egyptian Transport Services', 'المصرية لخدمات النقل', 'Transportation', 'النقل واللوجستيات'),
      ('POCO.CA', 'Port Said Container Handling', 'بورسعيد لتداول الحاويات', 'Transportation', 'النقل واللوجستيات'),
      ('DCCC.CA', 'Damietta Container Handling', 'دمياط لتداول الحاويات', 'Transportation', 'النقل واللوجستيات'),
      -- Insurance
      ('MOIN.CA', 'Mohandes Insurance', 'المهندس للتأمين', 'Insurance', 'التأمين'),
      ('DEIN.CA', 'Delta Insurance', 'الدلتا للتأمين', 'Insurance', 'التأمين'),
      -- Education
      ('CAED.CA', 'Cairo Educational Services', 'القاهرة للخدمات التعليمية', 'Education', 'التعليم'),
      ('MOED.CA', 'Egyptian Modern Education Systems', 'المصرية لنظم التعليم الحديثة', 'Education', 'التعليم'),
      -- Consumer Goods & Textiles
      ('SPIN.CA', 'Alexandria Spinning & Weaving', 'الإسكندرية للغزل والنسيج', 'Consumer Goods', 'السلع الاستهلاكية'),
      ('DSCW.CA', 'Dice Sport & Casual Wear', 'دايس للملابس الجاهزة', 'Consumer Goods', 'السلع الاستهلاكية'),
      ('KABO.CA', 'El Nasr Clothing & Textiles', 'النصر للملابس والمنسوجات', 'Consumer Goods', 'السلع الاستهلاكية'),
      ('LCSW.CA', 'Lecico Egypt', 'ليسيكو مصر', 'Consumer Goods', 'السلع الاستهلاكية'),
      ('ECAP.CA', 'Al Ezz Ceramics & Porcelain', 'العز للسيراميك والبورسلين', 'Consumer Goods', 'السلع الاستهلاكية'),
      ('CERA.CA', 'Arab Ceramic (Ceramica)', 'العربية للخزف سيراميكا', 'Consumer Goods', 'السلع الاستهلاكية'),
      ('MEGM.CA', 'Middle East Glass Manufacturing', 'الشرق الأوسط لصناعة الزجاج', 'Consumer Goods', 'السلع الاستهلاكية'),
      ('RAKT.CA', 'General Co. for Paper (Rakta)', 'العامة لصناعة الورق (راكتا)', 'Consumer Goods', 'السلع الاستهلاكية'),
      ('UNIP.CA', 'Universal Paper & Packaging', 'يونيفرسال لصناعة مواد التعبئة والتغليف', 'Consumer Goods', 'السلع الاستهلاكية'),
      ('RUBX.CA', 'Rubex International', 'روبكس العالمية لتصنيع البلاستيك', 'Consumer Goods', 'السلع الاستهلاكية'),
      ('DTPP.CA', 'Delta Printing & Packaging', 'دلتا للطباعة والتغليف', 'Consumer Goods', 'السلع الاستهلاكية'),
      ('EPPK.CA', 'El Ahram Printing & Packaging', 'الأهرام للطباعة والتغليف', 'Consumer Goods', 'السلع الاستهلاكية'),
      ('COSG.CA', 'Cairo Oil & Soap', 'القاهرة للزيوت والصابون', 'Consumer Goods', 'السلع الاستهلاكية'),
      ('MOSC.CA', 'Misr Oils & Soap', 'مصر للزيوت والصابون', 'Consumer Goods', 'السلع الاستهلاكية'),
      ('MFSC.CA', 'Egypt Free Shops', 'مصر للأسواق الحرة', 'Consumer Goods', 'السلع الاستهلاكية')
      ON CONFLICT (symbol) DO UPDATE SET
        name_en = EXCLUDED.name_en,
        name_ar = EXCLUDED.name_ar,
        sector_en = EXCLUDED.sector_en,
        sector_ar = EXCLUDED.sector_ar,
        is_active = TRUE,
        updated_at = CURRENT_TIMESTAMP
    `);
    console.log('✅ EGX stocks seeded');

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
