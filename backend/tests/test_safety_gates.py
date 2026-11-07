from app.strategy import evaluate_entry
from app.adapters.atlas_agent import _validate_alerts


def test_strategy_fails_closed_when_evidence_is_missing():
    result = evaluate_entry({})
    assert result["eligible"] is False
    assert len(result["failed_gates"]) == 6
    assert result["live_trading_enabled"] is False


def test_strategy_passes_only_when_all_six_gates_are_explicitly_met():
    evidence = {
        "origin_wallet_in_top10": True,
        "propagation_score": 0.70,
        "following_whales_within_5m": 2,
        "crowding_score": 0.549,
        "lp_burned": True,
        "mint_revoked": True,
    }
    result = evaluate_entry(evidence)
    assert result["eligible"] is True
    assert result["execution_mode"] == "paper"
    assert result["live_trading_enabled"] is False


def test_crowding_threshold_is_strictly_below_055():
    evidence = {
        "origin_wallet_in_top10": True,
        "propagation_score": 0.70,
        "following_whales_within_5m": 2,
        "crowding_score": 0.55,
        "lp_burned": True,
        "mint_revoked": True,
    }
    result = evaluate_entry(evidence)
    assert result["eligible"] is False
    assert "crowding_below_0_55" in result["failed_gates"]


def test_grok_alert_cannot_claim_unbounded_or_invalid_scores():
    alerts = _validate_alerts([{
        "origin_wallet": "wallet",
        "mint": "mint",
        "propagation_score": 1.5,
        "observed_follow_wallets": -3,
        "crowding_score": -0.1,
        "action": "buy_now",
    }])
    assert alerts[0]["propagation_score"] is None
    assert alerts[0]["observed_follow_wallets"] is None
    assert alerts[0]["crowding_score"] is None
    assert alerts[0]["action"] == "unknown"
    assert alerts[0]["model_generated_unverified"] is True
