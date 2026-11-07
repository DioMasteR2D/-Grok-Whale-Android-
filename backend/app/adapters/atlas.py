"""Helius flow adapter with automatic leaderboard fallback.

Primary discovery: SolScope/GMGN.
Fallback discovery: dEdge public read-only top-wallet leaderboard.
Helius requests use bounded concurrency and retry transient rate/server errors.
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
    from app.adapters.solscope import fetch_wallet_leaderboard
    try:
        leaderboard = await fetch_wallet_leaderboard("7d")
        addresses = _solscope_wallets(leaderboard, limit)
        if addresses:
            return addresses, "solscope_gmgn_7d", []
        primary_error = "SolScope returned no recognizable wallet addresses."
    except Exception as exc:
        primary_error = f"SolScope unavailable ({type(exc).__name__})."
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


async def _fetch_one(client, address, limit):
    url = f"{HELIUS_BASE}/addresses/{address}/transactions"
    params = {"api-key": HELIUS_API_KEY, "limit": max(1, min(limit, 25))}
    last_status = None
    for attempt in range(4):
        try:
            response = await client.get(url, params=params)
            last_status = response.status_code
            if response.status_code == 429 or response.status_code >= 500:
                if attempt < 3:
                    retry_after = response.headers.get("Retry-After")
                    try:
                        delay = min(12.0, max(1.0, float(retry_after))) if retry_after else (1.5 * (2 ** attempt))
                    except ValueError:
                        delay = 1.5 * (2 ** attempt)
                    await asyncio.sleep(delay)
                    continue
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
        except (httpx.TimeoutException, httpx.TransportError):
            if attempt < 3:
                await asyncio.sleep(1.5 * (2 ** attempt))
                continue
            raise
        except httpx.HTTPStatusError:
            # Do not include response body or API URL; those may contain secrets.
            raise RuntimeError(f"Helius HTTP {last_status}")
    raise RuntimeError(f"Helius HTTP {last_status or 'unknown'}")


async def fetch_wallet_flows(limit: int = 10) -> dict:
    if not HELIUS_API_KEY:
        return {"status": "not_configured", "items": [],
                "message": "Set HELIUS_API_KEY in the service environment."}
    wallets, discovery_source, discovery_warnings = await _discover_wallets(limit=20)
    if not wallets:
        return {"status": "discovery_error", "items": [],
                "discovery": discovery_source, "warnings": discovery_warnings,
                "message": "No eligible wallets were discovered from SolScope or the public fallback."}

    # Low concurrency plus bounded retries avoids bursting the Helius rate limit.
    sem = asyncio.Semaphore(2)
    async with httpx.AsyncClient(timeout=25) as client:
        async def one(address):
            async with sem:
                return await _fetch_one(client, address, limit)
        results = await asyncio.gather(*(one(a) for a in wallets), return_exceptions=True)

    items, errors = [], []
    for address, result in zip(wallets, results):
        if isinstance(result, Exception):
            message = str(result)
            status_code = None
            match = re.search(r"Helius HTTP (\d{3})", message)
            if match:
                status_code = int(match.group(1))
            errors.append({"wallet": address, "error": type(result).__name__,
                           "http_status": status_code})
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
