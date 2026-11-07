"""Atlas flow adapter.

Atlas remains its own TypeScript/Bun service (Helius + Anthropic). The Android
backend consumes its read-only flow endpoint; no private keys are used here.
"""
import os
import httpx

ATLAS_API_URL = os.getenv("ATLAS_API_URL", "").rstrip("/")

async def fetch_flows() -> dict:
    if not ATLAS_API_URL:
        return {"status": "not_configured", "items": [], "message": "Configure the Atlas read-only API URL."}
    async with httpx.AsyncClient(timeout=20) as client:
        response = await client.get(ATLAS_API_URL + "/api/flows")
        response.raise_for_status()
        return {"status": "ok", "items": response.json()}
