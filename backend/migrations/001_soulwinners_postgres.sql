-- Minimal PostgreSQL schema required by the read-only SoulWinners API.
-- Safe to run repeatedly. Does not import stale CSV snapshots or enable trading.
CREATE TABLE IF NOT EXISTS qualified_wallets (
    wallet_address TEXT PRIMARY KEY,
    source TEXT,
    roi_pct DOUBLE PRECISION,
    median_roi_pct DOUBLE PRECISION,
    profit_token_ratio DOUBLE PRECISION,
    trade_frequency DOUBLE PRECISION,
    roi_per_trade DOUBLE PRECISION,
    x10_ratio DOUBLE PRECISION,
    x20_ratio DOUBLE PRECISION,
    x50_ratio DOUBLE PRECISION,
    x100_ratio DOUBLE PRECISION,
    median_hold_time DOUBLE PRECISION,
    profit_per_hold_second DOUBLE PRECISION,
    cluster INTEGER,
    cluster_label TEXT,
    cluster_name TEXT,
    roi_final DOUBLE PRECISION,
    priority_score DOUBLE PRECISION,
    tier TEXT,
    strategy_bucket TEXT,
    current_balance_sol DOUBLE PRECISION,
    total_trades INTEGER,
    win_rate DOUBLE PRECISION,
    average_buy_size_sol DOUBLE PRECISION,
    bes_score DOUBLE PRECISION,
    qualified_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_alert_at TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_qualified_priority ON qualified_wallets(priority_score DESC);
CREATE INDEX IF NOT EXISTS idx_qualified_tier ON qualified_wallets(tier);

ALTER TABLE qualified_wallets ADD COLUMN IF NOT EXISTS average_buy_size_sol DOUBLE PRECISION;
ALTER TABLE qualified_wallets ADD COLUMN IF NOT EXISTS bes_score DOUBLE PRECISION;
CREATE INDEX IF NOT EXISTS idx_qualified_bes ON qualified_wallets(bes_score DESC);
