"""Read-only SoulWinners adapter. PostgreSQL preferred; legacy SQLite supported."""
import os
import sqlite3
from pathlib import Path

DB_PATH = os.getenv("SOULWINNERS_DB_PATH", "")
DATABASE_URL = os.getenv("SOULWINNERS_DATABASE_URL", "")

COLUMNS = """wallet_address, source, roi_pct, median_roi_pct,
    profit_token_ratio, trade_frequency, roi_per_trade, tier,
    strategy_bucket, current_balance_sol, total_trades, win_rate,
    qualified_at, last_alert_at"""
ORDER = " ORDER BY priority_score DESC LIMIT "

def initialize_postgres_schema() -> dict:
    """Create only the minimal read schema, idempotently; never seed fabricated data."""
    if not DATABASE_URL:
        return {"status": "not_configured"}
    ddl = """
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
        qualified_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        last_alert_at TIMESTAMP
    );
    CREATE INDEX IF NOT EXISTS idx_qualified_priority ON qualified_wallets(priority_score DESC);
    CREATE INDEX IF NOT EXISTS idx_qualified_tier ON qualified_wallets(tier);
    """
    try:
        import psycopg
        with psycopg.connect(DATABASE_URL, connect_timeout=8) as conn:
            with conn.cursor() as cur:
                cur.execute(ddl)
        return {"status": "ok"}
    except Exception:
        # Never expose database URLs, passwords, or provider connection details.
        return {"status": "unavailable"}

def fetch_qualified_wallets(limit: int = 100) -> dict:
    count = max(1, min(limit, 500))
    if DATABASE_URL:
        try:
            import psycopg
            with psycopg.connect(DATABASE_URL, connect_timeout=5) as conn:
                with conn.cursor(row_factory=psycopg.rows.dict_row) as cur:
                    cur.execute("SET TRANSACTION READ ONLY")
                    cur.execute("SELECT " + COLUMNS + " FROM qualified_wallets" + ORDER + "%s", (count,))
                    rows = cur.fetchall()
            return {"status": "ok", "items": rows, "storage": "postgres"}
        except psycopg.errors.UndefinedTable:
            return {"status": "schema_pending", "items": [], "storage": "postgres",
                    "message": "SoulWinners schema has not been initialized yet."}
        except Exception:
            return {"status": "unavailable", "items": [], "storage": "postgres",
                    "message": "SoulWinners PostgreSQL query failed; inspect private server logs."}
    if not DB_PATH:
        return {"status": "not_configured", "items": [],
                "message": "Set SOULWINNERS_DATABASE_URL or SOULWINNERS_DB_PATH."}
    path = Path(DB_PATH)
    if not path.is_file():
        return {"status": "unavailable", "items": [], "message": "SQLite file not found."}
    try:
        conn = sqlite3.connect(f"file:{path.resolve()}?mode=ro", uri=True, timeout=5)
        conn.row_factory = sqlite3.Row
        try:
            rows = conn.execute("SELECT " + COLUMNS + " FROM qualified_wallets" + ORDER + "?", (count,)).fetchall()
            return {"status": "ok", "items": [dict(row) for row in rows], "storage": "sqlite"}
        finally:
            conn.close()
    except sqlite3.Error:
        return {"status": "schema_error", "items": [], "message": "SoulWinners SQLite schema is not ready."}
