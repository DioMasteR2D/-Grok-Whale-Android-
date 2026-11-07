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


from app.analysis import build_atlas_propagation


def test_atlas_propagation_requires_real_swap_evidence_and_three_wallets():
    wallets = [{"wallet_address": f"wallet{i}"} for i in range(3)]
    flows = {"status": "ok", "items": [
        {"wallet_address": "wallet0", "transactions": [
            {"type": "SWAP", "fee_payer": "wallet0", "timestamp": 1000, "signature": "sig0",
             "token_transfers": [{"mint": "mintA", "fromUserAccount": "pool", "toUserAccount": "wallet0", "tokenAmount": 100.0}]}]},
        {"wallet_address": "wallet1", "transactions": [
            {"type": "SWAP", "fee_payer": "wallet1", "timestamp": 1060, "signature": "sig1",
             "token_transfers": [{"mint": "mintA", "fromUserAccount": "pool", "toUserAccount": "wallet1", "tokenAmount": 90.0}]}]},
        {"wallet_address": "wallet2", "transactions": [
            {"type": "SWAP", "fee_payer": "wallet2", "timestamp": 1120, "signature": "sig2",
             "token_transfers": [{"mint": "mintA", "fromUserAccount": "pool", "toUserAccount": "wallet2", "tokenAmount": 80.0}]}]},
    ]}
    result = build_atlas_propagation(flows, wallets)
    assert result["status"] == "ok"
    assert len(result["items"]) == 1
    event = result["items"][0]
    assert event["origin_wallet"] == "wallet0"
    assert event["following_whale_count"] == 2
    assert event["following_lags_seconds"] == [60, 120]
    assert 0 < event["propagation_score"] <= 1
    assert event["evidence_is_onchain_observation"] is True
    assert event["score_is_model_generated"] is False


def test_atlas_propagation_ignores_non_swap_and_unqualified_wallets():
    flows = {"status": "ok", "items": [
        {"wallet_address": "wallet0", "transactions": [
            {"type": "TRANSFER", "timestamp": 1000, "token_transfers": [
                {"mint": "mintA", "fromUserAccount": "pool", "toUserAccount": "wallet0", "tokenAmount": 100}]}]},
        {"wallet_address": "not-qualified", "transactions": [
            {"type": "SWAP", "timestamp": 1010, "token_transfers": [
                {"mint": "mintA", "fromUserAccount": "pool", "toUserAccount": "not-qualified", "tokenAmount": 90}]}]},
    ]}
    result = build_atlas_propagation(flows, [{"wallet_address": "wallet0"}])
    assert result["items"] == []


def test_atlas_propagation_requires_fee_payer_wallet_identity():
    wallets = [{"wallet_address": f"wallet{i}"} for i in range(3)]
    flows = {"status": "ok", "items": [
        {"wallet_address": f"wallet{i}", "transactions": [
            {"type": "SWAP", "fee_payer": "someone-else", "timestamp": 1000+i*10,
             "token_transfers": [{"mint": "mintB", "fromUserAccount": "pool",
                                  "toUserAccount": f"wallet{i}", "tokenAmount": 100}]}
        ]} for i in range(3)
    ]}
    assert build_atlas_propagation(flows, wallets)["items"] == []
