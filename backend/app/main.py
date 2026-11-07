from fastapi import FastAPI, Query
from pydantic import BaseModel
from datetime import datetime, timezone
from app.adapters.solscope import fetch_wallet_leaderboard
from app.adapters.soulwinners import fetch_qualified_wallets
from app.adapters.atlas import fetch_wallet_flows

app = FastAPI(title="DioMasteR2D Grok Whale API", version="0.2.0")

class PaperStatus(BaseModel):
    mode: str = "paper"
    live_trading_enabled: bool = False
    note: str = "Simulation only. No transaction signing or order execution."

@app.get("/health")
def health():
    return {"status": "ok", "service": "grok-whale-api", "time": datetime.now(timezone.utc).isoformat()}

@app.get("/api/v1/status", response_model=PaperStatus)
def status():
    return PaperStatus()

@app.get("/api/v1/whales")
async def whales(period: str = Query(default="7d", pattern="^(1d|7d|30d)$"), limit: int = Query(default=100, ge=1, le=500)):
    solscope, soulwinners = await __import__("asyncio").gather(
        fetch_wallet_leaderboard(period),
        __import__("asyncio").to_thread(fetch_qualified_wallets, limit),
    )
    return {"period": period, "sources": {"solscope": solscope, "soulwinners": soulwinners}}

@app.get("/api/v1/atlas/flows")
async def atlas_flows(limit: int = Query(default=10, ge=1, le=25)):
    return await fetch_wallet_flows(limit)

@app.get("/api/v1/signals")
def signals():
    return {"items": [], "source_status": "pending_fusion",
            "message": "Signals are withheld until upstream source records are available and normalized."}

@app.get("/api/v1/paper-portfolio")
def paper_portfolio():
    return {"mode": "paper", "quote_currency": "USD", "cash": 0.0,
            "open_positions": [], "realized_pnl": 0.0, "unrealized_pnl": 0.0,
            "live_trading_enabled": False}
