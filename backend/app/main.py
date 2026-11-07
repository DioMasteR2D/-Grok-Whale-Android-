from fastapi import FastAPI, Query
from pydantic import BaseModel, Field
from pydantic import field_validator
import os
import re
import httpx
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

class JupiterOrderRequest(BaseModel):
    input_mint: str = Field(min_length=32, max_length=44)
    output_mint: str = Field(min_length=32, max_length=44)
    amount: int = Field(gt=0, le=10**15)
    taker: str = Field(min_length=32, max_length=44)
    slippage_bps: int = Field(default=100, ge=10, le=300)

    @field_validator("input_mint", "output_mint", "taker")
    @classmethod
    def validate_base58(cls, value):
        if not re.fullmatch(r"[1-9A-HJ-NP-Za-km-z]{32,44}", value):
            raise ValueError("Must be a valid-looking Solana base58 address")
        return value


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
    """Apply the exact approved gates and rank only by a source-computed BES.

    SoulWinners' public metrics documentation defines BES as
    (ROI per trade * win rate * trade frequency) / average buy size.
    The qualified_wallets output currently lacks average_buy_size and the
    source-computed BES. Never substitute priority_score or invent a value.
    """
    candidates = []
    rejected = {"missing_bes_inputs": 0, "win_rate": 0, "trades": 0,
                "roi": 0, "archetype": 0, "excluded_label": 0}
    archetypes = ("core alpha", "moonshot", "moonshot hunters", "sniper")
    excluded = ("cex", "market maker", "bridge", "developer", "dev wallet")
    for row in rows:
        # Only the measured 30-day win_rate is valid for this gate.
        # profit_token_ratio is a different upstream metric and is not a substitute.
        win_rate = row.get("win_rate")
        try:
            win_rate = float(win_rate)
        except (TypeError, ValueError):
            win_rate = None
        try:
            trades = int(row.get("total_trades"))
        except (TypeError, ValueError):
            trades = 0
        try:
            roi = float(row.get("roi_pct"))
        except (TypeError, ValueError):
            roi = None
        label = str(row.get("cluster_name") or row.get("cluster_label") or row.get("strategy_bucket") or "").lower()
        source = str(row.get("source") or "").lower()
        if win_rate is None or win_rate < 0.60:
            rejected["win_rate"] += 1
            continue
        if trades < 15:
            rejected["trades"] += 1
            continue
        if roi is None or roi < 50:
            rejected["roi"] += 1
            continue
        if not any(name in label for name in archetypes):
            rejected["archetype"] += 1
            continue
        if any(term in label or term in source for term in excluded):
            rejected["excluded_label"] += 1
            continue
        bes = row.get("bes_score")
        if not isinstance(bes, (int, float)):
            rejected["missing_bes_inputs"] += 1
            continue
        candidates.append({**row, "bes_score": float(bes)})
    candidates.sort(key=lambda row: row["bes_score"], reverse=True)
    return candidates[:10], {
        "candidates_received": len(rows),
        "eligible_before_top10": len(candidates),
        "returned": min(10, len(candidates)),
        "rejected": rejected,
        "ranking_metric": "BES",
        "bes_formula": "(ROI per trade × win rate × trade frequency) / average buy size",
        "note": "No BES is inferred from priority_score. Rows without a source-computed BES are excluded.",
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
        "message": "Only rows with a measured win_rate >= 60%, ROI >= 50%, at least 15 trades, a supported archetype, and a source-computed BES are returned. profit_token_ratio is never substituted for win_rate. Missing exclusion labels cannot be independently verified.",
    }

@app.get("/api/v1/atlas/flows")
async def atlas_flows(limit: int = Query(default=10, ge=1, le=25)):
    return await get_cached_wallet_flows(limit)

@app.get("/api/v1/signals")
async def signals(limit: int = Query(default=25, ge=1, le=100)):
    flows = await get_cached_wallet_flows(10)
    return build_flow_signals(flows, max_items=limit)


@app.post("/api/v1/swap/order")
async def jupiter_order_preview(payload: JupiterOrderRequest):
    """Fetch a Jupiter quote/order for review only. Never signs or executes."""
    if payload.input_mint == payload.output_mint:
        return {"status": "rejected", "message": "Input and output tokens must differ."}
    headers = {"Accept": "application/json"}
    api_key = os.getenv("JUPITER_API_KEY", "").strip()
    if api_key:
        headers["x-api-key"] = api_key
    params = {
        "inputMint": payload.input_mint,
        "outputMint": payload.output_mint,
        "amount": str(payload.amount),
        "taker": payload.taker,
        "slippageBps": str(payload.slippage_bps),
    }
    try:
        async with httpx.AsyncClient(timeout=18) as client:
            response = await client.get(
                "https://api.jup.ag/swap/v2/order",
                params=params,
                headers=headers,
            )
        if response.status_code == 429:
            return {"status": "rate_limited", "message": "Jupiter rate limit reached; retry later."}
        response.raise_for_status()
        order = response.json()
    except httpx.HTTPStatusError as exc:
        logger.warning("Jupiter order preview returned HTTP %s", exc.response.status_code)
        return {"status": "provider_error", "message": "Jupiter quote service rejected the request."}
    except httpx.HTTPError as exc:
        logger.warning("Jupiter order preview transport error: %s", type(exc).__name__)
        return {"status": "provider_unavailable", "message": "Jupiter quote service is temporarily unavailable."}
    # Never return the serialized transaction in preview mode.
    return {
        "status": "quote_ready",
        "provider": "Jupiter Swap API v2",
        "input_mint": payload.input_mint,
        "output_mint": payload.output_mint,
        "in_amount": order.get("inAmount"),
        "out_amount": order.get("outAmount"),
        "other_amount_threshold": order.get("otherAmountThreshold"),
        "price_impact_pct": order.get("priceImpact"),
        "route_plan": order.get("routePlan", []),
        "request_id": order.get("requestId"),
        "transaction_prepared": bool(order.get("transaction")),
        "transaction_returned": False,
        "execution_enabled": False,
        "message": "Quote only. Atlas entry gates and paper/live controls are not satisfied for execution. No transaction was signed or sent.",
    }

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
