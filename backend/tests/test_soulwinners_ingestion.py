import asyncio
import app.adapters.soulwinners_ingestion as ingestion
from app.adapters.soulwinners_ingestion import _normalize, collect_wallet_history


def test_normalize_enforces_exact_30_day_window():
    now = 2_000_000_000
    wallet = "11111111111111111111111111111111"
    tx = {"signature": "sig-a", "timestamp": now - 100, "type": "SWAP"}
    assert _normalize(tx, wallet, now - 200, now)
    assert _normalize(tx, wallet, now - 50, now) is None
    assert _normalize({**tx, "timestamp": now + 1}, wallet, now - 200, now) is None
    assert _normalize({**tx, "timestamp": None}, wallet, now - 200, now) is None


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def raise_for_status(self):
        pass

    def json(self):
        return self.payload


class FakeClient:
    def __init__(self, pages):
        self.pages = pages
        self.calls = []

    async def post(self, url, params, json):
        self.calls.append({"url": url, "params": params.copy(), "json": json.copy()})
        return FakeResponse(self.pages.pop(0))


def parsed(signature, timestamp, tx_type="SWAP"):
    return {
        "signature": signature,
        "parserStatus": "OK",
        "parsed": {
            "blockTime": timestamp,
            "fee": 5000,
            "summary": {"type": tx_type},
            "tokenTransfers": [],
            "nativeTransfers": [],
        },
    }


def test_parsed_events_history_paginates_to_cutoff_and_deduplicates(monkeypatch):
    monkeypatch.setattr(ingestion, "PAGE_SIZE", 2)
    now = 2_000_000_000
    cutoff = now - 100
    wallet = "11111111111111111111111111111111"
    client = FakeClient([
        {"data": [parsed("s1", now - 10), parsed("s2", now - 50)], "paginationToken": "cursor-1"},
        {"data": [parsed("s2", now - 50), parsed("s3", cutoff - 1)], "paginationToken": "cursor-2"},
    ])
    result = asyncio.run(collect_wallet_history(client, wallet, cutoff, now, max_pages=4))
    assert result["complete"] is True
    assert result["stop_reason"] == "cutoff_reached"
    assert len(result["transactions"]) == 2
    assert client.calls[0]["url"] == ingestion.HELIUS_URL
    assert client.calls[0]["json"]["tokenAccounts"] == "balanceChanged"
    assert client.calls[1]["json"]["paginationToken"] == "cursor-1"


def test_parsed_events_empty_page_continues_when_cursor_exists():
    now = 2_000_000_000
    wallet = "11111111111111111111111111111111"
    client = FakeClient([
        {"data": [], "paginationToken": "cursor-1"},
        {"data": [parsed("s1", now - 10)], "paginationToken": None},
    ])
    result = asyncio.run(collect_wallet_history(client, wallet, now - 100, now, max_pages=3))
    assert result["complete"] is True
    assert len(result["transactions"]) == 1
    assert len(client.calls) == 2


def test_page_limit_is_marked_incomplete(monkeypatch):
    monkeypatch.setattr(ingestion, "PAGE_SIZE", 2)
    now = 2_000_000_000
    wallet = "11111111111111111111111111111111"
    client = FakeClient([{
        "data": [parsed("s1", now - 1), parsed("s2", now - 2)],
        "paginationToken": "cursor-1",
    }])
    result = asyncio.run(collect_wallet_history(client, wallet, now - 1000, now, max_pages=1))
    assert result["complete"] is False
    assert result["stop_reason"] == "page_limit_reached"
