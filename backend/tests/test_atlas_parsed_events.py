import asyncio
from app.adapters.atlas import _fetch_one


class FakeResponse:
    status_code = 200
    headers = {}

    def raise_for_status(self):
        pass

    def json(self):
        return {
            "data": [{
                "signature": "sig",
                "parsed": {
                    "blockTime": 2000000000,
                    "fee": 5000,
                    "feePayer": "11111111111111111111111111111111",
                    "slot": 123,
                    "summary": {"type": "swap", "parsedData": {"type": "swap"}},
                    "tokenTransfers": [{
                        "mint": "TokenMint",
                        "rawTokenAmount": "1234500",
                        "decimals": 6,
                        "fromUserAccount": "pool",
                        "toUserAccount": "11111111111111111111111111111111",
                    }],
                    "nativeTransfers": [],
                },
            }],
            "paginationToken": "next",
        }


class FakeClient:
    async def post(self, url, params, json):
        assert url.endswith("/v1/parsed-events/transaction-history")
        assert params == {"api-key": "test-key"}
        assert json["tokenAccounts"] == "balanceChanged"
        return FakeResponse()


def test_atlas_adapter_maps_parsed_events_to_stable_flow_schema(monkeypatch):
    monkeypatch.setattr("app.adapters.atlas.HELIUS_API_KEY", "test-key")
    result = asyncio.run(_fetch_one(FakeClient(), "11111111111111111111111111111111", 25))
    tx = result["transactions"][0]
    assert tx["type"] == "SWAP"
    assert tx["fee_payer"] == "11111111111111111111111111111111"
    assert tx["token_transfers"][0]["tokenAmount"] == 1.2345
    assert result["pagination_token"] == "next"
