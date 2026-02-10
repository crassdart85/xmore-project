-- Migration 005: Create user_watchlist junction table
-- Part of: Xmore Auth & Watchlist Feature

CREATE TABLE IF NOT EXISTS user_watchlist (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    stock_id INTEGER NOT NULL REFERENCES egx30_stocks(id) ON DELETE CASCADE,
    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, stock_id)
);

CREATE INDEX IF NOT EXISTS idx_watchlist_user ON user_watchlist(user_id);
