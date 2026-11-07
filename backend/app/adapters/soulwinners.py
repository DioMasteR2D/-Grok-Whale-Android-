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

def fetch_qualified_wallets(limit: int = 100) -> dict:
    count = max(1, min(limit, 500))
    if DATABASE_URL:
        try:
            import psycopg
            # A read-only transaction prevents accidental mutations.
            with psycopg.connect(DATABASE_URL, connect_timeout=5) as conn:
                with conn.cursor(row_factory=psycopg.rows.dict_row) as cur:
                    cur.execute("SET TRANSACTION READ ONLY")
                    cur.execute("SELECT " + COLUMNS + " FROM qualified_wallets" + ORDER + "%s", (count,))
                    rows = cur.fetchall()
            return {"status": "ok", "items": rows, "storage": "postgres"}
        except psycopg.errors.UndefinedTable:
            return {"status": "schema_pending", "items": [], "storage": "postgres",
                    "message": "SoulWinners schema has not been initialized yet."}
        except Exception as exc:
            # Avoid returning connection strings or credentials in public API errors.
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
