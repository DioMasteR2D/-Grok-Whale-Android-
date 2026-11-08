from fastapi import FastAPI, Query, Header, HTTPException
from pydantic import BaseModel, Field
from pydantic import field_validator
import os
import re
import httpx
from datetime import datetime, timezone
import logging
import asyncio
import time
import hmac
from app.adapters.solscope import fetch_wallet_leaderboard
from app.adapters.soulwinners import fetch_qualified_wallets, initialize_postgres_schema, DB_PATH, DATABASE_URL
from app.adapters.soulwinners_ingestion import run_ingestion, discover_and_ingest_wallets
from app.adapters.atlas import fetch_wallet_flows, HELIUS_API_KEY
from app.adapters.atlas_agent import analyze_atlas_flows, XAI_API_KEY, GROK_MODEL
from app.analysis import build_flow_signals, build_atlas_propagation
from app.strategy import STRATEGY, session_status, evaluate_entry
from app import paper
from app.adapters.onchain import verify_token
from app.adapters.prices import fetch_prices

logger = logging.getLogger("grok-whale-api")
app = FastAPI(title="DioMasteR2D Grok Whale API", version="0.6.0")

# Share one Helius scan between dashboard endpoints; avoids duplicate requests
# when the Android client refreshes flows and signals together.
_FLOW_CACHE_TTL_SECONDS = 45
_flow_cache = {}
_flow_cache_lock = asyncio.Lock()
_SOULWINNERS_REFRESH_HOURS = max(1, min(24, int(os.getenv("SOULWINNERS_REFRESH_HOURS", "6"))))
_soulwinners_worker_task = None
_soulwinners_ingestion_lock = asyncio.Lock()

async def _soulwinners_ingestion_worker():
    """Run an initial bounded history collection, then refresh on a fixed cadence."""
    while True:
        if DATABASE_URL and HELIUS_API_KEY and not _soulwinners_ingestion_lock.locked():
            async with _soulwinners_ingestion_lock:
                try:
                    logger.info("SoulWinners collector starting candidate discovery.")
                    result = await discover_and_ingest_wallets(limit=20)
                    logger.info(
                        "SoulWinners scheduled ingestion status=%s provider=%s candidates=%s completed=%s failed=%s tx_upserted=%s",
                        result.get("status"), result.get("discovery_provider") or result.get("provider"),
                        result.get("candidates_discovered"), result.get("wallets_completed"),
                        len(result.get("wallets_failed", [])), result.get("transactions_upserted")
                    )
                    if result.get("discovery_warnings"):
                        logger.warning("SoulWinners discovery fallback warnings=%s", result.get("discovery_warnings"))
                    if result.get("message"):
                        logger.info("SoulWinners collector detail: %s", result.get("message"))
                except Exception as exc:
                    logger.warning("SoulWinners scheduled ingestion failed (%s)", type(exc).__name__)
        else:
            logger.warning("SoulWinners collector skipped: database or Helius configuration missing.")
        await asyncio.sleep(_SOULWINNERS_REFRESH_HOURS * 3600)

async def get_cached_wallet_flows(limit: int = 10):
    now = time.monotonic()
    async with _flow_cache_lock:
        cached = _flow_cache.get(limit)
        if cached and now - cached["stored_at"] < _FLOW_CACHE_TTL_SECONDS:
            return cached["payload"]
        payload = await fetch_wallet_flows(limit)
        _flow_cache[limit] = {"stored_at": time.monotonic(), "payload": payload}
        return payload

class SoulWinnersIngestionRequest(BaseModel):
    wallet_addresses: list[str] = Field(min_length=1, max_length=100)

    @field_validator("wallet_addresses")
    @classmethod
    def validate_wallets(cls, values):
        if any(not re.fullmatch(r"[1-9A-HJ-NP-Za-km-z]{32,44}", value.strip()) for value in values):
            raise ValueError("Every wallet must be a valid-looking Solana base58 address")
        return list(dict.fromkeys(value.strip() for value in values))

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
async def initialize_sources():
    if DATABASE_URL:
        result = initialize_postgres_schema()
        if result.get("status") != "ok":
            logger.warning("SoulWinners schema initialization did not complete: %s", result.get("status"))
        else:
            logger.info("SoulWinners PostgreSQL schema is ready.")
        try:
            from app.adapters.soulwinners_ingestion import initialize_ingestion_schema
            initialize_ingestion_schema()
            logger.info("SoulWinners 30-day ingestion tables are ready.")
        except Exception as exc:
            logger.warning("SoulWinners ingestion schema initialization failed (%s)", type(exc).__name__)
        try:
            paper.initialize()
            logger.info("Persistent paper portfolio schema is ready.")
        except Exception as exc:
            logger.warning("Paper portfolio initialization failed (%s)", type(exc).__name__)
    else:
        logger.info("SoulWinners PostgreSQL is not configured; skipping schema initialization.")
    global _soulwinners_worker_task
    if DATABASE_URL and HELIUS_API_KEY and _soulwinners_worker_task is None:
        _soulwinners_worker_task = asyncio.create_task(_soulwinners_ingestion_worker())
        logger.info("SoulWinners scheduled 30-day collector enabled (every %s hours).", _SOULWINNERS_REFRESH_HOURS)

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
    db = fetch_qualified_wallets(1) if (DATABASE_URL or DB_PATH) else {"status": "not_configured"}
    return {
        "mode": "paper",
        "live_trading_enabled": False,
        "sources": {
            "gmgn_leaderboard": "direct_read_only_adapter",
            "soulwinners_database": db.get("status", "unknown"),
            "atlas_helius": "parsed_events_configured_for_qualified_wallet_scans" if HELIUS_API_KEY else "missing_helius_key",
            "soulwinners_history": "helius_parsed_events_30d_collector",
            "flow_analytics": "deterministic_v1",
            "grok_agent": {"status": "configured", "provider": "xAI", "model": GROK_MODEL} if XAI_API_KEY else {"status": "missing_xai_key", "provider": "xAI"},
        },
        "note": "Helius provides observed wallet activity; Grok analysis is advisory only. AI-generated propagation/crowding estimates never satisfy on-chain safety gates.",
    }

