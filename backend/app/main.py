from fastapi import FastAPI, Query
from pydantic import BaseModel
from datetime import datetime, timezone
import logging
import asyncio
import time
from app.adapters.solscope import fetch_wallet_leaderboard, GMGN_PROXY_URL
from app.adapters.soulwinners import fetch_qualified_wallets, initialize_postgres_schema, DB_PATH, DATABASE_URL
from app.adapters.atlas import fetch_wallet_flows, HELIUS_API_KEY
from app.analysis import build_flow_signals
from app.strategy import STRATEGY, session_status, evaluate_entry

logger = logging.getLogger("grok-whale-api")
app = FastAPI(title="DioMasteR2D Grok Whale API", version="0.6.0")

# Share one Helius scan between dashboard endpoints; avoids duplicate requests
# when the Android client refreshes flows and signals together.
_FLOW_CACHE_TTL_SECONDS = 45
_flow_cache = {}
_flow_cache_lock = asyncio.Lock()

async def get_cached_wallet_flows(limit: int = 10):
    now = time.monotonic()
    async with _flow_cache_lock:
        cached = _flow_cache.get(limit)
        if cached and now - cached["stored_at"] < _FLOW_CACHE_TTL_SECONDS:
            return cached["payload"]
        payload = await fetch_wallet_flows(limit)
        _flow_cache[limit] = {"stored_at": time.monotonic(), "payload": payload}
        return payload

class PaperStatus(BaseModel):
    mode: str = "paper"
    live_trading_enabled: bool = False
    note: str = "Simulation only. No transaction signing or order execution."

@app.on_event("startup")
def initialize_sources():
    if DATABASE_URL:
        result = initialize_postgres_schema()
        if result.get("status") != "ok":
            logger.warning("SoulWinners schema initialization did not complete: %s", result.get("status"))
        else:
            logger.info("SoulWinners PostgreSQL schema is ready.")
    else:
        logger.info("SoulWinners PostgreSQL is not configured; skipping schema initialization.")

@app.get("/")
def root():
    return {
        "service": "DioMasteR2D Grok Whale API",
        "status": "online",
        "health": "/health",
        "api_status": "/api/v1/status",
        "docs": "/docs",
        "mode": "paper",
        "live_trading_enabled": False,
    }

@app.get("/health")
def health():
    return {"status": "ok", "service": "grok-whale-api", "time": datetime.now(timezone.utc).isoformat()}

@app.get("/api/v1/status")
def status():
    db = fetch_qualified_wallets(1) if DATABASE_URL else {"status": "not_configured"}
    return {
        "mode": "paper",
        "live_trading_enabled": False,
        "sources": {
            "solscope_proxy": "configured" if GMGN_PROXY_URL else "missing_config",
            "soulwinners_database": db.get("status", "unknown"),
            "atlas_helius": "configured_auto_discovery" if HELIUS_API_KEY and GMGN_PROXY_URL else ("missing_helius_key" if not HELIUS_API_KEY else "missing_solscope_proxy"),
            "flow_analytics": "deterministic_v1",
            "atlas_agent": "not_deployed",
        },
        "note": "Whale wallets are discovered automatically. Helius provides raw activity; flow analytics are deterministic heuristics, not an LLM agent.",
    }

@app.get("/api/v1/whales")
async def whales(period: str = Query(default="7d", pattern="^(1d|7d|30d)$"), limit: int = Query(default=100, ge=1, le=500)):
    import asyncio
    solscope, soulwinners = await asyncio.gather(
        fetch_wallet_leaderboard(period),
        asyncio.to_thread(fetch_qualified_wallets, limit),
    )
    return {"period": period, "sources": {"solscope": solscope, "soulwinners": soulwinners}}


def _soulwinners_top10(rows):
    """Apply the user's approved gates to upstream SoulWinners output.
    Preserve its priority_score ranking; do not invent a BES score.
    """
    eligible = []
    rejected = {"win_rate": 0, "trades": 0, "roi": 0, "archetype": 0, "excluded_label": 0}
    archetypes = ("core alpha", "moonshot", "sniper")
    excluded = ("cex", "market maker", "bridge", "developer", "dev wallet")
    for row in rows:
        win_rate = row.get("profit_token_ratio")
        trades = row.get("total_trades")
        roi = row.get("roi_pct")
        cluster = str(row.get("cluster_name") or row.get("cluster_label") or "").lower()
        source = str(row.get("source") or "").lower()
        if not isinstance(win_rate, (int, float)) or win_rate < 0.60:
            rejected["win_rate"] += 1
            continue
        if not isinstance(trades, int) or trades < 15:
            rejected["trades"] += 1
            continue
        if not isinstance(roi, (int, float)) or roi < 50:
            rejected["roi"] += 1
            continue
        if not any(label in cluster for label in archetypes):
            rejected["archetype"] += 1
            continue
        if any(label in cluster or label in source for label in excluded):
            rejected["excluded_label"] += 1
            continue
        eligible.append(row)
    eligible.sort(key=lambda row: float(row.get("priority_score") or 0), reverse=True)
    return eligible[:10], {
        "candidates_received": len(rows),
        "eligible_before_top10": len(eligible),
        "returned": min(10, len(eligible)),
        "rejected": rejected,
        "ranking_metric": "SoulWinners priority_score (upstream formula)",
        "note": "The upstream SoulWinners code exposes priority_score, not a field named BES. No replacement score is calculated here.",
    }

@app.get("/api/v1/whales/top")
def qualified_top_whales():
    result = fetch_qualified_wallets(500)
    if result.get("status") != "ok":
        return {
            "status": result.get("status", "unknown"),
            "items": [],
            "qualification": {"returned": 0},
            "message": result.get("message", "SoulWinners data is not available."),
        }
    items, qualification = _soulwinners_top10(result.get("items", []))
    return {
        "status": "ok",
        "source": "SoulWinners",
        "items": items,
        "qualification": qualification,
        "message": "Only source rows meeting the available ROI, win-rate, trade-count and archetype gates are returned. Missing/unsupported exclusion labels cannot be independently verified.",
    }

@app.get("/api/v1/atlas/flows")
async def atlas_flows(limit: int = Query(default=10, ge=1, le=25)):
    return await get_cached_wallet_flows(limit)

@app.get("/api/v1/signals")
async def signals(limit: int = Query(default=25, ge=1, le=100)):
    flows = await get_cached_wallet_flows(10)
    return build_flow_signals(flows, max_items=limit)

@app.get("/api/v1/paper-portfolio")
def paper_portfolio():
    return {"mode": "paper", "quote_currency": "USD", "cash": 0.0,
            "open_positions": [], "realized_pnl": 0.0, "unrealized_pnl": 0.0,
            "live_trading_enabled": False}

@app.get("/api/v1/strategy")
def strategy_config():
    return {
        "strategy": STRATEGY,
        "session": session_status(),
        "live_trading_enabled": False,
    }

@app.post("/api/v1/strategy/evaluate")
def strategy_evaluate(payload: dict):
    # Missing evidence fails closed. This endpoint evaluates eligibility only;
    # it does not create a paper or live order.
    return evaluate_entry(payload)
