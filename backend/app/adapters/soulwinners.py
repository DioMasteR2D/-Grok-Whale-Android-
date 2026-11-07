"""SoulWinners data adapter.

SoulWinners is a standalone Python monitoring pipeline with its own SQLite
schema and background workers. This integration reads its exported API/feed
when configured; it does not start its Telegram bot or any execution modules.
"""
import os
import httpx

SOULWINNERS_API_URL = os.getenv("SOULWINNERS_API_URL", "").rstrip("/")

async def fetch_wallets() -> dict:
    if not SOULWINNERS_API_URL:
        return {"status": "not_configured", "items": [], "message": "Configure the SoulWinners read-only feed/API endpoint."}
    async with httpx.AsyncClient(timeout=15) as client:
        response = await client.get(SOULWINNERS_API_URL + "/api/wallets")
        response.raise_for_status()
        return {"status": "ok", "items": response.json()}
