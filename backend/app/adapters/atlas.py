"""Read-only Helius activity adapter for the Atlas wallet set.

This returns observed wallet activity only. Atlas' Anthropic agent, sector
inference and propagation scoring are not represented as available unless its
own service is deployed and configured separately.
"""
import os
import asyncio
import httpx

HELIUS_API_KEY = os.getenv("HELIUS_API_KEY", "")
ATLAS_SEED_WALLETS = [x.strip() for x in os.getenv("ATLAS_SEED_WALLETS", "").split(",") if x.strip()]
HELIUS_BASE = "https://api.helius.xyz/v0"

async def fetch_wallet_flows(limit: int = 10) -> dict:
    if not HELIUS_API_KEY or not ATLAS_SEED_WALLETS:
        return {"status": "not_configured", "items": [], "message": "Set HELIUS_API_KEY and ATLAS_SEED_WALLETS (comma-separated public addresses)."}
    sem = asyncio.Semaphore(4)
    async with httpx.AsyncClient(timeout=20) as client:
        async def one(address: str):
            async with sem:
                url = f"{HELIUS_BASE}/addresses/{address}/transactions"
                response = await client.get(url, params={"api-key": HELIUS_API_KEY, "limit": max(1, min(limit, 25))})
                response.raise_for_status()
                txs = response.json()
                return {
                    "wallet_address": address,
                    "transactions": [{
                        "signature": tx.get("signature"),
                        "timestamp": tx.get("timestamp"),
                        "type": tx.get("type"),
                        "description": tx.get("description"),
                        "token_transfers": tx.get("tokenTransfers", []),
                        "native_transfers": tx.get("nativeTransfers", []),
                    } for tx in txs]
                }
        results = await asyncio.gather(*(one(a) for a in ATLAS_SEED_WALLETS), return_exceptions=True)
    items, errors = [], []
    for address, result in zip(ATLAS_SEED_WALLETS, results):
        if isinstance(result, Exception):
            errors.append({"wallet": address, "error": str(result)})
        else:
            items.append(result)
    return {"status": "partial" if errors else "ok", "items": items, "errors": errors,
            "message": "Raw Helius wallet activity only; Atlas agent scoring requires the Atlas service."}
