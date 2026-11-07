"""Helius flow adapter with automatic leaderboard fallback.

Primary discovery: existing SolScope/GMGN proxy.
Fallback discovery: dEdge public read-only top-wallet leaderboard (no API key).
The dEdge public leaderboard is a cached 15-day snapshot; stale wallets are
excluded. Helius supplies raw on-chain activity, not AI scoring.
"""
import os
import re
import asyncio
import httpx

HELIUS_API_KEY = os.getenv("HELIUS_API_KEY", "")
HELIUS_BASE = "https://api.helius.xyz/v0"
DEDGE_LEADERBOARD_URL = "https://api.dedge.pro/public/top-wallets"
BASE58_ADDRESS = re.compile(r"^[1-9A-HJ-NP-Za-km-z]{32,44}$")


def _solscope_wallets(payload, limit=20):
    found, seen = [], set()
    keys = {"wallet_address", "walletAddress", "address"}

    def walk(value):
        if isinstance(value, dict):
            for key, item in value.items():
                if key in keys and isinstance(item, str):
                    candidate = item.strip()
                    if BASE58_ADDRESS.fullmatch(candidate) and candidate not in seen:
                        seen.add(candidate)
                        found.append(candidate)
                if isinstance(item, (dict, list)):
                    walk(item)
        elif isinstance(value, list):
            for item in value:
                walk(item)

    walk(payload)
    return found[:limit]


async def _discover_wallets(limit=20):
    # Prefer SolScope/GMGN, but do not let its 502 outage stop discovery.
    from app.adapters.solscope import fetch_wallet_leaderboard
    try:
        leaderboard = await fetch_wallet_leaderboard("7d")
        addresses = _solscope_wallets(leaderboard, limit)
        if addresses:
            return addresses, "solscope_gmgn_7d", []
        primary_error = "SolScope returned no recognizable wallet addresses."
    except Exception as exc:
        primary_error = f"SolScope unavailable ({type(exc).__name__})."

    # Public, read-only dEdge endpoint. It is cached and may be incomplete.
    try:
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.get(DEDGE_LEADERBOARD_URL)
            response.raise_for_status()
            payload = response.json()
        rows = payload.get("wallets", []) if isinstance(payload, dict) else []
        addresses = []
        for row in rows:
            if not isinstance(row, dict):
                continue
            address = row.get("wallet_address")
            # Exclude stale or explicitly skip-rated records.
            verdict = row.get("verdict") or {}
            if row.get("is_stale") is True or verdict.get("decision") == "skip":
                continue
            if isinstance(address, str) and BASE58_ADDRESS.fullmatch(address):
                addresses.append(address)
            if len(addresses) >= limit:
                break
        if addresses:
            return addresses, "dedge_public_top_wallets_15d", [primary_error]
        return [], "none", [primary_error, "dEdge returned no eligible wallet addresses."]
    except Exception as exc:
        return [], "none", [primary_error, f"dEdge fallback unavailable ({type(exc).__name__})."]


async def fetch_wallet_flows(limit: int = 10) -> dict:
    if not HELIUS_API_KEY:
        return {"status": "not_configured", "items": [],
                "message": "Set HELIUS_API_KEY in the service environment."}

    wallets, discovery_source, discovery_warnings = await _discover_wallets(limit=20)
    if not wallets:
        return {"status": "discovery_error", "items": [],
                "discovery": discovery_source, "warnings": discovery_warnings,
                "message": "No eligible wallets were discovered from SolScope or the public fallback."}

    sem = asyncio.Semaphore(4)
    async with httpx.AsyncClient(timeout=20) as client:
        async def one(address: str):
            async with sem:
                url = f"{HELIUS_BASE}/addresses/{address}/transactions"
                response = await client.get(
                    url, params={"api-key": HELIUS_API_KEY, "limit": max(1, min(limit, 25))}
                )
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
            errors.append({"wallet": address, "error": type(result).__name__})
        else:
            items.append(result)

    return {
        "status": "ok" if items and not errors else ("partial" if items else "helius_error"),
        "discovery": discovery_source,
        "wallets_discovered": len(wallets),
        "wallets_with_activity_response": len(items),
        "items": items,
        "errors": errors,
        "warnings": discovery_warnings,
        "message": "Helius raw wallet activity only. dEdge fallback is a cached 15-day leaderboard; Atlas AI scoring remains a separate, undeployed service."
    }
