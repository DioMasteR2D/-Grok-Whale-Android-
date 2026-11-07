"""Atlas LLM analysis adapter.

This is a bounded analysis layer over observed Helius flows. It never invents
LP/mint safety evidence and never creates or executes a swap.
"""
import json
import logging
import os
import httpx

log = logging.getLogger("grok-whale-atlas")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "").strip()
ATLAS_MODEL = os.getenv("ATLAS_MODEL", "claude-3-5-haiku-latest").strip()

SYSTEM = """You are the Atlas on-chain flow analyst. Analyze only the supplied observed
wallet/token transfer facts. Return JSON only with keys: summary (string),
alerts (array). Each alert must contain origin_wallet (string), mint (string),
action (originating|propagating|distributing|rotating|unknown),
propagation_score (number 0..1), observed_follow_wallets (integer),
crowding_score (number 0..1 or null), rationale (string),
evidence_signatures (array of strings), missing_evidence (array of strings).
Do not infer LP burn, mint revocation, token safety, trade intent, ROI, or
wallet ranking. If evidence is absent, use null or list it in missing_evidence.
Never recommend execution. Do not fabricate wallet relationships or facts."""

def _compact_flows(payload: dict, max_wallets: int = 20) -> list:
    result = []
    for wallet in (payload.get("items") or [])[:max_wallets]:
        address = wallet.get("wallet_address")
        txs = []
        for tx in (wallet.get("transactions") or [])[:25]:
            transfers = []
            for t in (tx.get("token_transfers") or [])[:20]:
                transfers.append({
                    "mint": t.get("mint"),
                    "amount": t.get("tokenAmount"),
                    "from": t.get("fromUserAccount"),
                    "to": t.get("toUserAccount"),
                })
            if transfers:
                txs.append({"signature": tx.get("signature"),
                            "timestamp": tx.get("timestamp"),
                            "transfers": transfers})
        if address and txs:
            result.append({"wallet": address, "transactions": txs})
    return result

async def analyze_atlas_flows(flow_payload: dict, top_wallets: list) -> dict:
    if not ANTHROPIC_API_KEY:
        return {"status": "not_configured", "agent": "atlas-llm",
                "message": "ANTHROPIC_API_KEY is not configured."}
    if flow_payload.get("status") not in ("ok", "partial"):
        return {"status": "source_unavailable", "agent": "atlas-llm",
                "message": "No usable Helius activity is available."}
    observed = _compact_flows(flow_payload)
    if not observed:
        return {"status": "no_activity", "agent": "atlas-llm", "alerts": [],
                "message": "No token transfer evidence was returned for analysis."}
    payload = {
        "top10_bes_wallets": [w.get("wallet_address") for w in top_wallets
                              if w.get("wallet_address")],
        "helius_observed_wallet_activity": observed,
        "discovery_source": flow_payload.get("discovery"),
    }
    headers = {"x-api-key": ANTHROPIC_API_KEY, "anthropic-version": "2023-06-01",
               "content-type": "application/json"}
    body = {"model": ATLAS_MODEL, "max_tokens": 2500, "system": SYSTEM,
            "messages": [{"role": "user", "content":
                "Analyze this observed batch. Return only the required JSON.\\n" +
                json.dumps(payload, separators=(",", ":"))}]}
    try:
        async with httpx.AsyncClient(timeout=35) as client:
            response = await client.post("https://api.anthropic.com/v1/messages",
                                         headers=headers, json=body)
        if response.status_code == 429:
            return {"status": "rate_limited", "agent": "atlas-llm",
                    "message": "Anthropic rate limit reached."}
        response.raise_for_status()
        data = response.json()
        text = "".join(b.get("text", "") for b in data.get("content", [])
                       if b.get("type") == "text")
        parsed = json.loads(text)
        alerts = parsed.get("alerts", [])
        if not isinstance(alerts, list):
            raise ValueError("Atlas response alerts must be an array")
        return {"status": "ok", "agent": "atlas-llm", "model": ATLAS_MODEL,
                "summary": str(parsed.get("summary", "")),
                "alerts": alerts[:20], "wallets_analyzed": len(observed),
                "top10_wallets_supplied": len(payload["top10_bes_wallets"]),
                "execution_enabled": False,
                "missing_safety_checks": ["lp_burned", "mint_revoked",
                    "two_follow_wallets_within_5m", "verified_crowding",
                    "persistent_risk_exit_engine"],
                "message": "Atlas AI analysis only. Entry gates must be independently verified; no trade is executed."}
    except httpx.HTTPStatusError as exc:
        log.warning("Atlas Anthropic request failed with HTTP %s", exc.response.status_code)
        return {"status": "provider_error", "agent": "atlas-llm",
                "message": "Anthropic rejected the Atlas analysis request."}
    except (httpx.HTTPError, ValueError, json.JSONDecodeError) as exc:
        log.warning("Atlas analysis unavailable: %s", type(exc).__name__)
        return {"status": "analysis_error", "agent": "atlas-llm",
                "message": "Atlas analysis response was unavailable or invalid."}
