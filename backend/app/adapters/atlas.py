"""Read-only Helius activity adapter with automatic whale discovery.

Wallets are discovered from the SolScope/GMGN leaderboard. No manual seed
wallet list is required. This adapter reports raw on-chain activity only;
Atlas/Anthropic scoring is a separate service and is never implied here.
"""
import os
import asyncio
import httpx

HELIUS_API_KEY = os.getenv("HELIUS_API_KEY", "")
HELIUS_BASE = "https://api.helius.xyz/v0"

def _wallet_addresses(payload, limit=20):
    found = []
    seen = set()
    keys = {"wallet_address", "walletAddress", "address"}
    def walk(value):
        if isinstance(value, dict):
            for key, item in value.items():
                if key in keys and isinstance(item, str):
                    candidate = item.strip()
                    if 32 <= len(candidate) <= 44 and candidate not in seen:
                        seen.add(candidate)
                        found.append(candidate)
                if isinstance(item, (dict, list)):
                    walk(item)
        elif isinstance(value, list):
            for item in value:
                walk(item)
    walk(payload)
    return found[:limit]

async def fetch_wallet_flows(limit: int = 10) -> dict:
    if not HELIUS_API_KEY:
        return {"status": "not_configured", "items": [], "message": "Set HELIUS_API_KEY in the service environment."}

    # Discover candidates from the live SolScope leaderboard instead of
    # requiring the user to supply wallet addresses manually.
    from app.adapters.solscope import fetch_wallet_leaderboard
    try:
        leaderboard = await fetch_wallet_leaderboard("7d")
        wallets = _wallet_addresses(leaderboard, limit=20)
    except Exception as exc:
        return {"status": "discovery_error", "items": [], "message": "SolScope whale discovery failed.", "error": str(exc)}

    if not wallets:
        return {"status": "no_wallets_found", "items": [], "message": "No wallet addresses were found in the current SolScope leaderboard response."}

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
        results = await asyncio.gather(*(one(a) for a in wallets), return_exceptions=True)
    items, errors = [], []
    for address, result in zip(wallets, results):
        if isinstance(result, Exception):
            errors.append({"wallet": address, "error": str(result)})
        else:
            items.append(result)
    return {
        "status": "partial" if errors else "ok",
        "discovery": "solscope_gmgn_7d_leaderboard",
        "wallets_discovered": len(wallets),
        "items": items,
        "errors": errors,
        "message": "Wallets discovered automatically from SolScope; Helius returns raw activity only. Atlas agent scoring requires separate deployment."
    }
