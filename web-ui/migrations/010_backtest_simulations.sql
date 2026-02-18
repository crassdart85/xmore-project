-- Time Machine: backtest simulation cache
CREATE TABLE IF NOT EXISTS backtest_simulations (
    id SERIAL PRIMARY KEY,
    input_amount DECIMAL(12,2) NOT NULL,
    start_date DATE NOT NULL,
    end_date DATE NOT NULL DEFAULT CURRENT_DATE,
    duration_days INTEGER NOT NULL,
    final_value DECIMAL(12,2) NOT NULL,
    total_return_pct DECIMAL(8,4) NOT NULL,
    annualized_return_pct DECIMAL(8,4),
    egx30_return_pct DECIMAL(8,4),
    alpha_pct DECIMAL(8,4),
    max_drawdown_pct DECIMAL(8,4),
    sharpe_ratio DECIMAL(6,4),
    win_rate_pct DECIMAL(5,2),
    total_trades INTEGER NOT NULL,
    simulation_data TEXT NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(input_amount, start_date)
);

CREATE INDEX IF NOT EXISTS idx_backtest_created ON backtest_simulations(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_backtest_lookup ON backtest_simulations(input_amount, start_date);
