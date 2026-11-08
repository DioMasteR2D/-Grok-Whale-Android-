from fastapi.testclient import TestClient

from app import main


MINT = "So11111111111111111111111111111111111111112"
LP_MINT = "11111111111111111111111111111111"


def test_paper_buy_rejects_outside_session_before_any_source_or_order(monkeypatch):
    monkeypatch.setattr(main, "session_status", lambda: {"active": False, "timezone": "Europe/Athens"})
    monkeypatch.setattr(main.paper, "buy", lambda *args, **kwargs: (_ for _ in ()).throw(
        AssertionError("paper.buy must not be called")
    ))

    with TestClient(main.app) as client:
        response = client.post("/api/v1/paper/buy", json={
            "mint": MINT, "lp_mint": LP_MINT, "usd": 10
        })

    assert response.status_code == 200
    assert response.json()["status"] == "rejected"
    assert response.json()["reason"] == "outside_strategy_session"
    assert response.json()["live_trading_enabled"] is False


def test_paper_buy_rejects_when_soulwinners_is_unavailable(monkeypatch):
    monkeypatch.setattr(main, "session_status", lambda: {"active": True})
    monkeypatch.setattr(main, "fetch_qualified_wallets", lambda limit: {
        "status": "unavailable", "items": []
    })
    monkeypatch.setattr(main.paper, "buy", lambda *args, **kwargs: (_ for _ in ()).throw(
        AssertionError("paper.buy must not be called")
    ))

    with TestClient(main.app) as client:
        response = client.post("/api/v1/paper/buy", json={
            "mint": MINT, "lp_mint": LP_MINT, "usd": 10
        })

    assert response.status_code == 200
    assert response.json()["status"] == "rejected"
    assert response.json()["reason"] == "soulwinners_unavailable"
    assert response.json()["live_trading_enabled"] is False


def test_paper_buy_rejects_without_measured_qualified_top10(monkeypatch):
    monkeypatch.setattr(main, "session_status", lambda: {"active": True})
    monkeypatch.setattr(main, "fetch_qualified_wallets", lambda limit: {
        "status": "ok", "items": []
    })
    monkeypatch.setattr(main, "_soulwinners_top10", lambda rows: ([], {"returned": 0}))
    monkeypatch.setattr(main.paper, "buy", lambda *args, **kwargs: (_ for _ in ()).throw(
        AssertionError("paper.buy must not be called")
    ))

    with TestClient(main.app) as client:
        response = client.post("/api/v1/paper/buy", json={
            "mint": MINT, "lp_mint": LP_MINT, "usd": 10
        })

    assert response.status_code == 200
    assert response.json()["status"] == "rejected"
    assert response.json()["reason"] == "no_measured_top10_wallets"
    assert response.json()["live_trading_enabled"] is False


def test_paper_buy_requires_explicit_lp_mint_and_valid_base58():
    with TestClient(main.app) as client:
        missing_lp = client.post("/api/v1/paper/buy", json={
            "mint": MINT, "usd": 10
        })
        invalid_mint = client.post("/api/v1/paper/buy", json={
            "mint": "not-a-solana-mint", "lp_mint": LP_MINT, "usd": 10
        })

    assert missing_lp.status_code == 422
    assert invalid_mint.status_code == 422
