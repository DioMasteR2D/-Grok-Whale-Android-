from app import paper


class FakeCursor:
    def __init__(self, row):
        self.row = row
        self.query = None
        self.params = None

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def execute(self, query, params):
        self.query = query
        self.params = params

    def fetchone(self):
        return self.row


class FakeConnection:
    def __init__(self, row):
        self.cursor_instance = FakeCursor(row)

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def cursor(self):
        return self.cursor_instance


def test_session_summary_returns_measured_session_totals(monkeypatch):
    connection = FakeConnection((25.0, 3.5, -1.0, 4, 3, 2, 2, 2))
    monkeypatch.setattr(paper, "_db", lambda: connection)

    result = paper.session_summary()

    assert result["status"] == "ok"
    assert result["mode"] == "paper"
    assert result["capital_deployed_usd"] == 25.0
    assert result["realized_pnl_usd"] == 3.5
    assert result["unrealized_pnl_usd"] == -1.0
    assert result["total_pnl_usd"] == 2.5
    assert result["trades"] == 4
    assert result["memes"] == 3
    assert result["whales"] == 2
    assert result["closed_positions"] == 2
    assert result["open_positions"] == 2
    assert result["live_trading_enabled"] is False
    assert connection.cursor_instance.params[0].tzinfo is not None
    assert connection.cursor_instance.params[1].tzinfo is not None


def test_session_summary_fails_closed_without_database(monkeypatch):
    monkeypatch.setattr(paper, "_db", lambda: (_ for _ in ()).throw(
        RuntimeError("persistent_database_not_configured")
    ))

    result = paper.session_summary()

    assert result["status"] == "unavailable"
    assert result["live_trading_enabled"] is False
