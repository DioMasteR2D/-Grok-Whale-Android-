"""Deterministic, explainable analysis of Helius wallet token flows.

This is a research heuristic, not an LLM prediction or trading recommendation.
Only tokens with identifiable mint addresses and directional transfers are scored.
"""
from collections import defaultdict
from datetime import datetime, timezone

def build_flow_signals(flow_payload: dict, max_items: int = 25) -> dict:
    if flow_payload.get("status") not in ("ok", "partial"):
        return {
            "status": "source_unavailable",
            "items": [],
            "source_status": flow_payload.get("status", "unknown"),
            "message": "No usable Helius flow data is available."
        }

    wallets = flow_payload.get("items", [])
    token_rows = defaultdict(lambda: {
        "wallet_net": defaultdict(float),
        "wallet_buys": defaultdict(int),
        "wallet_sells": defaultdict(int),
        "signatures": set(),
        "latest_timestamp": 0,
        "transfer_count": 0,
    })

    for wallet_result in wallets:
        wallet = wallet_result.get("wallet_address")
        if not wallet:
            continue
        for tx in wallet_result.get("transactions", []):
            signature = tx.get("signature")
            ts = tx.get("timestamp")
            try:
                ts = int(ts or 0)
            except (TypeError, ValueError):
                ts = 0
            for transfer in tx.get("token_transfers", []):
                mint = transfer.get("mint")
                if not mint or not isinstance(mint, str):
                    continue
                try:
                    amount = abs(float(transfer.get("tokenAmount") or 0))
                except (TypeError, ValueError):
                    continue
                if amount <= 0:
                    continue
                source = transfer.get("fromUserAccount") or ""
                target = transfer.get("toUserAccount") or ""
                row = token_rows[mint]
                direction = 0
                if target == wallet and source != wallet:
                    direction = 1
                    row["wallet_buys"][wallet] += 1
                elif source == wallet and target != wallet:
                    direction = -1
                    row["wallet_sells"][wallet] += 1
                if direction:
                    row["wallet_net"][wallet] += direction * amount
                    row["transfer_count"] += 1
                    if signature:
                        row["signatures"].add(signature)
                    row["latest_timestamp"] = max(row["latest_timestamp"], ts)

    now = int(datetime.now(timezone.utc).timestamp())
    results = []
    for mint, row in token_rows.items():
        net = row["wallet_net"]
        buyers = sum(1 for value in net.values() if value > 0)
        sellers = sum(1 for value in net.values() if value < 0)
        participants = buyers + sellers
        if participants == 0:
            continue
        buy_ratio = buyers / participants
        wallet_coverage = min(1.0, participants / 5.0)
        activity = min(1.0, row["transfer_count"] / 10.0)
        age_hours = max(0.0, (now - row["latest_timestamp"]) / 3600) if row["latest_timestamp"] else 999999
        freshness = max(0.0, 1.0 - age_hours / 72.0)
        score = round(100 * (0.50 * buy_ratio + 0.25 * wallet_coverage + 0.15 * activity + 0.10 * freshness))
        if buyers > sellers:
            bias = "accumulation"
        elif sellers > buyers:
            bias = "distribution"
        else:
            bias = "mixed"
        results.append({
            "mint": mint,
            "bias": bias,
            "score": score,
            "wallets_buying": buyers,
            "wallets_selling": sellers,
            "wallets_observed": participants,
            "transfer_count": row["transfer_count"],
            "unique_transactions": len(row["signatures"]),
            "latest_activity": datetime.fromtimestamp(row["latest_timestamp"], timezone.utc).isoformat() if row["latest_timestamp"] else None,
            "confidence": "low" if participants < 2 or row["transfer_count"] < 2 else ("medium" if participants < 4 else "higher"),
            "action": "watch" if bias == "accumulation" and score >= 55 and buyers >= 2 else "observe",
            "score_basis": "wallet direction, participant coverage, transfer count, and recency",
            "limitations": ["No token price, liquidity, market cap, or holder concentration was checked.",
                            "Transfers are not guaranteed to represent discretionary buys or sells.",
                            "Heuristic score is not an AI prediction or financial advice."]
        })

    results.sort(key=lambda item: (item["score"], item["wallets_buying"], item["transfer_count"]), reverse=True)
    return {
        "status": "ok",
        "engine": "deterministic_flow_heuristic_v1",
        "signals_count": len(results[:max_items]),
        "wallets_analyzed": len(wallets),
        "items": results[:max_items],
        "source_status": flow_payload.get("status"),
        "discovery": flow_payload.get("discovery"),
        "message": "Research watchlist only. No orders are generated or executed."
    }
