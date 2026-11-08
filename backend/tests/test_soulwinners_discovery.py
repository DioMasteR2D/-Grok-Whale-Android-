import asyncio

from app.adapters import soulwinners_ingestion as ingestion


def test_discovery_ingests_only_addresses_from_30d_leaderboard(monkeypatch):
    calls = {}

    async def fake_leaderboard(period):
        calls["period"] = period
        return {
            "status": "ok",
            "pnl_leaderboard": {"payload": {"wallets": [
                {"wallet_address": "11111111111111111111111111111111"}
            ]}},
            "winrate_leaderboard": {"payload": {}},
        }

    async def fake_run(wallets, days):
        calls["wallets"] = wallets
        calls["days"] = days
        return {"status": "partial", "qualification_updated": False}

    monkeypatch.setattr("app.adapters.solscope.fetch_wallet_leaderboard", fake_leaderboard)
    monkeypatch.setattr(ingestion, "run_ingestion", fake_run)

    result = asyncio.run(ingestion.discover_and_ingest_wallets(limit=10))

    assert calls["period"] == "30d"
    assert calls["days"] == 30
    assert calls["wallets"] == ["11111111111111111111111111111111"]
    assert result["discovery_provider"] == "GMGN"
    assert result["qualification_updated"] is False


def test_discovery_fails_closed_when_leaderboard_unavailable(monkeypatch):
    async def fake_leaderboard(period):
        return {"status": "rate_limited"}

    async def fail_if_called(*args, **kwargs):
        raise AssertionError("ingestion must not run without candidates")

    monkeypatch.setattr("app.adapters.solscope.fetch_wallet_leaderboard", fake_leaderboard)
    monkeypatch.setattr(ingestion, "run_ingestion", fail_if_called)

    result = asyncio.run(ingestion.discover_and_ingest_wallets(limit=10))

    assert result["status"] == "discovery_unavailable"
    assert result["candidates_discovered"] == 0
    assert result["qualification_updated"] is False
