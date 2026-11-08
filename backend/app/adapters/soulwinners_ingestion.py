"""Bounded 30-day Helius history ingestion for SoulWinners research.

This collector stores raw, timestamped transaction observations. It deliberately
DOES NOT calculate win rate/ROI or promote wallets into qualified_wallets:
those require position-level cost basis, reliable valuation and fee accounting.
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import os
from datetime import datetime, timedelta, timezone
from typing import Any

import httpx

HELIUS_API_KEY = os.getenv("HELIUS_API_KEY", "").strip()
HELIUS_URL = "https://mainnet.helius-rpc.com/v1/parsed-events/transaction-history"
PAGE_SIZE = 100
MAX_PAGES_PER_WALLET = max(1, min(500, int(os.getenv("SOULWINNERS_MAX_PAGES_PER_WALLET", "100"))))


def _timestamp(tx: dict[str, Any]) -> int | None:
    value = tx.get("timestamp")
    try:
        parsed = int(value)
        return parsed if parsed > 0 else None
    except (TypeError, ValueError):
        return None


def _normalize(tx: dict[str, Any], wallet: str, cutoff: int, now: int) -> dict[str, Any] | None:
    ts = _timestamp(tx)
    signature = tx.get("signature")
    if ts is None or not isinstance(signature, str) or not signature:
        return None
    if ts < cutoff or ts > now:
        return None
    # Store the full parsed transaction for later reproducible metric calculation.
    raw = json.dumps(tx, separators=(",", ":"), sort_keys=True, default=str)
    return {
        "wallet_address": wallet,
        "signature": signature,
        "block_time": datetime.fromtimestamp(ts, timezone.utc),
        "tx_type": str(tx.get("type") or "UNKNOWN")[:64],
        "fee_lamports": int(tx.get("fee") or 0) if str(tx.get("fee") or "0").isdigit() else 0,
        "raw_json": raw,
        "payload_hash": hashlib.sha256(raw.encode()).hexdigest(),
    }


async def collect_wallet_history(
    client: httpx.AsyncClient,
    wallet: str,
    cutoff: int,
    now: int,
    max_pages: int = MAX_PAGES_PER_WALLET,
) -> dict[str, Any]:
    """Fetch 30d history with Helius Parsed Events and token-account coverage."""
    pagination_token = None
    rows: dict[str, dict[str, Any]] = {}
    pages = 0
    reached_cutoff = False
    exhausted = False
    while pages < max_pages:
        payload: dict[str, Any] = {
            "address": wallet,
            "limit": PAGE_SIZE,
            "sortOrder": "desc",
            "commitment": "finalized",
            "tokenAccounts": "balanceChanged",
        }
        if pagination_token:
            payload["paginationToken"] = pagination_token
        response = await client.post(
            HELIUS_URL,
            params={"api-key": HELIUS_API_KEY},
            json=payload,
        )
        response.raise_for_status()
        page = response.json()
        if not isinstance(page, dict) or not isinstance(page.get("data"), list):
            raise ValueError("Helius Parsed Events returned an invalid history page")
        pages += 1
        batch = page["data"]
        if not batch:
            next_token = page.get("paginationToken")
            if next_token:
                if next_token == pagination_token:
                    raise ValueError("Helius pagination cursor did not advance")
                pagination_token = next_token
                continue
            exhausted = True
            break

        oldest_in_page = None
        for item in batch:
            if not isinstance(item, dict):
                raise ValueError("Helius page contains a malformed transaction row")
            parsed = item.get("parsed")
            if not isinstance(parsed, dict):
                # An item-level parser failure is not silently counted as valid history.
                continue
            ts_value = parsed.get("blockTime")
            try:
                ts = int(ts_value)
            except (TypeError, ValueError):
                raise ValueError("Parsed transaction has no valid blockTime")
            oldest_in_page = ts if oldest_in_page is None else min(oldest_in_page, ts)
            normalized = _normalize({
                **parsed,
                "signature": item.get("signature"),
                "timestamp": ts,
                "type": (parsed.get("summary") or {}).get("type", "UNKNOWN"),
            }, wallet, cutoff, now)
            if normalized:
                rows[normalized["signature"]] = normalized

        if oldest_in_page is not None and oldest_in_page < cutoff:
            reached_cutoff = True
            break
        next_token = page.get("paginationToken")
        if not next_token:
            exhausted = True
            break
        if next_token == pagination_token:
            raise ValueError("Helius pagination cursor did not advance")
        pagination_token = next_token

    complete = reached_cutoff or exhausted
    return {
        "wallet_address": wallet,
        "transactions": list(rows.values()),
        "pages_fetched": pages,
        "complete": complete,
        "stop_reason": "cutoff_reached" if reached_cutoff else ("history_exhausted" if exhausted else "page_limit_reached"),
        "oldest_observed": min((r["block_time"] for r in rows.values()), default=None),
    }


def initialize_ingestion_schema() -> None:
    from app.adapters.soulwinners import DATABASE_URL
    if not DATABASE_URL:
        return
    import psycopg
    ddl = """
    CREATE TABLE IF NOT EXISTS soulwinners_ingestion_runs (
      id BIGSERIAL PRIMARY KEY, window_start TIMESTAMPTZ NOT NULL, window_end TIMESTAMPTZ NOT NULL,
      source TEXT NOT NULL, wallets_requested INTEGER NOT NULL, wallets_completed INTEGER NOT NULL,
      wallets_failed INTEGER NOT NULL, status TEXT NOT NULL CHECK (status IN ('complete','partial','failed')),
      metadata JSONB NOT NULL DEFAULT '{}'::jsonb, created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
      CHECK (window_end > window_start));
    CREATE TABLE IF NOT EXISTS soulwinners_wallet_transactions (
      wallet_address TEXT NOT NULL, signature TEXT NOT NULL, block_time TIMESTAMPTZ NOT NULL,
      tx_type TEXT NOT NULL, fee_lamports BIGINT NOT NULL DEFAULT 0, raw_json JSONB NOT NULL,
      payload_hash TEXT NOT NULL, ingestion_run_id BIGINT NOT NULL REFERENCES soulwinners_ingestion_runs(id),
      ingested_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP, PRIMARY KEY(wallet_address, signature));
    CREATE INDEX IF NOT EXISTS idx_sw_tx_block_time ON soulwinners_wallet_transactions(block_time);
    CREATE INDEX IF NOT EXISTS idx_sw_tx_wallet_time ON soulwinners_wallet_transactions(wallet_address, block_time DESC);
    """
    with psycopg.connect(DATABASE_URL, connect_timeout=8) as conn:
        with conn.cursor() as cur:
            cur.execute(ddl)

async def run_ingestion(wallets: list[str], days: int = 30) -> dict[str, Any]:
    """Fetch and persist bounded 30-day histories. No fabricated qualification."""
    if not HELIUS_API_KEY:
        return {"status": "not_configured", "message": "HELIUS_API_KEY is missing."}
    if days != 30:
        return {"status": "rejected", "message": "This collector is fixed to a 30-day window."}
    clean_wallets = list(dict.fromkeys(w.strip() for w in wallets if isinstance(w, str) and w.strip()))
    if not clean_wallets or len(clean_wallets) > 100:
        return {"status": "rejected", "message": "Provide 1 to 100 candidate wallet addresses."}

    now_dt = datetime.now(timezone.utc)
    now = int(now_dt.timestamp())
    cutoff_dt = now_dt - timedelta(days=30)
    cutoff = int(cutoff_dt.timestamp())
    sem = asyncio.Semaphore(2)
    async with httpx.AsyncClient(timeout=30) as client:
        async def fetch(wallet: str):
            async with sem:
                return await collect_wallet_history(client, wallet, cutoff, now)
        results = await asyncio.gather(*(fetch(w) for w in clean_wallets), return_exceptions=True)

    successful = [r for r in results if isinstance(r, dict)]
    failures = [{"wallet_address": clean_wallets[i], "error_type": type(r).__name__}
                for i, r in enumerate(results) if isinstance(r, Exception)]
    try:
        import psycopg
        from app.adapters.soulwinners import DATABASE_URL
        if not DATABASE_URL:
            return {"status": "not_configured", "message": "SOULWINNERS_DATABASE_URL is missing; fetched data was not persisted."}
        with psycopg.connect(DATABASE_URL, connect_timeout=8) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """INSERT INTO soulwinners_ingestion_runs
                       (window_start, window_end, source, wallets_requested, wallets_completed, wallets_failed, status, metadata)
                       VALUES (%s,%s,'helius_parsed_events_transaction_history',%s,%s,%s,%s,%s::jsonb)
                       RETURNING id""",
                    (cutoff_dt, now_dt, len(clean_wallets),
                     sum(1 for r in successful if r["complete"]), len(failures),
                     "complete" if len(successful) == len(clean_wallets) and all(r["complete"] for r in successful) else "partial",
                     json.dumps({"failures": failures, "page_limit_per_wallet": MAX_PAGES_PER_WALLET})))
                run_id = cur.fetchone()[0]
                inserted = 0
                for result in successful:
                    for row in result["transactions"]:
                        cur.execute(
                            """INSERT INTO soulwinners_wallet_transactions
                               (wallet_address, signature, block_time, tx_type, fee_lamports, raw_json, payload_hash, ingestion_run_id)
                               VALUES (%s,%s,%s,%s,%s,%s::jsonb,%s,%s)
                               ON CONFLICT (wallet_address, signature) DO UPDATE SET
                                 block_time=EXCLUDED.block_time, tx_type=EXCLUDED.tx_type,
                                 fee_lamports=EXCLUDED.fee_lamports, raw_json=EXCLUDED.raw_json,
                                 payload_hash=EXCLUDED.payload_hash, ingestion_run_id=EXCLUDED.ingestion_run_id""",
                            (row["wallet_address"], row["signature"], row["block_time"], row["tx_type"],
                             row["fee_lamports"], row["raw_json"], row["payload_hash"], run_id))
                        inserted += 1
        complete_wallets = sum(1 for r in successful if r["complete"])
        overall = "complete" if not failures and complete_wallets == len(clean_wallets) else "partial"
        return {
            "status": overall, "run_id": run_id, "window_days": 30,
            "window_start": cutoff_dt.isoformat(), "window_end": now_dt.isoformat(),
            "wallets_requested": len(clean_wallets), "wallets_completed": complete_wallets,
            "wallets_failed": failures, "transactions_upserted": inserted,
            "wallets": [{k: v for k, v in r.items() if k != "transactions"} |
                        {"transactions_fetched": len(r["transactions"])} for r in successful],
            "qualification_updated": False,
            "message": "Raw 30-day Parsed Events history stored. ROI, win rate, BES and qualification remain uncomputed until transaction-level PnL validation is implemented."
        }
    except Exception as exc:
        return {"status": "storage_error", "error_type": type(exc).__name__,
                "wallets_fetched": len(successful),
                "message": "History was fetched but persistence failed; inspect private server logs."}


async def discover_and_ingest_wallets(limit: int = 20) -> dict[str, Any]:
    """Discover candidate wallets from the 30-day GMGN leaderboard, then ingest raw history.

    Leaderboard entries are seeds only; this function never calculates or assigns
    SoulWinners qualification, ROI, win rate, BES, or strategy eligibility.
    """
    bounded_limit = max(1, min(int(limit), 100))
    from app.adapters.solscope import fetch_wallet_leaderboard
    from app.adapters.atlas import _solscope_wallets

    leaderboard = await fetch_wallet_leaderboard("30d")
    if leaderboard.get("status") != "ok":
        return {
            "status": "discovery_unavailable",
            "provider_status": leaderboard.get("status"),
            "candidates_discovered": 0,
            "qualification_updated": False,
            "message": "30-day GMGN leaderboard unavailable; no wallets were ingested."
        }

    pnl = leaderboard.get("pnl_leaderboard", {}).get("payload", {})
    winrate = leaderboard.get("winrate_leaderboard", {}).get("payload", {})
    candidates = _solscope_wallets({"pnl": pnl, "winrate": winrate}, bounded_limit)
    if not candidates:
        return {
            "status": "no_candidates",
            "provider": "GMGN",
            "period": "30d",
            "candidates_discovered": 0,
            "qualification_updated": False,
            "message": "No valid wallet addresses were present in the 30-day leaderboard response."
        }

    result = await run_ingestion(candidates, days=30)
    return {
        **result,
        "discovery_provider": "GMGN",
        "discovery_period": "30d",
        "candidates_discovered": len(candidates),
        "qualification_updated": False,
        "message": "Candidate wallet histories collected from the 30-day leaderboard. Candidates are not qualified; ROI, win rate and BES remain uncomputed."
    }
