-- =============================================
-- Migration 008: Model Portfolios Engine (Phase 1)
-- =============================================

CREATE TABLE IF NOT EXISTS model_portfolios (
    id SERIAL PRIMARY KEY,
    portfolio_type VARCHAR(20) NOT NULL,
    generated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    total_stocks INTEGER NOT NULL,
    cash_pct DECIMAL(5,2) NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    valid_until TIMESTAMPTZ NOT NULL,
    generation_metadata JSONB,
    CONSTRAINT chk_cash_pct CHECK (cash_pct BETWEEN 0 AND 100)
);

CREATE INDEX IF NOT EXISTS idx_model_portfolios_type_active
    ON model_portfolios(portfolio_type, is_active);
CREATE INDEX IF NOT EXISTS idx_model_portfolios_generated_at
    ON model_portfolios(generated_at);

CREATE TABLE IF NOT EXISTS portfolio_allocations (
    id SERIAL PRIMARY KEY,
    portfolio_id INTEGER NOT NULL REFERENCES model_portfolios(id),
    stock_symbol VARCHAR(10) NOT NULL,
    stock_name_ar VARCHAR(100) NOT NULL,
    allocation_pct DECIMAL(5,2) NOT NULL,
    signal_type VARCHAR(20) NOT NULL,
    consensus_score DECIMAL(3,2) NOT NULL,
    entry_price DECIMAL(10,2) NOT NULL,
    stop_loss_price DECIMAL(10,2) NOT NULL,
    target_price DECIMAL(10,2) NOT NULL,
    rationale TEXT,
    CONSTRAINT chk_allocation_pct CHECK (allocation_pct BETWEEN 0 AND 100),
    CONSTRAINT chk_consensus_score CHECK (consensus_score BETWEEN 0 AND 1)
);

CREATE INDEX IF NOT EXISTS idx_portfolio_allocations_portfolio_id
    ON portfolio_allocations(portfolio_id);
CREATE INDEX IF NOT EXISTS idx_portfolio_allocations_symbol
    ON portfolio_allocations(stock_symbol);

CREATE TABLE IF NOT EXISTS portfolio_performance (
    id SERIAL PRIMARY KEY,
    portfolio_id INTEGER NOT NULL REFERENCES model_portfolios(id),
    snapshot_date DATE NOT NULL,
    total_return_pct DECIMAL(8,4),
    daily_return_pct DECIMAL(8,4),
    egx30_return_pct DECIMAL(8,4),
    alpha_pct DECIMAL(8,4),
    sharpe_ratio DECIMAL(6,4),
    max_drawdown_pct DECIMAL(8,4),
    win_rate_pct DECIMAL(5,2),
    UNIQUE(portfolio_id, snapshot_date)
);

CREATE INDEX IF NOT EXISTS idx_portfolio_performance_portfolio_date
    ON portfolio_performance(portfolio_id, snapshot_date);

-- Prevent updates/deletes once a row is no longer active.
CREATE OR REPLACE FUNCTION prevent_inactive_portfolio_mutation()
RETURNS TRIGGER AS $$
BEGIN
    IF OLD.is_active = FALSE THEN
        RAISE EXCEPTION 'Cannot mutate inactive model_portfolios rows';
    END IF;
    RETURN COALESCE(NEW, OLD);
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_model_portfolios_no_update_inactive ON model_portfolios;
CREATE TRIGGER trg_model_portfolios_no_update_inactive
    BEFORE UPDATE ON model_portfolios
    FOR EACH ROW
    EXECUTE FUNCTION prevent_inactive_portfolio_mutation();

DROP TRIGGER IF EXISTS trg_model_portfolios_no_delete_inactive ON model_portfolios;
CREATE TRIGGER trg_model_portfolios_no_delete_inactive
    BEFORE DELETE ON model_portfolios
    FOR EACH ROW
    EXECUTE FUNCTION prevent_inactive_portfolio_mutation();

-- Auto-deactivate previous active portfolio of same type before inserting a new active row.
CREATE OR REPLACE FUNCTION deactivate_previous_portfolio()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.is_active = TRUE THEN
        UPDATE model_portfolios
        SET is_active = FALSE
        WHERE portfolio_type = NEW.portfolio_type
          AND is_active = TRUE;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_model_portfolios_single_active ON model_portfolios;
CREATE TRIGGER trg_model_portfolios_single_active
    BEFORE INSERT ON model_portfolios
    FOR EACH ROW
    EXECUTE FUNCTION deactivate_previous_portfolio();
