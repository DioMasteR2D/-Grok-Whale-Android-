"""Grok (xAI) analysis adapter for observed Helius wallet flows.

Model output is advisory and untrusted. It never supplies verified on-chain
safety evidence, never creates orders, and never signs or executes transactions.
"""
import json
import logging
import os
import httpx

log = logging.getLogger("grok-whale-atlas")
XAI_API_KEY = os.getenv("XAI_API_KEY", "").strip()
GROK_MODEL = os.getenv("GROK_MODEL", "grok-3-mini").strip()

SYSTEM = """You are the DioMasteR2D Grok on-chain flow analyst. Analyze only supplied
observed wallet/token transfer facts. Return JSON only with keys: summary (string),
alerts (array). Each alert should contain origin_wallet (string), mint (string),
action (originating|propagating|distributing|rotating|unknown),
propagation_score (number 0..1 or null), observed_follow_wallets (integer or null),
crowding_score (number 0..1 or null), rationale (string),
evidence_signatures (array of strings), missing_evidence (array of strings).
Do not infer LP burn, mint revocation, token safety, trade intent, ROI, or wallet
ranking. If evidence is absent, use null or list it in missing_evidence.
Wallet activity is not necessarily a discretionary buy or sell. Never recommend
execution. Do not fabricate wallet relationships or facts."""

def _compact_flows(payload: dict, max_wallets: int = 20) -> list:
    result = []
    for wallet in (payload.get("items") or [])[:max_wallets]:
        address = wallet.get("wallet_address")
        txs = []
        for tx in (wallet.get("transactions") or [])[:25]:
            transfers = []
            for transfer in (tx.get("token_transfers") or [])[:20]:
                transfers.append({
                    "mint": transfer.get("mint"),
                    "amount": transfer.get("tokenAmount"),
                    "from": transfer.get("fromUserAccount"),
                    "to": transfer.get("toUserAccount"),
                })
            if transfers:
                txs.append({
                    "signature": tx.get("signature"),
                    "timestamp": tx.get("timestamp"),
                    "type": tx.get("type"),
                    "transfers": transfers,
                })
        if address and txs:
            result.append({"wallet": address, "transactions": txs})
    return result

def _validate_alerts(alerts):
    if not isinstance(alerts, list):
        raise ValueError("Grok response alerts must be an array")
    clean = []
    for alert in alerts[:20]:
        if not isinstance(alert, dict):
            continue
        score = alert.get("propagation_score")
        crowding = alert.get("crowding_score")
        followers = alert.get("observed_follow_wallets")
        if not isinstance(score, (int, float)) or not 0 <= score <= 1:
            score = None
        if not isinstance(crowding, (int, float)) or not 0 <= crowding <= 1:
            crowding = None
        if not isinstance(followers, int) or followers < 0:
            followers = None
        clean.append({
            "origin_wallet": str(alert.get("origin_wallet") or ""),
            "mint": str(alert.get("mint") or ""),
            "action": alert.get("action") if alert.get("action") in {
                "originating", "propagating", "distributing", "rotating", "unknown"
            } else "unknown",
            "propagation_score": score,
            "observed_follow_wallets": followers,
            "crowding_score": crowding,
            "rationale": str(alert.get("rationale") or "")[:1200],
            "evidence_signatures": [str(x) for x in alert.get("evidence_signatures", [])[:20]],
            "missing_evidence": [str(x) for x in alert.get("missing_evidence", [])[:20]],
            "model_generated_unverified": True,
        })
    return clean

async def analyze_atlas_flows(flow_payload: dict, top_wallets: list) -> dict:
    if not XAI_API_KEY:
        return {
            "status": "not_configured", "agent": "grok-xai",
            "message": "XAI_API_KEY is not configured on the backend.",
        }
    if flow_payload.get("status") not in ("ok", "partial"):
        return {
            "status": "source_unavailable", "agent": "grok-xai",
            "message": "No usable Helius activity is available.",
        }
    observed = _compact_flows(flow_payload)
    if not observed:
        return {
            "status": "no_activity", "agent": "grok-xai", "alerts": [],
            "message": "No token transfer evidence was returned for analysis.",
        }
    payload = {
        "top10_bes_wallets": [
            wallet.get("wallet_address") for wallet in top_wallets
            if wallet.get("wallet_address")
        ],
        "helius_observed_wallet_activity": observed,
        "discovery_source": flow_payload.get("discovery"),
    }
    headers = {"Authorization": f"Bearer {XAI_API_KEY}", "Content-Type": "application/json"}
    body = {
        "model": GROK_MODEL,
        "temperature": 0,
        "response_format": {"type": "json_object"},
        "messages": [
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content":
                "Analyze this observed batch. Return only the required JSON.\n" +
                json.dumps(payload, separators=(",", ":"))},
        ],
    }
    try:
        async with httpx.AsyncClient(timeout=35) as client:
            response = await client.post(
                "https://api.x.ai/v1/chat/completions",
                headers=headers,
                json=body,
            )
        if response.status_code == 429:
            return {
                "status": "rate_limited", "agent": "grok-xai",
                "message": "xAI rate limit reached.",
            }
        response.raise_for_status()
        data = response.json()
        content = data["choices"][0]["message"]["content"]
        parsed = json.loads(content)
        alerts = _validate_alerts(parsed.get("alerts", []))
        return {
            "status": "ok", "agent": "grok-xai", "model": GROK_MODEL,
            "summary": str(parsed.get("summary", ""))[:2000],
            "alerts": alerts, "wallets_analyzed": len(observed),
            "top10_wallets_supplied": len(payload["top10_bes_wallets"]),
            "analysis_is_advisory": True,
            "model_output_is_not_onchain_verification": True,
            "missing_safety_checks": [
                "lp_burned", "mint_revoked", "two_follow_wallets_within_5m",
                "verified_crowding", "persistent_risk_exit_engine",
            ],
            "execution_enabled": False,
            "message": "Grok analysis only. AI estimates are unverified and cannot satisfy mandatory on-chain entry gates.",
        }
    except httpx.HTTPStatusError as exc:
        log.warning("Grok xAI request failed with HTTP %s", exc.response.status_code)
        return {
            "status": "provider_error", "agent": "grok-xai",
            "message": "xAI rejected the Grok analysis request.",
        }
    except (httpx.HTTPError, ValueError, KeyError, IndexError, TypeError) as exc:
        log.warning("Grok analysis unavailable: %s", type(exc).__name__)
        return {
            "status": "analysis_error", "agent": "grok-xai",
            "message": "Grok response was unavailable or invalid.",
        }
