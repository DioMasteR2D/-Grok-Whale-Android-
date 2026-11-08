from app.main import _is_origin_exit_after_entry


ORIGIN = "11111111111111111111111111111111"
MINT = "So11111111111111111111111111111111111111112"


def _swap(timestamp, source=ORIGIN, mint=MINT):
    return {
        "type": "SWAP",
        "timestamp": timestamp,
        "signature": "sig",
        "tokenTransfers": [{"mint": mint, "fromUserAccount": source}],
    }


def test_origin_swap_after_entry_closes_candidate():
    assert _is_origin_exit_after_entry(
        _swap(1_800_000_100), ORIGIN, MINT, "2027-01-15T08:00:00+00:00"
    )


def test_historical_origin_swap_before_entry_is_ignored():
    assert not _is_origin_exit_after_entry(
        _swap(1_800_000_000), ORIGIN, MINT, "2027-01-15T08:00:00+00:00"
    )


def test_origin_swap_at_entry_second_is_ignored():
    assert not _is_origin_exit_after_entry(
        _swap(1_800_000_000), ORIGIN, MINT, "2027-01-15T08:00:00+00:00"
    )


def test_non_swap_or_wrong_token_outflow_is_ignored():
    tx = _swap(1_800_000_100, mint="EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v")
    assert not _is_origin_exit_after_entry(
        tx, ORIGIN, MINT, "2027-01-15T08:00:00+00:00"
    )
    tx = _swap(1_800_000_100)
    tx["type"] = "TRANSFER"
    assert not _is_origin_exit_after_entry(
        tx, ORIGIN, MINT, "2027-01-15T08:00:00+00:00"
    )


def test_missing_or_invalid_timestamp_fails_closed():
    assert not _is_origin_exit_after_entry(
        _swap(None), ORIGIN, MINT, "2027-01-15T08:00:00+00:00"
    )
    assert not _is_origin_exit_after_entry(
        _swap(1_800_000_100), ORIGIN, MINT, None
    )
