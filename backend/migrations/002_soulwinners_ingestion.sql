-- Raw 30-day Helius history. Does not claim realized PnL or wallet qualification.
CREATE TABLE IF NOT EXISTS soulwinners_ingestion_runs (
    id BIGSERIAL PRIMARY KEY,
    window_start TIMESTAMPTZ NOT NULL,
    window_end TIMESTAMPTZ NOT NULL,
    source TEXT NOT NULL,
    wallets_requested INTEGER NOT NULL,
    wallets_completed INTEGER NOT NULL,
    wallets_failed INTEGER NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('complete','partial','failed')),
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CHECK (window_end > window_start)
);
CREATE TABLE IF NOT EXISTS soulwinners_wallet_transactions (
    wallet_address TEXT NOT NULL,
    signature TEXT NOT NULL,
    block_time TIMESTAMPTZ NOT NULL,
    tx_type TEXT NOT NULL,
    fee_lamports BIGINT NOT NULL DEFAULT 0,
    raw_json JSONB NOT NULL,
    payload_hash TEXT NOT NULL,
    ingestion_run_id BIGINT NOT NULL REFERENCES soulwinners_ingestion_runs(id),
    ingested_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (wallet_address, signature)
);
CREATE INDEX IF NOT EXISTS idx_sw_tx_block_time ON soulwinners_wallet_transactions(block_time);
CREATE INDEX IF NOT EXISTS idx_sw_tx_wallet_time ON soulwinners_wallet_transactions(wallet_address, block_time DESC);
