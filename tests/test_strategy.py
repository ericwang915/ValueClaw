"""
Tests for strategy orchestration layer.

Covers:
- Strategy registration / unregistration / update
- Strategy status lifecycle (stopped → running → stopped)
- Pending trade approval / rejection
- Script strategy signal processing
- Trade attribution (strategy_id on trades)
"""

import json
import os
import pytest
from unittest.mock import patch


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def _isolate_dirs(tmp_path, monkeypatch):
    """Redirect all file-based storage to tmp_path."""
    home = str(tmp_path / "value_claw_home")
    os.makedirs(home, exist_ok=True)
    monkeypatch.setattr("value_claw.config.VALUE_CLAW_HOME", home)


# ── Registration ──────────────────────────────────────────────────────────────

class TestRegistration:

    def test_register_prompt_strategy(self):
        from value_claw.core.strategy import register_strategy, list_strategies
        result = register_strategy(
            strategy_id="momentum-us",
            name="US Momentum",
            strategy_type="prompt",
            portfolio_id="us-stocks",
            schedule="0 9 * * 1-5",
            execution_mode="auto",
            prompt_template="Check RSI/MACD for top holdings and rebalance.",
        )
        assert result["ok"] is True
        assert result["strategy"]["id"] == "momentum-us"
        assert result["strategy"]["status"] == "stopped"

        strategies = list_strategies()
        assert len(strategies) == 1
        assert strategies[0]["type"] == "prompt"

    def test_register_script_strategy(self):
        from value_claw.core.strategy import register_strategy
        result = register_strategy(
            strategy_id="quant-alpha",
            name="Quant Alpha",
            strategy_type="script",
            portfolio_id="us-stocks",
            schedule="30 9 * * 1-5",
            script_path="/path/to/alpha.py",
        )
        assert result["ok"] is True

    def test_register_n8n_strategy(self):
        from value_claw.core.strategy import register_strategy
        result = register_strategy(
            strategy_id="n8n-flow",
            name="n8n Trading Flow",
            strategy_type="n8n",
            portfolio_id="crypto",
            schedule="0 */4 * * *",
            n8n_workflow_id="wf-123",
        )
        assert result["ok"] is True

    def test_reject_duplicate_id(self):
        from value_claw.core.strategy import register_strategy
        register_strategy(
            strategy_id="test-dup",
            name="Test",
            strategy_type="prompt",
            portfolio_id="us-stocks",
            schedule="0 9 * * *",
            prompt_template="test",
        )
        result = register_strategy(
            strategy_id="test-dup",
            name="Test 2",
            strategy_type="prompt",
            portfolio_id="us-stocks",
            schedule="0 9 * * *",
            prompt_template="test2",
        )
        assert result["ok"] is False
        assert "already exists" in result["error"]

    def test_reject_script_without_path(self):
        from value_claw.core.strategy import register_strategy
        result = register_strategy(
            strategy_id="bad-script",
            name="Bad Script",
            strategy_type="script",
            portfolio_id="us-stocks",
            schedule="0 9 * * *",
        )
        assert result["ok"] is False
        assert "script_path" in result["error"]

    def test_reject_invalid_portfolio(self):
        from value_claw.core.strategy import register_strategy
        result = register_strategy(
            strategy_id="bad-port",
            name="Bad Portfolio",
            strategy_type="prompt",
            portfolio_id="nonexistent",
            schedule="0 9 * * *",
            prompt_template="test",
        )
        assert result["ok"] is False


# ── Lifecycle ─────────────────────────────────────────────────────────────────

class TestLifecycle:

    def _create_strategy(self):
        from value_claw.core.strategy import register_strategy
        register_strategy(
            strategy_id="lifecycle-test",
            name="Lifecycle",
            strategy_type="prompt",
            portfolio_id="us-stocks",
            schedule="0 9 * * *",
            prompt_template="test",
        )

    def test_status_transitions(self):
        from value_claw.core.strategy import get_strategy, set_strategy_status
        self._create_strategy()

        strat = get_strategy("lifecycle-test")
        assert strat.status == "stopped"

        set_strategy_status("lifecycle-test", "running")
        strat = get_strategy("lifecycle-test")
        assert strat.status == "running"

        set_strategy_status("lifecycle-test", "stopped")
        strat = get_strategy("lifecycle-test")
        assert strat.status == "stopped"

    def test_unregister_stopped(self):
        from value_claw.core.strategy import unregister_strategy, list_strategies
        self._create_strategy()
        result = unregister_strategy("lifecycle-test")
        assert result["ok"] is True
        assert len(list_strategies()) == 0

    def test_cannot_unregister_running(self):
        from value_claw.core.strategy import set_strategy_status, unregister_strategy
        self._create_strategy()
        set_strategy_status("lifecycle-test", "running")
        result = unregister_strategy("lifecycle-test")
        assert result["ok"] is False
        assert "running" in result["error"].lower()

    def test_update_strategy(self):
        from value_claw.core.strategy import get_strategy, update_strategy
        self._create_strategy()
        result = update_strategy("lifecycle-test", schedule="30 10 * * 1-5", execution_mode="auto")
        assert result["ok"] is True
        strat = get_strategy("lifecycle-test")
        assert strat.schedule == "30 10 * * 1-5"
        assert strat.execution_mode == "auto"

    def test_record_run(self):
        from value_claw.core.strategy import get_strategy, record_run
        self._create_strategy()
        record_run("lifecycle-test", "Executed 3 trades")
        strat = get_strategy("lifecycle-test")
        assert strat.last_run_at is not None
        assert "3 trades" in strat.last_result


