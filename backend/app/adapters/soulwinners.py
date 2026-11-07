"""Read-only SoulWinners adapter. PostgreSQL preferred; legacy SQLite supported."""
import os
import sqlite3
from pathlib import Path

DB_PATH = os.getenv("SOULWINNERS_DB_PATH", "")
DATABASE_URL = os.getenv("SOULWINNERS_DATABASE_URL", "")

COLUMNS = """wallet_address, source, roi_pct, median_roi_pct,
    profit_token_ratio, trade_frequency, roi_per_trade, x10_ratio, x20_ratio,
    x50_ratio, x100_ratio, cluster, cluster_label, cluster_name, roi_final,
    priority_score, tier, strategy_bucket, current_balance_sol, total_trades,
    win_rate, average_buy_size_sol, bes_score, qualified_at, last_alert_at"""
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
        average_buy_size_sol DOUBLE PRECISION,
        bes_score DOUBLE PRECISION,
        qualified_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        last_alert_at TIMESTAMP
    );
    ALTER TABLE qualified_wallets ADD COLUMN IF NOT EXISTS average_buy_size_sol DOUBLE PRECISION;
    ALTER TABLE qualified_wallets ADD COLUMN IF NOT EXISTS bes_score DOUBLE PRECISION;
    CREATE INDEX IF NOT EXISTS idx_qualified_priority ON qualified_wallets(priority_score DESC);
    CREATE INDEX IF NOT EXISTS idx_qualified_bes ON qualified_wallets(bes_score DESC);
    CREATE INDEX IF NOT EXISTS idx_qualified_tier ON qualified_wallets(tier);
    """
    try:
        import psycopg
        with psycopg.connect(DATABASE_URL, connect_timeout=8) as conn:
            with conn.cursor() as cur:
                cur.execute(ddl)
        return {"status": "ok"}
    except Exception as exc:
        # Never expose database URLs, passwords, or provider connection details.
        import logging
        logging.getLogger("grok-whale-api").warning(
            "SoulWinners schema initialization failed (%s)", type(exc).__name__
        )
        return {"status": "unavailable", "error_type": type(exc).__name__}

def fetch_qualified_wallets(limit: int = 100) -> dict:
    count = max(1, min(limit, 500))
    if DATABASE_URL:
        try:
            import psycopg
            with psycopg.connect(DATABASE_URL, connect_timeout=5) as conn:
                with conn.cursor(row_factory=psycopg.rows.dict_row) as cur:
                    cur.execute("SET TRANSACTION READ ONLY")
                    # Derive average buy size from real upstream performance
                    # data when that table exists; never infer BES from priority_score.
                    cur.execute("SELECT to_regclass('public.wallet_performance')")
                    has_performance = next(iter(cur.fetchone().values())) is not None
                    if has_performance:
                        cur.execute("SELECT column_name FROM information_schema.columns WHERE table_schema='public' AND table_name='wallet_performance'")
                        performance_columns = {r["column_name"] for r in cur.fetchall()}
                        has_performance = {"wallet_address", "buy_transactions", "total_sol_spent"}.issubset(performance_columns)
                    if has_performance:
                        cur.execute(
                            """SELECT q.wallet_address, q.source, q.roi_pct, q.median_roi_pct,
                                      q.profit_token_ratio, q.trade_frequency, q.roi_per_trade,
                                      q.x10_ratio, q.x20_ratio, q.x50_ratio, q.x100_ratio,
                                      q.cluster, q.cluster_label, q.cluster_name, q.roi_final,
                                      q.priority_score, q.tier, q.strategy_bucket,
                                      q.current_balance_sol, q.total_trades, q.win_rate,
                                      CASE WHEN p.buy_transactions > 0
                                           THEN p.total_sol_spent / p.buy_transactions
                                           ELSE q.average_buy_size_sol END AS average_buy_size_sol,
                                      q.bes_score, q.qualified_at, q.last_alert_at
                               FROM qualified_wallets q
                               LEFT JOIN wallet_performance p ON p.wallet_address=q.wallet_address
                               LIMIT %s""",
                            (count,))
                    else:
                        cur.execute("SELECT " + COLUMNS + " FROM qualified_wallets LIMIT %s", (count,))
                    rows = cur.fetchall()
            items = []
            for row in rows:
                item = dict(row)
                avg_buy = item.get("average_buy_size_sol")
                roi_trade = item.get("roi_per_trade")
                # Win rate must be the measured win_rate field. profit_token_ratio
                # is a distinct upstream metric and must never feed BES.
                win_rate = item.get("win_rate")
                frequency = item.get("trade_frequency")
                if all(isinstance(v, (int, float)) for v in (avg_buy, roi_trade, win_rate, frequency)) and avg_buy > 0:
                    item["bes_score"] = (roi_trade * win_rate * frequency) / avg_buy
                else:
                    item["bes_score"] = None
                items.append(item)
            items.sort(key=lambda x: x["bes_score"] if x["bes_score"] is not None else float("-inf"), reverse=True)
            return {"status": "ok", "items": items, "storage": "postgres",
                    "bes_average_buy_source": "wallet_performance.total_sol_spent / buy_transactions" if has_performance else "qualified_wallets.average_buy_size_sol"}
        except psycopg.errors.UndefinedTable:
            return {"status": "schema_pending", "items": [], "storage": "postgres",
                    "message": "SoulWinners schema has not been initialized yet."}
        except Exception as exc:
            import logging
            logging.getLogger("grok-whale-api").warning(
                "SoulWinners PostgreSQL query failed (%s)", type(exc).__name__
            )
            return {"status": "unavailable", "items": [], "storage": "postgres",
                    "error_type": type(exc).__name__,
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
            items = []
            for row in rows:
                item = dict(row)
                avg_buy = item.get("average_buy_size_sol")
                roi_trade = item.get("roi_per_trade")
                # Win rate must be the measured win_rate field. profit_token_ratio
                # is a distinct upstream metric and must never feed BES.
                win_rate = item.get("win_rate")
                frequency = item.get("trade_frequency")
                if all(isinstance(v, (int, float)) for v in (avg_buy, roi_trade, win_rate, frequency)) and avg_buy > 0:
                    item["bes_score"] = (roi_trade * win_rate * frequency) / avg_buy
                else:
                    item["bes_score"] = None
                items.append(item)
            items.sort(key=lambda x: x["bes_score"] if x["bes_score"] is not None else float("-inf"), reverse=True)
            return {"status": "ok", "items": items, "storage": "sqlite"}
        finally:
            conn.close()
    except sqlite3.Error:
        return {"status": "schema_error", "items": [], "message": "SoulWinners SQLite schema is not ready."}
