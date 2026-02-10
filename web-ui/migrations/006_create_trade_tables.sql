CREATE TABLE IF NOT EXISTS position_status_enum (status VARCHAR(10) PRIMARY KEY);
INSERT INTO position_status_enum (status) VALUES ('OPEN'), ('CLOSED') ON CONFLICT DO NOTHING;

CREATE TABLE IF NOT EXISTS trade_action_enum (action VARCHAR(10) PRIMARY KEY);
INSERT INTO trade_action_enum (action) VALUES ('BUY'), ('SELL'), ('HOLD'), ('WATCH') ON CONFLICT DO NOTHING;

CREATE TABLE IF NOT EXISTS user_positions (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    symbol VARCHAR(20) NOT NULL,
    status VARCHAR(10) NOT NULL DEFAULT 'OPEN',
    entry_date DATE NOT NULL,
    entry_price REAL,
    exit_date DATE,
    exit_price REAL,
    return_pct REAL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, symbol, status) -- Partial index preferred but this works for basic constraint
);

-- Partial index for only one OPEN position per user per stock
CREATE UNIQUE INDEX IF NOT EXISTS idx_unique_open_position 
    ON user_positions(user_id, symbol) 
    WHERE status = 'OPEN';

CREATE INDEX IF NOT EXISTS idx_positions_user ON user_positions(user_id);
CREATE INDEX IF NOT EXISTS idx_positions_status ON user_positions(status);

CREATE TABLE IF NOT EXISTS trade_recommendations (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    symbol VARCHAR(20) NOT NULL,
    recommendation_date DATE NOT NULL,
    
    action VARCHAR(10) NOT NULL,
    signal VARCHAR(10) NOT NULL,
    confidence INTEGER NOT NULL,
    conviction VARCHAR(10),
    risk_action VARCHAR(15),
    priority REAL,
    
    close_price REAL,
    stop_loss_pct REAL,
    target_pct REAL,
    stop_loss_price REAL,
    target_price REAL,
    risk_reward_ratio REAL,
    
    reasons TEXT,       -- JSON string
    reasons_ar TEXT,    -- JSON string
    
    bull_score INTEGER,
    bear_score INTEGER,
    agents_agreeing INTEGER,
    agents_total INTEGER,
    risk_flags TEXT,    -- JSON string
    
    actual_next_day_return REAL,
    actual_5day_return REAL,
    was_correct BOOLEAN,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE(user_id, symbol, recommendation_date)
);

CREATE INDEX IF NOT EXISTS idx_trade_rec_user_date ON trade_recommendations(user_id, recommendation_date DESC);
CREATE INDEX IF NOT EXISTS idx_trade_rec_date ON trade_recommendations(recommendation_date DESC);