# ── Pending trades ────────────────────────────────────────────────────────────

class TestPendingTrades:

    def _setup(self):
        from value_claw.core.strategy import register_strategy
        from value_claw.core import portfolio
        register_strategy(
            strategy_id="approval-strat",
            name="Approval Strategy",
            strategy_type="prompt",
            portfolio_id="us-stocks",
            schedule="0 9 * * *",
            execution_mode="approval",
            prompt_template="test",
        )
        portfolio.top_up(100000.0)

    def test_submit_and_list_pending(self):
        from value_claw.core.strategy import PendingTrade, _submit_pending, list_pending_trades, _now_iso
        self._setup()

        trade = PendingTrade(
            id="t001",
            strategy_id="approval-strat",
            action="buy",
            symbol="AAPL",
            quantity=10,
            price=175.0,
            thesis="Momentum signal",
            created_at=_now_iso(),
        )
        _submit_pending(trade)

        pending = list_pending_trades()
        assert len(pending) == 1
        assert pending[0]["symbol"] == "AAPL"

    def test_approve_trade(self):
        from value_claw.core.strategy import PendingTrade, _submit_pending, approve_trade, list_pending_trades, _now_iso
        self._setup()

        trade = PendingTrade(
            id="t002",
            strategy_id="approval-strat",
            action="buy",
            symbol="AAPL",
            quantity=5,
            price=175.0,
            thesis="Test buy",
            created_at=_now_iso(),
        )
        _submit_pending(trade)

        result = approve_trade("t002")
        assert result["ok"] is True
        assert result["trade_status"] == "approved"

        pending = list_pending_trades()
        assert len(pending) == 0

    def test_reject_trade(self):
        from value_claw.core.strategy import PendingTrade, _submit_pending, reject_trade, list_pending_trades, _now_iso
        self._setup()

        trade = PendingTrade(
            id="t003",
            strategy_id="approval-strat",
            action="buy",
            symbol="MSFT",
            quantity=10,
            price=400.0,
            thesis="Test reject",
            created_at=_now_iso(),
        )
        _submit_pending(trade)

        result = reject_trade("t003")
        assert result["ok"] is True
        assert result["status"] == "rejected"

        pending = list_pending_trades()
        assert len(pending) == 0

    def test_approve_nonexistent(self):
        from value_claw.core.strategy import approve_trade
        result = approve_trade("nope")
        assert result["ok"] is False


# ── Signal processing ─────────────────────────────────────────────────────────

class TestSignalProcessing:

    def _setup_auto_strategy(self):
        from value_claw.core.strategy import register_strategy, get_strategy
        from value_claw.core import portfolio
        register_strategy(
            strategy_id="auto-strat",
            name="Auto Trader",
            strategy_type="script",
            portfolio_id="us-stocks",
            schedule="0 9 * * *",
            execution_mode="auto",
            script_path="/dummy.py",
        )
        portfolio.top_up(50000.0)
        return get_strategy("auto-strat")

    def test_auto_execute_signals(self):
        from value_claw.core.strategy import process_signals
        strat = self._setup_auto_strategy()
        signals = [
            {"action": "buy", "symbol": "AAPL", "quantity": 10, "price": 175.0, "thesis": "momentum"},
        ]
        result = process_signals(strat, signals)
        assert len(result["executed"]) == 1
        assert result["executed"][0]["symbol"] == "AAPL"
        assert len(result["errors"]) == 0

    def test_approval_queues_signals(self):
        from value_claw.core.strategy import register_strategy, get_strategy, process_signals, list_pending_trades
        from value_claw.core import portfolio
        register_strategy(
            strategy_id="queue-strat",
            name="Queue Trader",
            strategy_type="script",
            portfolio_id="us-stocks",
            schedule="0 9 * * *",
            execution_mode="approval",
            script_path="/dummy.py",
        )
        portfolio.top_up(50000.0)
        strat = get_strategy("queue-strat")

        signals = [
            {"action": "buy", "symbol": "NVDA", "quantity": 5, "price": 800.0, "thesis": "AI momentum"},
        ]
        result = process_signals(strat, signals)
        assert len(result["queued"]) == 1
        assert len(list_pending_trades()) == 1

    def test_invalid_signals_produce_errors(self):
        from value_claw.core.strategy import process_signals
        strat = self._setup_auto_strategy()
        signals = [
            {"action": "hold", "symbol": "AAPL", "quantity": 10, "price": 175.0},
            {"action": "buy", "symbol": "AAPL", "quantity": -5, "price": 175.0},
        ]
        result = process_signals(strat, signals)
        assert len(result["errors"]) == 2
        assert len(result["executed"]) == 0


# ── Trade attribution ─────────────────────────────────────────────────────────

class TestTradeAttribution:

    def test_strategy_id_on_trade(self):
        from value_claw.core.strategy import process_signals, register_strategy, get_strategy, get_strategy_trades
        from value_claw.core import portfolio

        register_strategy(
            strategy_id="attr-strat",
            name="Attribution Test",
            strategy_type="script",
            portfolio_id="us-stocks",
            schedule="0 9 * * *",
            execution_mode="auto",
            script_path="/dummy.py",
        )
        portfolio.top_up(50000.0)
        strat = get_strategy("attr-strat")

        process_signals(strat, [
            {"action": "buy", "symbol": "AAPL", "quantity": 5, "price": 175.0, "thesis": "test"},
        ])

        trades = get_strategy_trades("attr-strat")
        assert len(trades) >= 1
        assert trades[0]["strategy_id"] == "attr-strat"