@app.post("/api/v1/soulwinners/ingest")
async def soulwinners_ingest(payload: SoulWinnersIngestionRequest, authorization: str | None = Header(default=None)):
    """Admin-only raw 30-day history ingestion. Never qualifies wallets by itself."""
    expected = os.getenv("SOULWINNERS_INGEST_TOKEN", "").strip()
    if not expected:
        raise HTTPException(status_code=503, detail="Ingestion admin token is not configured.")
    if not hmac.compare_digest(authorization or "", f"Bearer {expected}"):
        raise HTTPException(status_code=401, detail="Unauthorized.")
    if not DATABASE_URL:
        raise HTTPException(status_code=503, detail="SoulWinners PostgreSQL is not configured.")
    return await run_ingestion(payload.wallet_addresses, days=30)

@app.post("/api/v1/soulwinners/ingest/discover")
async def soulwinners_discover_and_ingest(limit: int = Query(default=20, ge=1, le=100), authorization: str | None = Header(default=None)):
    """Admin-only discovery from GMGN 30d leaderboard followed by raw 30d ingestion."""
    expected = os.getenv("SOULWINNERS_INGEST_TOKEN", "").strip()
    if not expected:
        raise HTTPException(status_code=503, detail="Ingestion admin token is not configured.")
    if not hmac.compare_digest(authorization or "", f"Bearer {expected}"):
        raise HTTPException(status_code=401, detail="Unauthorized.")
    if not DATABASE_URL:
        raise HTTPException(status_code=503, detail="SoulWinners PostgreSQL is not configured.")
    return await discover_and_ingest_wallets(limit=limit)
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


@app.post("/api/v1/atlas/agent/scan")
async def atlas_agent_scan(limit: int = Query(default=10, ge=1, le=20)):
    """Scan only SoulWinners-qualified wallets; never substitute unrelated discovery."""
    top_result = fetch_qualified_wallets(500) if DATABASE_URL or DB_PATH else {"status": "not_configured", "items": []}
    top_items, qualification = _soulwinners_top10(top_result.get("items", [])) if top_result.get("status") == "ok" else ([], {"returned": 0})
    if not top_items:
        return {
            "status": "no_qualified_wallets", "agent": "grok-xai", "alerts": [],
            "deterministic_propagation": {"status": "blocked", "items": []},
            "wallet_ranking_status": top_result.get("status"), "wallet_qualification": qualification,
            "message": "No SoulWinners wallets satisfy the current measured qualification gates. Atlas scan is not run against unrelated discovery wallets.",
            "live_trading_enabled": False,
        }
    qualified_addresses = [row["wallet_address"] for row in top_items]
    flows = await fetch_wallet_flows(limit=25, wallet_addresses=qualified_addresses)
    deterministic = build_atlas_propagation(flows, top_items, window_seconds=300)
    analysis = await analyze_atlas_flows(flows, top_items)
    return {
        **analysis, "source_status": flows.get("status"),
        "wallet_ranking_status": top_result.get("status"), "wallet_qualification": qualification,
        "deterministic_propagation": deterministic, "ai_is_advisory_only": True,
        "live_trading_enabled": False,
    }

@app.get("/api/v1/atlas/flows")
async def atlas_flows(limit: int = Query(default=10, ge=1, le=25)):
    return await get_cached_wallet_flows(limit)

class TokenVerifyRequest(BaseModel):
    mint: str = Field(min_length=32, max_length=44)
    lp_mint: str | None = Field(default=None, min_length=32, max_length=44)

@app.post("/api/v1/atlas/token/verify")
async def atlas_token_verify(payload: TokenVerifyRequest):
    """Verify mint authority and supplied pool LP supply directly at finalized RPC."""
    return await verify_token(payload.mint, payload.lp_mint)

@app.get("/api/v1/prices")
async def token_prices(mints: str = Query(min_length=32, max_length=2200)):
    requested = [x.strip() for x in mints.split(",") if x.strip()]
    return await fetch_prices(requested)

