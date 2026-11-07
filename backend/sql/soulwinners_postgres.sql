-- SoulWinners PostgreSQL schema. Apply once through a trusted database admin.
-- This creates an empty table; it does not fabricate or import historical wallet data.
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
    qualified_at TEXT,
    last_alert_at TEXT
);
CREATE INDEX IF NOT EXISTS idx_qualified_wallets_priority
    ON qualified_wallets (priority_score DESC);
