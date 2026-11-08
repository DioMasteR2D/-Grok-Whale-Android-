from datetime import datetime, timezone
from app.adapters.soulwinners_ingestion import _normalize, collect_wallet_history
import httpx
import pytest

def test_normalize_enforces_exact_30_day_window():
    now = 2_000_000_000
    wallet = "11111111111111111111111111111111"
    tx = {"signature": "sig-a", "timestamp": now - 100, "type": "SWAP"}
    assert _normalize(tx, wallet, now - 200, now)
    assert _normalize(tx, wallet, now - 50, now) is None
    assert _normalize({**tx, "timestamp": now + 1}, wallet, now - 200, now) is None
    assert _normalize({**tx, "timestamp": None}, wallet, now - 200, now) is None

class FakeResponse:
    def __init__(self, payload): self.payload = payload
    def raise_for_status(self): pass
    def json(self): return self.payload

class FakeClient:
    def __init__(self, pages): self.pages = pages; self.calls = []
    async def get(self, url, params):
        self.calls.append(params.copy())
        return FakeResponse(self.pages.pop(0))

@pytest.mark.asyncio
async def test_history_paginates_until_cutoff_and_deduplicates():
    now = 2_000_000_000
    cutoff = now - 100
    wallet = "11111111111111111111111111111111"
    client = FakeClient([
        [{"signature": "s1", "timestamp": now - 10, "type": "SWAP"},
         {"signature": "s2", "timestamp": now - 50, "type": "SWAP"}],
        [{"signature": "s2", "timestamp": now - 50, "type": "SWAP"},
         {"signature": "s3", "timestamp": cutoff - 1, "type": "SWAP"}],
    ])
    result = await collect_wallet_history(client, wallet, cutoff, now, max_pages=4)
    assert result["complete"] is True
    assert result["stop_reason"] == "cutoff_reached"
    assert len(result["transactions"]) == 2
    assert client.calls[1]["before-signature"] == "s2"

@pytest.mark.asyncio
async def test_page_limit_is_marked_incomplete():
    now = 2_000_000_000
    wallet = "11111111111111111111111111111111"
    page = [{"signature": f"s{i}", "timestamp": now - i, "type": "SWAP"} for i in range(100)]
    client = FakeClient([page])
    result = await collect_wallet_history(client, wallet, now - 1000, now, max_pages=1)
    assert result["complete"] is False
    assert result["stop_reason"] == "page_limit_reached"
