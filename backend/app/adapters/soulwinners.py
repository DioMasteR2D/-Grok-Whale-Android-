"""Read-only adapter for SoulWinners' documented SQLite output schema."""
import os
import sqlite3
from pathlib import Path

DB_PATH = os.getenv("SOULWINNERS_DB_PATH", "")

def fetch_qualified_wallets(limit: int = 100) -> dict:
    if not DB_PATH:
        return {"status": "not_configured", "items": [], "message": "Set SOULWINNERS_DB_PATH to the SoulWinners SQLite database file."}
    path = Path(DB_PATH)
    if not path.is_file():
        return {"status": "unavailable", "items": [], "message": "Configured SoulWinners database file was not found."}
    try:
        # URI mode=ro prevents this integration from modifying the upstream DB.
        conn = sqlite3.connect(f"file:{path.resolve()}?mode=ro", uri=True, timeout=5)
        conn.row_factory = sqlite3.Row
        try:
            rows = conn.execute(
                """SELECT wallet_address, source, roi_pct, median_roi_pct,
                          profit_token_ratio, trade_frequency, roi_per_trade,
                          tier, strategy_bucket, current_balance_sol,
                          total_trades, win_rate, qualified_at, last_alert_at
                   FROM qualified_wallets
                   ORDER BY priority_score DESC LIMIT ?""",
                (max(1, min(limit, 500)),),
            ).fetchall()
            return {"status": "ok", "items": [dict(row) for row in rows]}
        finally:
            conn.close()
    except sqlite3.Error as exc:
        return {"status": "schema_error", "items": [], "message": str(exc)}
