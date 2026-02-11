-- =============================================
-- Migration 007: Performance Validation & Benchmarking
-- Tasks 1, 2, 4, 6
-- =============================================

-- ─── TASK 1A: IMMUTABILITY TRIGGERS ──────────────────────────

-- Prevent mutation of core consensus prediction fields
CREATE OR REPLACE FUNCTION prevent_consensus_mutation()
RETURNS TRIGGER AS $$
BEGIN
    IF OLD.final_signal IS NOT NULL AND NEW.final_signal != OLD.final_signal THEN
        RAISE EXCEPTION 'Cannot modify final_signal after creation (immutable field)';
    END IF;
    IF OLD.confidence IS NOT NULL AND NEW.confidence != OLD.confidence THEN
        RAISE EXCEPTION 'Cannot modify confidence after creation (immutable field)';
    END IF;
    IF OLD.conviction IS NOT NULL AND NEW.conviction != OLD.conviction THEN
        RAISE EXCEPTION 'Cannot modify conviction after creation (immutable field)';
    END IF;
    IF OLD.bull_score IS NOT NULL AND NEW.bull_score != OLD.bull_score THEN
        RAISE EXCEPTION 'Cannot modify bull_score after creation (immutable field)';
    END IF;
    IF OLD.bear_score IS NOT NULL AND NEW.bear_score != OLD.bear_score THEN
        RAISE EXCEPTION 'Cannot modify bear_score after creation (immutable field)';
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_consensus_immutable ON consensus_results;
CREATE TRIGGER trg_consensus_immutable
    BEFORE UPDATE ON consensus_results
    FOR EACH ROW
    EXECUTE FUNCTION prevent_consensus_mutation();


-- Prevent mutation of core trade_recommendation fields
CREATE OR REPLACE FUNCTION prevent_recommendation_mutation()
RETURNS TRIGGER AS $$
BEGIN
    IF OLD.action IS NOT NULL AND NEW.action != OLD.action THEN
        RAISE EXCEPTION 'Cannot modify action after creation (immutable)';
    END IF;
    IF OLD.signal IS NOT NULL AND NEW.signal != OLD.signal THEN
        RAISE EXCEPTION 'Cannot modify signal after creation (immutable)';
    END IF;
    IF OLD.confidence IS NOT NULL AND NEW.confidence != OLD.confidence THEN
        RAISE EXCEPTION 'Cannot modify confidence after creation (immutable)';
    END IF;
    IF OLD.close_price IS NOT NULL AND NEW.close_price != OLD.close_price THEN
        RAISE EXCEPTION 'Cannot modify close_price after creation (immutable)';
    END IF;
    IF OLD.conviction IS NOT NULL AND NEW.conviction != OLD.conviction THEN
        RAISE EXCEPTION 'Cannot modify conviction after creation (immutable)';
    END IF;
    IF OLD.reasons IS NOT NULL AND NEW.reasons != OLD.reasons THEN
        RAISE EXCEPTION 'Cannot modify reasons after creation (immutable)';
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_recommendation_immutable ON trade_recommendations;
CREATE TRIGGER trg_recommendation_immutable
    BEFORE UPDATE ON trade_recommendations
    FOR EACH ROW
    EXECUTE FUNCTION prevent_recommendation_mutation();


-- ─── TASK 1B: AUDIT TRAIL TABLE ─────────────────────────────

CREATE TABLE IF NOT EXISTS prediction_audit_log (
    id SERIAL PRIMARY KEY,
    table_name VARCHAR(50) NOT NULL,
    record_id INTEGER NOT NULL,
    field_changed VARCHAR(50) NOT NULL,
    old_value TEXT,
    new_value TEXT,
    changed_by VARCHAR(50) DEFAULT 'system',
    changed_at TIMESTAMP DEFAULT NOW(),
    pipeline_run_id VARCHAR(50)
);

CREATE INDEX IF NOT EXISTS idx_audit_table_record ON prediction_audit_log(table_name, record_id);
CREATE INDEX IF NOT EXISTS idx_audit_date ON prediction_audit_log(changed_at DESC);

