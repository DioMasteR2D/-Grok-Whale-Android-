"""SolScope/GMGN adapter. The upstream Flask proxy remains untouched.

This adapter consumes the documented GMGN smart-money wallet endpoints through
the upstream-compatible proxy URL. Endpoint response shapes can change; callers
must treat unknown payloads as unavailable rather than inventing metrics.
"""
import os
import httpx

GMGN_PROXY_URL = os.getenv("GMGN_PROXY_URL", "").rstrip("/")

async def fetch_wallet_leaderboard(period: str = "7d") -> dict:
    if not GMGN_PROXY_URL:
        return {"status": "not_configured", "items": [], "message": "Set GMGN_PROXY_URL to the existing SolScope proxy base URL."}
    if period not in {"1d", "7d", "30d"}:
        raise ValueError("period must be 1d, 7d or 30d")
    # The upstream proxy accepts a URL query string as its raw query string.
    target = f"https://gmgn.ai/defi/quotation/v1/smartmoney/sol/wallet_top? 기간={period}"
    async with httpx.AsyncClient(timeout=15) as client:
        response = await client.get(GMGN_PROXY_URL + "/proxy?" + target)
        response.raise_for_status()
        return {"status": "ok", "items": response.json()}
