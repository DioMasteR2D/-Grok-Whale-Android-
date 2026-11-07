"""Grok Bot strategy gates transcribed from the user's approved reference prompt.

These are integration-layer rules. Upstream SolScope, SoulWinners and Atlas
configuration and source code remain untouched. This module evaluates gates
only; it never submits orders or signs transactions.
"""
from datetime import datetime
from zoneinfo import ZoneInfo

TIMEZONE = "Europe/Athens"
SESSION_START = "13:30"
SESSION_END = "21:30"

STRATEGY = {
    "wallet_ranking": {
        "metric": "BES",
        "keep_top": 10,
        "period_days": 30,
        "min_win_rate": 0.60,
        "min_trades": 15,
        "min_roi": 0.50,
        "archetypes": ["Core Alpha", "Moonshot", "Sniper"],
        "exclude": ["CEX", "market makers", "bridges", "developers"],
    },
    "atlas_entry_gates": {
        "origin_wallet_in_top10": True,
        "min_propagation_score": 0.70,
        "min_following_whales": 2,
        "follow_window_seconds": 300,
        "max_crowding": 0.55,
        "lp_burned_required": True,
        "mint_revoked_required": True,
    },
    "position": {
        "max_portfolio_percent": 0.08,
        "stop_loss_percent": -0.06,
        "exit_when_origin_whale_exits": True,
    },
    "execution": {
        "provider": "Phantom",
        "requires_explicit_wallet_approval": True,
        "current_mode": "paper",
        "live_trading_enabled": False,
    },
}


def session_status(now=None):
    local_now = now.astimezone(ZoneInfo(TIMEZONE)) if now else datetime.now(ZoneInfo(TIMEZONE))
    current = local_now.strftime("%H:%M")
    active = SESSION_START <= current < SESSION_END
    return {
        "active": active,
        "timezone": TIMEZONE,
        "start": SESSION_START,
        "end": SESSION_END,
        "local_time": local_now.isoformat(),
    }


def evaluate_entry(data: dict) -> dict:
    """Evaluate every required gate. Missing evidence fails closed."""
    checks = {
        "origin_wallet_in_top10": data.get("origin_wallet_in_top10") is True,
        "propagation_score": isinstance(data.get("propagation_score"), (int, float))
            and data["propagation_score"] >= 0.70,
        "following_whales_within_5m": isinstance(data.get("following_whales_within_5m"), int)
            and data["following_whales_within_5m"] >= 2,
        "crowding_below_0_55": isinstance(data.get("crowding_score"), (int, float))
            and data["crowding_score"] < 0.55,
        "lp_burned": data.get("lp_burned") is True,
        "mint_revoked": data.get("mint_revoked") is True,
    }
    passed = all(checks.values())
    return {
        "eligible": passed,
        "checks": checks,
        "failed_gates": [name for name, ok in checks.items() if not ok],
        "execution_mode": "paper",
        "live_trading_enabled": False,
        "message": "All Atlas entry gates passed; paper evaluation only." if passed
            else "Entry rejected: one or more mandatory gates failed or lack evidence.",
    }
