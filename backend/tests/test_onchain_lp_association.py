import asyncio
import base64

from app.adapters import onchain


def test_arbitrary_zero_supply_lp_mint_cannot_pass_burn_gate(monkeypatch):
    calls = []

    async def fake_rpc(method, params):
        calls.append(method)
        if method == "getAccountInfo":
            raw = bytearray(82)
            raw[0:4] = (0).to_bytes(4, "little")
            raw[46:50] = (0).to_bytes(4, "little")
            return {"value": {"data": [base64.b64encode(raw).decode(), "base64"]}}, None
        if method == "getTokenSupply":
            return {"value": {"amount": "0", "decimals": 0}}, None
        raise AssertionError(method)

    monkeypatch.setattr(onchain, "_rpc", fake_rpc)
    result = asyncio.run(onchain.verify_token(
        "So11111111111111111111111111111111111111112",
        "11111111111111111111111111111111",
    ))

    assert result["checks"]["mint_revoked"] is True
    assert result["checks"]["lp_burned"] is False
    assert result["status"] == "checks_failed_or_incomplete"
    assert result["evidence"]["lp"]["reason"] == "pool_lp_mint_association_not_verified"
    assert "getTokenSupply" not in calls
