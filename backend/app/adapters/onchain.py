"""Independent Solana RPC verification for token safety gates.

LP burn is deliberately conservative: it passes only when the supplied LP mint's
entire on-chain supply is zero. A high burn percentage is not treated as burned.
"""
import base64
import os
import re
import httpx

RPC_URL = os.getenv("SOLANA_RPC_URL", "").strip()
HELIUS_KEY = os.getenv("HELIUS_API_KEY", "").strip()
B58 = re.compile(r"^[1-9A-HJ-NP-Za-km-z]{32,44}$")

def _rpc_url():
    if RPC_URL:
        return RPC_URL
    if HELIUS_KEY:
        return f"https://mainnet.helius-rpc.com/?api-key={HELIUS_KEY}"
    return ""

async def _rpc(method, params):
    url = _rpc_url()
    if not url:
        return None, "rpc_not_configured"
    async with httpx.AsyncClient(timeout=12) as client:
        response = await client.post(url, json={"jsonrpc":"2.0","id":1,"method":method,"params":params})
        response.raise_for_status()
        payload = response.json()
    if payload.get("error"):
        return None, "rpc_error"
    return payload.get("result"), None

async def verify_token(mint: str, lp_mint: str | None = None):
    if not B58.fullmatch(mint or ""):
        return {"status":"rejected","mint":mint,"checks":{"mint_revoked":False,"lp_burned":False},
                "evidence":{"mint":"invalid_address","lp":"not_checked"}}
    result, error = await _rpc("getAccountInfo", [mint, {"encoding":"base64","commitment":"finalized"}])
    if error or not result or not result.get("value"):
        return {"status":"unavailable","mint":mint,"checks":{"mint_revoked":False,"lp_burned":False},
                "evidence":{"mint":error or "account_not_found","lp":"not_checked"}}
    try:
        raw = base64.b64decode(result["value"]["data"][0])
        if len(raw) < 82:
            raise ValueError("short_mint_account")
        mint_authority_option = int.from_bytes(raw[0:4], "little")
        freeze_authority_option = int.from_bytes(raw[46:50], "little")
        mint_revoked = mint_authority_option == 0
        freeze_revoked = freeze_authority_option == 0
    except Exception:
        return {"status":"unavailable","mint":mint,"checks":{"mint_revoked":False,"lp_burned":False},
                "evidence":{"mint":"malformed_or_unsupported_mint_account","lp":"not_checked"}}
    # Fail closed until the supplied LP mint is associated with the actual pool.
    # Checking an arbitrary mint's zero supply does not prove the pool liquidity was burned.
    lp_burned = False
    lp_evidence = {
        "status": "unverified",
        "reason": "pool_lp_mint_association_not_verified",
        "supplied_lp_mint": lp_mint,
        "rule": "A zero-supply LP mint is insufficient unless its association with the actual token pool is independently verified."
    }
    return {
        "status":"verified" if mint_revoked and lp_burned else "checks_failed_or_incomplete",
        "mint":mint,"lp_mint":lp_mint,
        "checks":{"mint_revoked":mint_revoked,"freeze_authority_revoked":freeze_revoked,
                  "lp_burned":lp_burned},
        "evidence":{"mint":{"mint_authority_option":mint_authority_option,
                            "freeze_authority_option":freeze_authority_option,
                            "commitment":"finalized"},
                    "lp":lp_evidence},
        "warning":"LP burn is fail-closed: this endpoint does not yet discover and verify the actual pool LP mint, so no supplied LP mint can satisfy the LP-burn gate."
    }
