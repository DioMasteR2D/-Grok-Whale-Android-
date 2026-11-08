import asyncio

import app.adapters.solscope as solscope


class FakeResponse:
    status_code = 200

    def __init__(self, payload):
        self.payload = payload
        self.url = None
        self.params = None

    def raise_for_status(self):
        return None

    def json(self):
        return self.payload


class FakeClient:
    def __init__(self, *args, **kwargs):
        self.responses = [
            FakeResponse({"data": {"rank": [{"address": "wallet-a"}]}}),
            FakeResponse({"data": {"rank": [{"address": "wallet-b"}]}}),
        ]
        self.requests = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False

    async def get(self, url, params, headers):
        self.requests.append((url, params, headers))
        return self.responses.pop(0)


def test_gmgn_leaderboard_uses_fixed_provider_and_marks_candidates(monkeypatch):
    client = FakeClient()
    monkeypatch.setattr(solscope.httpx, "AsyncClient", lambda **kwargs: client)

    result = asyncio.run(solscope.fetch_wallet_leaderboard("30d"))

    assert result["status"] == "ok"
    assert result["provider"] == "GMGN"
    assert result["qualification"] == "candidate_discovery_only"
    assert len(client.requests) == 2
    assert all(url.startswith(solscope.GMGN_BASE + "/30d") for url, _, _ in client.requests)
    assert {params["orderby"] for _, params, _ in client.requests} == {"pnl", "winrate"}
    assert all(params["limit"] == "200" for _, params, _ in client.requests)


def test_gmgn_rejects_unsupported_period():
    try:
        asyncio.run(solscope.fetch_wallet_leaderboard("90d"))
    except ValueError as exc:
        assert "period must be" in str(exc)
    else:
        raise AssertionError("unsupported period was accepted")