def _is_origin_exit_after_entry(tx: dict, origin: str, mint: str, opened_at: str | None) -> bool:
    """Accept only a timestamped SWAP outflow that occurred after this position opened."""
    if not opened_at or not isinstance(tx, dict):
        return False
    try:
        opened = datetime.fromisoformat(opened_at.replace("Z", "+00:00"))
        if opened.tzinfo is None:
            opened = opened.replace(tzinfo=timezone.utc)
        timestamp = int(tx.get("timestamp"))
        if timestamp <= 0 or datetime.fromtimestamp(timestamp, timezone.utc) <= opened:
            return False
    except (TypeError, ValueError, OverflowError):
        return False
    if str(tx.get("type", "")).upper() != "SWAP":
        return False
    return any(
        isinstance(transfer, dict)
        and transfer.get("mint") == mint
        and transfer.get("fromUserAccount") == origin
        for transfer in (tx.get("tokenTransfers") or [])
    )


@app.get("/api/v1/paper/session-summary")
def paper_session_summary():
    """Return measured paper activity for the Europe/Athens 13:30–21:30 session."""
    return paper.session_summary()


@app.get("/api/v1/paper/refresh")
async def refresh_paper_prices():
    """Refresh open paper positions from Jupiter Price v3 and enforce paper SL."""
    portfolio = paper.summary()
    if portfolio.get("status") != "ok":
        return {"status":"paper_unavailable","portfolio":portfolio}
    positions = portfolio.get("open_positions", [])
    if not positions:
        return {"status":"ok","updated":[],"message":"No open paper positions."}
    # Close a whale-linked paper position only on an observed Helius SWAP
    # with an outgoing transfer of the exact token mint from the origin wallet.
    whale_exits = []
    if HELIUS_API_KEY:
        async with httpx.AsyncClient(timeout=15) as client:
            for position in positions:
                origin = position.get("origin_wallet")
                if not origin:
                    continue
                try:
                    response = await client.get(
                        "https://api.helius.xyz/v0/addresses/" + origin + "/transactions",
                        params={"api-key":HELIUS_API_KEY,"limit":25}
                    )
                    response.raise_for_status()
                    txs = response.json()
                    for tx in txs if isinstance(txs,list) else []:
                        if _is_origin_exit_after_entry(
                            tx, origin, position["mint"], position.get("opened_at")
                        ):
                            whale_exits.append({"position_id":position["id"],"mint":position["mint"],
                                                "origin_wallet":origin,"signature":tx.get("signature"),
                                                "timestamp":tx.get("timestamp")})
                            break
                except httpx.HTTPError:
                    continue
    closed = []
    for event in whale_exits:
        result = paper.close(event["position_id"])
        if result.get("status") == "closed":
            closed.append({**event,"paper_close":result})
    portfolio = paper.summary()
    positions = portfolio.get("open_positions", [])
    if not positions:
        return {"status":"ok","whale_exits":closed,"updated":[],
                "message":"Whale exits processed; no open paper positions remain."}
    priced = await fetch_prices([p["mint"] for p in positions])
    if priced.get("status") != "ok":
        return {"status":priced.get("status"),"price_status":priced,"updated":[]}
    marks = {mint:row["usd_price"] for mint,row in priced.get("items",{}).items()
             if row and isinstance(row.get("usd_price"),(int,float))}
    if not marks:
        return {"status":"no_reliable_prices","price_status":priced,"updated":[]}
    marked = paper.mark_prices(marks)
    return {"status":marked.get("status"),"provider":"Jupiter Price API v3",
            "price_status":priced.get("status"),"updated":marked.get("updated",[]),
            "missing_prices":priced.get("missing_prices",[]),"whale_exits":closed,"portfolio":paper.summary(),
            "live_trading_enabled":False}

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

@app.get("/api/v1/execution/readiness")
def execution_readiness():
    """Explicitly report blockers before any real swap can be enabled."""
    db = fetch_qualified_wallets(1) if DATABASE_URL else {"status": "not_configured"}
    checks = {
        "soulwinners_ingestion_verified": False,
        "measured_bes_and_win_rate_available": False,
        "atlas_agent_runtime_deployed": False,
        "lp_burn_and_mint_revocation_provider": bool(HELIUS_API_KEY or os.getenv("SOLANA_RPC_URL")),
        "six_atlas_entry_gates_verified": False,
        "jupiter_order_preview_available": True,
        "phantom_transaction_signing_and_approval_tested": False,
        "jupiter_price_v3_configured": bool(os.getenv("JUPITER_API_KEY")),
        "risk_and_exit_engine_persistent": False,
        "origin_whale_exit_detection_verified": False,
    }
    blockers = [name for name, passed in checks.items() if not passed]
    return {
        "mode": "paper",
        "automatic_live_buys": False,
        "live_trading_enabled": False,
        "wallet_approval_required": True,
        "soulwinners_database_status": db.get("status", "unknown"),
        "checks": checks,
        "blockers": blockers,
        "ready_for_live_execution": False,
        "message": "Live execution is fail-closed until every data, safety, wallet-approval, and risk check is verified.",
    }
