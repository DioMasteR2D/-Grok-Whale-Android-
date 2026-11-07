"""SolScope-compatible GMGN leaderboard adapter.

Uses the existing SolScope Flask proxy unchanged. GMGN response schemas may
change; this module returns source payloads and does not fabricate metrics.
"""
import os
import httpx

GMGN_PROXY_URL = os.getenv("GMGN_PROXY_URL", "").rstrip("/")

async def _get_gmgn(url: str) -> dict:
    if not GMGN_PROXY_URL:
        return {"status": "not_configured", "items": [], "message": "Set GMGN_PROXY_URL to the existing SolScope proxy base URL."}
    async with httpx.AsyncClient(timeout=20) as client:
        response = await client.get(GMGN_PROXY_URL + "/proxy?" + url)
        response.raise_for_status()
        return response.json()

async def fetch_wallet_leaderboard(period: str = "7d") -> dict:
    if period not in {"1d", "7d", "30d"}:
        raise ValueError("period must be 1d, 7d or 30d")
    base = f"https://gmgn.ai/defi/quotation/v1/rank/sol/wallets/{period}"
    pnl, winrate = await __import__("asyncio").gather(
        _get_gmgn(base + "?orderby=pnl&direction=desc&limit=200"),
        _get_gmgn(base + "?orderby=winrate&direction=desc&limit=200"),
    )
    return {"status": "ok", "period": period, "pnl_leaderboard": pnl, "winrate_leaderboard": winrate}
