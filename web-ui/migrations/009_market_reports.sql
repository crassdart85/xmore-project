-- =============================================
-- Migration 009: Market Intelligence Reports
-- =============================================

CREATE TABLE IF NOT EXISTS market_reports (
    id SERIAL PRIMARY KEY,
    filename TEXT NOT NULL,
    upload_date TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    extracted_text TEXT,
    language VARCHAR(2) NOT NULL DEFAULT 'EN',
    summary TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_market_reports_language CHECK (language IN ('EN', 'AR'))
);

CREATE INDEX IF NOT EXISTS idx_market_reports_upload_date
    ON market_reports(upload_date DESC);