-- Audit trigger for trade_recommendations outcome updates
CREATE OR REPLACE FUNCTION audit_recommendation_changes()
RETURNS TRIGGER AS $$
BEGIN
    IF OLD.actual_next_day_return IS DISTINCT FROM NEW.actual_next_day_return THEN
        INSERT INTO prediction_audit_log (table_name, record_id, field_changed, old_value, new_value)
        VALUES ('trade_recommendations', OLD.id, 'actual_next_day_return',
                OLD.actual_next_day_return::text, NEW.actual_next_day_return::text);
    END IF;
    IF OLD.actual_5day_return IS DISTINCT FROM NEW.actual_5day_return THEN
        INSERT INTO prediction_audit_log (table_name, record_id, field_changed, old_value, new_value)
        VALUES ('trade_recommendations', OLD.id, 'actual_5day_return',
                OLD.actual_5day_return::text, NEW.actual_5day_return::text);
    END IF;
    IF OLD.was_correct IS DISTINCT FROM NEW.was_correct THEN
        INSERT INTO prediction_audit_log (table_name, record_id, field_changed, old_value, new_value)
        VALUES ('trade_recommendations', OLD.id, 'was_correct',
                OLD.was_correct::text, NEW.was_correct::text);
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_audit_recommendations ON trade_recommendations;
CREATE TRIGGER trg_audit_recommendations
    AFTER UPDATE ON trade_recommendations
    FOR EACH ROW
    EXECUTE FUNCTION audit_recommendation_changes();


-- ─── TASK 2: BENCHMARK COLUMNS ──────────────────────────────

ALTER TABLE trade_recommendations
    ADD COLUMN IF NOT EXISTS benchmark_1d_return REAL,
    ADD COLUMN IF NOT EXISTS benchmark_5d_return REAL,
    ADD COLUMN IF NOT EXISTS alpha_1d REAL,
    ADD COLUMN IF NOT EXISTS alpha_5d REAL,
    ADD COLUMN IF NOT EXISTS buyhold_1d_return REAL,
    ADD COLUMN IF NOT EXISTS buyhold_5d_return REAL,
    ADD COLUMN IF NOT EXISTS resolved_at TIMESTAMP,
    ADD COLUMN IF NOT EXISTS model_version VARCHAR(20),
    ADD COLUMN IF NOT EXISTS is_live BOOLEAN DEFAULT TRUE;

ALTER TABLE user_positions
    ADD COLUMN IF NOT EXISTS benchmark_return_pct REAL,
    ADD COLUMN IF NOT EXISTS alpha_pct REAL;

CREATE INDEX IF NOT EXISTS idx_trade_rec_live
    ON trade_recommendations(is_live, recommendation_date DESC);


-- ─── TASK 4: AGENT PERFORMANCE DAILY TABLE ──────────────────

CREATE TABLE IF NOT EXISTS agent_performance_daily (
    id SERIAL PRIMARY KEY,
    snapshot_date DATE NOT NULL,
    agent_name VARCHAR(50) NOT NULL,

    predictions_30d INTEGER DEFAULT 0,
    correct_30d INTEGER DEFAULT 0,
    win_rate_30d REAL,
    avg_confidence_30d REAL,

    predictions_90d INTEGER DEFAULT 0,
    correct_90d INTEGER DEFAULT 0,
    win_rate_90d REAL,

    created_at TIMESTAMP DEFAULT NOW(),

    UNIQUE(snapshot_date, agent_name)
);

CREATE INDEX IF NOT EXISTS idx_agent_perf_date ON agent_performance_daily(snapshot_date DESC);
CREATE INDEX IF NOT EXISTS idx_agent_perf_agent ON agent_performance_daily(agent_name);


-- ─── TASK 6: MATERIALIZED VIEW ──────────────────────────────

CREATE MATERIALIZED VIEW IF NOT EXISTS mv_performance_global AS
SELECT
    COUNT(*) AS total_predictions,
    COUNT(*) FILTER (WHERE was_correct = TRUE) AS wins,
    COUNT(*) FILTER (WHERE was_correct = FALSE) AS losses,
    ROUND((COUNT(*) FILTER (WHERE was_correct = TRUE))::numeric
          / NULLIF(COUNT(*), 0) * 100, 1) AS win_rate,
    ROUND(AVG(actual_next_day_return)::numeric, 3) AS avg_return_1d,
    ROUND(AVG(actual_5day_return)::numeric, 3) AS avg_return_5d,
    ROUND(AVG(alpha_1d)::numeric, 3) AS avg_alpha_1d,
    ROUND(AVG(benchmark_1d_return)::numeric, 3) AS avg_benchmark_1d,
    COUNT(*) FILTER (WHERE alpha_1d > 0) AS beat_benchmark_count,
    MIN(recommendation_date) AS first_prediction,
    MAX(recommendation_date) AS last_prediction,
    COUNT(*) >= 100 AS meets_minimum
FROM trade_recommendations
WHERE was_correct IS NOT NULL
AND is_live = TRUE;

-- Dummy unique index so REFRESH CONCURRENTLY works
CREATE UNIQUE INDEX IF NOT EXISTS idx_mv_perf_global_uniq ON mv_performance_global (total_predictions);

-- Refresh helper function
CREATE OR REPLACE FUNCTION refresh_performance_views()
RETURNS void AS $$
BEGIN
    REFRESH MATERIALIZED VIEW CONCURRENTLY mv_performance_global;
END;
$$ LANGUAGE plpgsql;
