"""PostgreSQL-backed paper portfolio. Simulation only; never signs or sends."""
import os
from datetime import datetime, timezone

DB = os.getenv("SOULWINNERS_DATABASE_URL", "").strip()
MAX_OPEN_POSITIONS = max(1, min(50, int(os.getenv("MAX_OPEN_POSITIONS", "10"))))
MAX_TRADE_USD = max(0.5, min(2.0, float(os.getenv("PAPER_TRADE_USD", "2"))))
TAKE_PROFIT_PCT = max(1.0, min(50.0, float(os.getenv("PAPER_TAKE_PROFIT_PCT", "10"))))
STOP_LOSS_PCT = max(1.0, min(25.0, float(os.getenv("PAPER_STOP_LOSS_PCT", "5"))))


def _db():
    if not DB:
        raise RuntimeError("persistent_database_not_configured")
    import psycopg
    return psycopg.connect(DB)


def initialize():
    with _db() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS paper_portfolio (
                    id INTEGER PRIMARY KEY,
                    starting_cash DOUBLE PRECISION NOT NULL,
                    cash DOUBLE PRECISION NOT NULL,
                    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
                );
                CREATE TABLE IF NOT EXISTS paper_positions (
                    id BIGSERIAL PRIMARY KEY,
                    mint TEXT NOT NULL,
                    quantity DOUBLE PRECISION NOT NULL,
                    entry_price DOUBLE PRECISION NOT NULL,
                    last_price DOUBLE PRECISION NOT NULL,
                    status TEXT NOT NULL DEFAULT 'open',
                    origin_wallet TEXT,
                    opened_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
                    closed_at TIMESTAMPTZ,
                    realized_pnl DOUBLE PRECISION NOT NULL DEFAULT 0
                );
                CREATE INDEX IF NOT EXISTS idx_paper_open ON paper_positions(status);
                INSERT INTO paper_portfolio(id, starting_cash, cash)
                VALUES(1, 1000, 1000) ON CONFLICT(id) DO NOTHING;
                ALTER TABLE paper_positions ADD COLUMN IF NOT EXISTS origin_wallet TEXT;
            """)


def summary():
    try:
        with _db() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT cash, starting_cash FROM paper_portfolio WHERE id=1")
                row = cur.fetchone()
                if not row:
                    return {"status": "not_initialized", "mode": "paper"}
                cash, start = row
                cur.execute("""
                    SELECT id, mint, quantity, entry_price, last_price, opened_at, origin_wallet
                    FROM paper_positions WHERE status='open' ORDER BY id DESC
                """)
                positions = cur.fetchall()
                cur.execute("SELECT COALESCE(SUM(realized_pnl), 0) FROM paper_positions WHERE status='closed'")
                realized = float(cur.fetchone()[0])
                items = []
                unrealized = 0.0
                for pid, mint, quantity, entry, last, opened, origin in positions:
                    pnl = (last - entry) * quantity
                    unrealized += pnl
                    items.append({
                        "id": pid, "mint": mint, "quantity": quantity,
                        "entry_price": entry, "last_price": last,
                        "market_value": quantity * last, "unrealized_pnl": pnl,
                        "opened_at": opened.isoformat() if opened else None,
                        "origin_wallet": origin,
                        "take_profit_price": entry * (1 + TAKE_PROFIT_PCT / 100),
                        "stop_loss_price": entry * (1 - STOP_LOSS_PCT / 100),
                    })
                return {
                    "status": "ok", "mode": "paper", "quote_currency": "USD",
                    "starting_cash": start, "cash": cash, "open_positions": items,
                    "realized_pnl": realized, "unrealized_pnl": unrealized,
                    "equity": cash + sum(item["market_value"] for item in items),
                    "max_open_positions": MAX_OPEN_POSITIONS,
                    "paper_trade_usd": MAX_TRADE_USD,
                    "take_profit_pct": TAKE_PROFIT_PCT,
                    "stop_loss_pct": STOP_LOSS_PCT,
                    "live_trading_enabled": False,
                }
    except Exception as exc:
        return {
            "status": "not_configured" if str(exc) == "persistent_database_not_configured" else "unavailable",
            "mode": "paper", "open_positions": [],
            "message": "Persistent paper database is not available.",
            "live_trading_enabled": False,
        }


def buy(mint, usd, price, origin_wallet=None):
    if (not isinstance(mint, str) or not 32 <= len(mint) <= 44
            or not isinstance(usd, (int, float)) or isinstance(usd, bool)
            or not isinstance(price, (int, float)) or isinstance(price, bool)
            or not (0 < usd <= MAX_TRADE_USD and 0 < price < 1e15)):
        return {
            "status": "rejected",
            "message": f"Invalid input. Paper trade size cannot exceed ${MAX_TRADE_USD:.2f}.",
        }
    try:
        with _db() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT cash FROM paper_portfolio WHERE id=1 FOR UPDATE")
                row = cur.fetchone()
                if not row:
                    return {"status": "not_initialized"}
                cash = float(row[0])
                cur.execute("SELECT COALESCE(SUM(quantity*last_price), 0) FROM paper_positions WHERE status='open'")
                equity = cash + float(cur.fetchone()[0])
                if usd > cash:
                    return {"status": "rejected", "message": "Insufficient paper cash."}
                if usd > equity * 0.08 + 1e-8:
                    return {"status": "rejected", "message": "Position exceeds approved 8% portfolio cap."}
                cur.execute("SELECT COUNT(*) FROM paper_positions WHERE status='open'")
                if int(cur.fetchone()[0]) >= MAX_OPEN_POSITIONS:
                    return {"status": "rejected", "message": f"Maximum open paper positions reached ({MAX_OPEN_POSITIONS})."}
                cur.execute("SELECT 1 FROM paper_positions WHERE mint=%s AND status='open'", (mint,))
                if cur.fetchone():
                    return {"status": "rejected", "message": "Position already open for this mint."}
                quantity = usd / price
                cur.execute("UPDATE paper_portfolio SET cash=cash-%s WHERE id=1", (usd,))
                cur.execute("""
                    INSERT INTO paper_positions(mint, quantity, entry_price, last_price, origin_wallet)
                    VALUES(%s, %s, %s, %s, %s) RETURNING id
                """, (mint, quantity, price, price, origin_wallet))
                return {
                    "status": "opened", "mode": "paper", "position_id": cur.fetchone()[0],
                    "mint": mint, "quantity": quantity, "invested_usd": usd,
                    "take_profit_pct": TAKE_PROFIT_PCT, "stop_loss_pct": STOP_LOSS_PCT,
                    "origin_wallet": origin_wallet, "live_trading_enabled": False,
                }
    except Exception:
        return {"status": "unavailable", "message": "Persistent paper database is not available.", "live_trading_enabled": False}


def mark_prices(prices):
    if not prices or any(not isinstance(value, (int, float)) or isinstance(value, bool) or value <= 0
                         for value in prices.values()):
        return {"status": "rejected", "message": "Positive USD prices are required."}
    updated = []
    try:
        with _db() as conn:
            with conn.cursor() as cur:
                for mint, price in prices.items():
                    price = float(price)
                    cur.execute("""
                        UPDATE paper_positions SET last_price=%s
                        WHERE mint=%s AND status='open'
                        RETURNING id, quantity, entry_price
                    """, (price, mint))
                    for pid, quantity, entry in cur.fetchall():
                        pnl = (price - entry) * quantity
                        change_pct = ((price / entry) - 1) * 100
                        if change_pct >= TAKE_PROFIT_PCT or change_pct <= -STOP_LOSS_PCT:
                            reason = "take_profit_exit" if change_pct >= TAKE_PROFIT_PCT else "stop_loss_exit"
                            cur.execute("""
                                UPDATE paper_positions SET status='closed', closed_at=%s, realized_pnl=%s
                                WHERE id=%s AND status='open'
                            """, (datetime.now(timezone.utc), pnl, pid))
                            cur.execute("UPDATE paper_portfolio SET cash=cash+%s WHERE id=1", (quantity * price,))
                            updated.append({
                                "id": pid, "mint": mint, "action": reason,
                                "change_pct": change_pct, "realized_pnl": pnl,
                            })
                        else:
                            updated.append({
                                "id": pid, "mint": mint, "action": "marked",
                                "change_pct": change_pct, "unrealized_pnl": pnl,
                            })
        return {
            "status": "ok", "updated": updated,
            "take_profit_pct": TAKE_PROFIT_PCT, "stop_loss_pct": STOP_LOSS_PCT,
            "live_trading_enabled": False,
        }
    except Exception:
        return {"status": "unavailable", "message": "Persistent paper database is not available.", "live_trading_enabled": False}


def close(position_id):
    try:
        with _db() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    UPDATE paper_positions SET status='closed', closed_at=%s,
                    realized_pnl=(last_price-entry_price)*quantity
                    WHERE id=%s AND status='open'
                    RETURNING mint, quantity, last_price, realized_pnl
                """, (datetime.now(timezone.utc), position_id))
                row = cur.fetchone()
                if not row:
                    return {"status": "not_found"}
                mint, quantity, price, pnl = row
                cur.execute("UPDATE paper_portfolio SET cash=cash+%s WHERE id=1", (quantity * price,))
                return {"status": "closed", "mode": "paper", "mint": mint,
                        "realized_pnl": pnl, "live_trading_enabled": False}
    except Exception:
        return {"status": "unavailable", "message": "Persistent paper database is not available.", "live_trading_enabled": False}
