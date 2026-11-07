from fastapi import FastAPI
from pydantic import BaseModel
from datetime import datetime, timezone

app = FastAPI(title="DioMasteR2D Grok Whale API", version="0.1.0")

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
def whales():
    # Adapter TODO: normalize verified SolScope / SoulWinners wallet records.
    return {"items": [], "source_status": "not_connected"}

@app.get("/api/v1/atlas/flows")
def atlas_flows():
    # Adapter TODO: map Atlas origin/follower/sector propagation events.
    return {"items": [], "source_status": "not_connected"}

@app.get("/api/v1/signals")
def signals():
    # Signal fusion must include provenance, timestamps and confidence rationale.
    return {"items": [], "source_status": "not_connected"}

@app.get("/api/v1/paper-portfolio")
def paper_portfolio():
    return {
        "mode": "paper",
        "quote_currency": "USD",
        "cash": 0.0,
        "open_positions": [],
        "realized_pnl": 0.0,
        "unrealized_pnl": 0.0,
        "live_trading_enabled": False,
    }
