import asyncio

from app.adapters import soulwinners_ingestion as ingestion


def test_discovery_ingests_only_addresses_from_30d_leaderboard(monkeypatch):
    calls = {}

    async def fake_discover(limit):
        calls["limit"] = limit
        return ["11111111111111111111111111111111"], "dedge_public_top_wallets_15d", ["SolScope unavailable"]

    async def fake_run(wallets, days):
        calls["wallets"] = wallets
        calls["days"] = days
        return {"status": "partial", "qualification_updated": False}

    monkeypatch.setattr("app.adapters.atlas._discover_wallets", fake_discover)
    monkeypatch.setattr(ingestion, "run_ingestion", fake_run)

    result = asyncio.run(ingestion.discover_and_ingest_wallets(limit=10))

    assert calls["limit"] == 10
    assert calls["days"] == 30
    assert calls["wallets"] == ["11111111111111111111111111111111"]
    assert result["discovery_provider"] == "dedge_public_top_wallets_15d"
    assert result["discovery_warnings"] == ["SolScope unavailable"]
    assert result["qualification_updated"] is False


def test_discovery_fails_closed_when_leaderboard_unavailable(monkeypatch):
    async def fake_discover(limit):
        return [], "none", ["SolScope unavailable", "dEdge unavailable"]

    async def fail_if_called(*args, **kwargs):
        raise AssertionError("ingestion must not run without candidates")

    monkeypatch.setattr("app.adapters.atlas._discover_wallets", fake_discover)
    monkeypatch.setattr(ingestion, "run_ingestion", fail_if_called)

    result = asyncio.run(ingestion.discover_and_ingest_wallets(limit=10))

    assert result["status"] == "no_candidates"
    assert result["candidates_discovered"] == 0
    assert result["qualification_updated"] is False
