"""Read-only GMGN Solana wallet leaderboard adapter.

The API backend fetches the fixed GMGN leaderboard endpoints directly. No
third-party SolScope proxy URL is required and no arbitrary URL is accepted.
GMGN response schemas can change; raw provider payloads are preserved.
"""
import asyncio
import logging

import httpx

logger = logging.getLogger("grok-whale-api")

GMGN_BASE = "https://gmgn.ai/defi/quotation/v1/rank/sol/wallets"
_ALLOWED_PERIODS = {"1d", "7d", "30d"}
_TIMEOUT = httpx.Timeout(15.0, connect=5.0)
_HEADERS = {
    "Accept": "application/json",
    "User-Agent": "DioMasteR2D-GrokWhale/1.0",
}


async def _get_gmgn(client: httpx.AsyncClient, period: str, orderby: str) -> dict:
    url = f"{GMGN_BASE}/{period}"
    try:
        response = await client.get(
            url,
            params={"orderby": orderby, "direction": "desc", "limit": "200"},
            headers=_HEADERS,
        )
        if response.status_code == 429:
            return {"status": "rate_limited", "items": [], "provider": "GMGN"}
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, dict):
            return {"status": "invalid_response", "items": [], "provider": "GMGN"}
        return {"status": "ok", "provider": "GMGN", "payload": payload}
    except httpx.HTTPStatusError as exc:
        logger.warning("GMGN leaderboard HTTP error: %s", exc.response.status_code)
        return {"status": "provider_error", "items": [], "provider": "GMGN"}
    except (httpx.HTTPError, ValueError) as exc:
        logger.warning("GMGN leaderboard request failed (%s)", type(exc).__name__)
        return {"status": "provider_unavailable", "items": [], "provider": "GMGN"}


async def fetch_wallet_leaderboard(period: str = "7d") -> dict:
    if period not in _ALLOWED_PERIODS:
        raise ValueError("period must be 1d, 7d or 30d")
    async with httpx.AsyncClient(timeout=_TIMEOUT, follow_redirects=False) as client:
        pnl, winrate = await asyncio.gather(
            _get_gmgn(client, period, "pnl"),
            _get_gmgn(client, period, "winrate"),
        )
    return {
        "status": "ok" if pnl.get("status") == winrate.get("status") == "ok" else "partial",
        "provider": "GMGN",
        "period": period,
        "pnl_leaderboard": pnl,
        "winrate_leaderboard": winrate,
        "qualification": "candidate_discovery_only",
        "note": "GMGN leaderboard rows are candidate seeds only; they are not SoulWinners-qualified wallets.",
    }
