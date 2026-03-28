"""
Tests for the PostgreSQL persistence layer (value_claw.db).

Uses SQLite in-memory to avoid requiring a real PostgreSQL instance.
"""

import os
import pytest


@pytest.fixture(autouse=True)
def _isolate(tmp_path, monkeypatch):
    home = str(tmp_path / "vc_home")
    os.makedirs(home, exist_ok=True)
    monkeypatch.setattr("value_claw.config.VALUE_CLAW_HOME", home)


@pytest.fixture
def db_session():
    """Initialize the DB module with an in-memory SQLite database."""
    from value_claw import db
    db._initialized = False
    db._engine = None
    db._SessionLocal = None
    ok = db.init_db("sqlite:///:memory:")
    assert ok is True
    yield db
    db._initialized = False
    db._engine = None
    db._SessionLocal = None


class TestInit:

    def test_no_url_returns_false(self, monkeypatch):
        monkeypatch.delenv("DATABASE_URL", raising=False)
        from value_claw import db
        db._initialized = False
        result = db.init_db("")
        assert result is False
        assert db.is_initialized() is False

    def test_sqlite_in_memory_works(self, db_session):
        assert db_session.is_initialized() is True


class TestRecordTrade:

    def test_record_and_query(self, db_session):
        db_session.record_trade(
            timestamp="2026-03-14T10:00:00+00:00",
            portfolio_id="us-stocks",
            mode="simulate",
            side="buy",
            symbol="AAPL",
            quantity=10,
            price=175.0,
            total_cost=1750.0,
            cash_before=10000.0,
            cash_after=8250.0,
            thesis="Momentum play",
            strategy_id="momentum-us",
        )

        trades = db_session.get_trades_from_db(portfolio_id="us-stocks")
        assert len(trades) == 1
        assert trades[0]["symbol"] == "AAPL"
        assert trades[0]["side"] == "buy"
        assert trades[0]["strategy_id"] == "momentum-us"
        assert trades[0]["quantity"] == 10

    def test_filter_by_strategy(self, db_session):
        db_session.record_trade(
            timestamp="2026-03-14T10:00:00+00:00",
            portfolio_id="us-stocks", mode="simulate", side="buy",
            symbol="AAPL", quantity=10, price=175.0, total_cost=1750.0,
            cash_before=10000.0, cash_after=8250.0, strategy_id="strat-a",
        )
        db_session.record_trade(
            timestamp="2026-03-14T11:00:00+00:00",
            portfolio_id="us-stocks", mode="simulate", side="buy",
            symbol="MSFT", quantity=5, price=400.0, total_cost=2000.0,
            cash_before=8250.0, cash_after=6250.0, strategy_id="strat-b",
        )

        trades_a = db_session.get_trades_from_db(strategy_id="strat-a")
        assert len(trades_a) == 1
        assert trades_a[0]["symbol"] == "AAPL"

        all_trades = db_session.get_trades_from_db()
        assert len(all_trades) == 2


class TestRecordSnapshot:

    def test_record_and_query_daily(self, db_session):
        db_session.record_snapshot(
            timestamp="2026-03-14T10:00:00+00:00",
            portfolio_id="us-stocks",
            mode="simulate",
            total_value=50000.0,
            cash_balance=10000.0,
            holdings_value=40000.0,
            total_cost=35000.0,
            pnl=5000.0,
            positions={"AAPL": {"price": 175.0}},
        )

        daily = db_session.get_daily_values("us-stocks", "simulate", days=30)
        assert len(daily) == 1
        assert daily[0]["total_value"] == 50000.0
        assert daily[0]["pnl"] == 5000.0

    def test_upsert_same_day(self, db_session):
        db_session.record_snapshot(
            timestamp="2026-03-14T08:00:00+00:00",
            portfolio_id="us-stocks", mode="simulate",
            total_value=50000.0, cash_balance=10000.0,
            holdings_value=40000.0, total_cost=35000.0, pnl=5000.0,
        )
        db_session.record_snapshot(
            timestamp="2026-03-14T16:00:00+00:00",
            portfolio_id="us-stocks", mode="simulate",
            total_value=51000.0, cash_balance=10000.0,
            holdings_value=41000.0, total_cost=35000.0, pnl=6000.0,
        )

        daily = db_session.get_daily_values("us-stocks", "simulate", days=30)
        assert len(daily) == 1
        assert daily[0]["total_value"] == 51000.0

    def test_query_snapshots(self, db_session):
        db_session.record_snapshot(
            timestamp="2026-03-14T10:00:00+00:00",
            portfolio_id="us-stocks", mode="simulate",
            total_value=50000.0, cash_balance=10000.0,
            holdings_value=40000.0, total_cost=35000.0, pnl=5000.0,
        )

        snaps = db_session.get_snapshots_from_db("us-stocks", "simulate", days=30)
        assert len(snaps) == 1


class TestPortfolioEvents:

    def test_record_and_query(self, db_session):
        db_session.record_portfolio_event("us-stocks", "simulate", "topup", 10000.0, "Initial deposit")
        db_session.record_portfolio_event("us-stocks", "simulate", "cashout", 2000.0, "Withdrawal")

        events = db_session.get_portfolio_events(portfolio_id="us-stocks")
        assert len(events) == 2
        assert events[0]["event_type"] in ("topup", "cashout")

    def test_filter_by_type(self, db_session):
        db_session.record_portfolio_event("us-stocks", "simulate", "topup", 10000.0)
        db_session.record_portfolio_event("us-stocks", "simulate", "cashout", 2000.0)

        topups = db_session.get_portfolio_events(event_type="topup")
        assert len(topups) == 1


class TestStrategyEvents:

    def test_record_and_query(self, db_session):
        db_session.record_strategy_event("momentum-us", "register", "type=prompt, portfolio=us-stocks")
        db_session.record_strategy_event("momentum-us", "running", "Strategy started")

        events = db_session.get_strategy_events(strategy_id="momentum-us")
        assert len(events) == 2

    def test_all_events(self, db_session):
        db_session.record_strategy_event("strat-a", "register")
        db_session.record_strategy_event("strat-b", "register")

        all_events = db_session.get_strategy_events()
        assert len(all_events) == 2


class TestNoopWithoutInit:
    """All record/query functions should silently no-op when DB is not initialized."""

    def test_record_trade_noop(self):
        from value_claw import db
        db._initialized = False
        db.record_trade(
            timestamp="2026-01-01T00:00:00+00:00",
            portfolio_id="x", mode="y", side="buy", symbol="Z",
            quantity=1, price=1, total_cost=1, cash_before=1, cash_after=0,
        )

    def test_query_returns_empty(self):
        from value_claw import db
        db._initialized = False
        assert db.get_daily_values("x", "y") == []
        assert db.get_trades_from_db() == []
        assert db.get_portfolio_events() == []
        assert db.get_strategy_events() == []
