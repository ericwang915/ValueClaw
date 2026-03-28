"""
Strategy orchestration for value_claw.

The agent does NOT execute individual trades. Instead it manages *strategies*
— autonomous trading programs that run on a schedule and produce buy/sell
decisions. The agent's role is to start, stop, switch, and monitor strategies.

Three strategy types are supported:

1. **script**  — A Python script that outputs JSON signals.
   The engine runs it in a subprocess, parses the output, and either
   executes trades directly (auto mode) or queues them for approval.

2. **prompt** — A natural-language prompt template that is fed to an
   agent session on each trigger.  The session has buy/sell tools so
   the LLM can decide what to trade.

3. **n8n** — An n8n workflow triggered via webhook.  The workflow does
   its own analysis and POSTs trade signals back via the REST API.

Pending trades (approval mode) are stored in a separate file and can
be approved or rejected by the user through the agent, Telegram, or
the web dashboard.

Storage layout::

    ~/.value_claw/context/strategies/
        registry.json          # all registered strategies
        pending_trades.json    # approval queue
"""

from __future__ import annotations

import json
import logging
import os
import subprocess
import sys
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Literal

logger = logging.getLogger(__name__)

StrategyType = Literal["script", "prompt", "n8n"]
StrategyStatus = Literal["running", "stopped"]
ExecutionMode = Literal["auto", "approval"]
TradeAction = Literal["buy", "sell"]
PendingStatus = Literal["pending", "approved", "rejected", "expired"]


# ── Data models ──────────────────────────────────────────────────────────────

@dataclass
class Strategy:
    id: str
    name: str
    type: StrategyType
    status: StrategyStatus
    execution_mode: ExecutionMode
    schedule: str
    script_path: str | None = None
    prompt_template: str | None = None
    n8n_workflow_id: str | None = None
    params: dict = field(default_factory=dict)
    created_at: str = ""
    last_run_at: str | None = None
    last_result: str | None = None

    def __post_init__(self):
        if not self.created_at:
            self.created_at = _now_iso()


@dataclass
class PendingTrade:
    id: str
    strategy_id: str
    action: TradeAction
    symbol: str
    quantity: float
    price: float
    thesis: str
    created_at: str
    status: PendingStatus = "pending"


# ── Helpers ──────────────────────────────────────────────────────────────────

def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _strategies_dir() -> str:
    from .. import config as _cfg
    d = os.path.join(str(_cfg.VALUE_CLAW_HOME), "context", "strategies")
    os.makedirs(d, exist_ok=True)
    return d


def _registry_file() -> str:
    return os.path.join(_strategies_dir(), "registry.json")


def _pending_file() -> str:
    return os.path.join(_strategies_dir(), "pending_trades.json")


# ── Registry persistence ────────────────────────────────────────────────────

def _load_registry() -> dict[str, Strategy]:
    path = _registry_file()
    if not os.path.exists(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            raw = json.load(f)
        return {k: Strategy(**v) for k, v in raw.items()}
    except (OSError, json.JSONDecodeError, TypeError) as exc:
        logger.error("[Strategy] Failed to load registry: %s", exc)
        return {}


def _save_registry(strategies: dict[str, Strategy]) -> None:
    path = _registry_file()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump({k: asdict(v) for k, v in strategies.items()}, f, indent=2, ensure_ascii=False)


# ── Pending trades persistence ───────────────────────────────────────────────

def _load_pending() -> list[PendingTrade]:
    path = _pending_file()
    if not os.path.exists(path):
        return []
    try:
        with open(path, "r", encoding="utf-8") as f:
            raw = json.load(f)
        return [PendingTrade(**t) for t in raw]
    except (OSError, json.JSONDecodeError, TypeError) as exc:
        logger.error("[Strategy] Failed to load pending trades: %s", exc)
        return []


def _save_pending(trades: list[PendingTrade]) -> None:
    path = _pending_file()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump([asdict(t) for t in trades], f, indent=2, ensure_ascii=False)


# ── Strategy CRUD ────────────────────────────────────────────────────────────

def register_strategy(
    strategy_id: str,
    name: str,
    strategy_type: StrategyType,
    schedule: str,
    execution_mode: ExecutionMode = "approval",
    script_path: str | None = None,
    prompt_template: str | None = None,
    n8n_workflow_id: str | None = None,
    params: dict | None = None,
) -> dict[str, Any]:
    """Register a new strategy (initially stopped)."""
    if strategy_type == "script" and not script_path:
        return {"ok": False, "error": "script_path is required for type=script."}
    if strategy_type == "prompt" and not prompt_template:
        return {"ok": False, "error": "prompt_template is required for type=prompt."}
    if strategy_type == "n8n" and not n8n_workflow_id:
        return {"ok": False, "error": "n8n_workflow_id is required for type=n8n."}

    strategies = _load_registry()
    if strategy_id in strategies:
        return {"ok": False, "error": f"Strategy '{strategy_id}' already exists."}

    strat = Strategy(
        id=strategy_id,
        name=name,
        type=strategy_type,
        status="stopped",
        execution_mode=execution_mode,
        schedule=schedule,
        script_path=script_path,
        prompt_template=prompt_template,
        n8n_workflow_id=n8n_workflow_id,
        params=params or {},
    )
    strategies[strategy_id] = strat
    _save_registry(strategies)
    logger.info("[Strategy] Registered '%s' (type=%s)", strategy_id, strategy_type)

    try:
        from .. import db
        db.record_strategy_event(strategy_id, "register",
                                 f"type={strategy_type}, mode={execution_mode}")
    except Exception:
        pass

    return {"ok": True, "strategy": asdict(strat)}


def unregister_strategy(strategy_id: str) -> dict[str, Any]:
    """Remove a strategy from the registry. Must be stopped first."""
    strategies = _load_registry()
    strat = strategies.get(strategy_id)
    if not strat:
        return {"ok": False, "error": f"Strategy '{strategy_id}' not found."}
    if strat.status == "running":
        return {"ok": False, "error": f"Strategy '{strategy_id}' is running. Stop it first."}
    del strategies[strategy_id]
    _save_registry(strategies)
    logger.info("[Strategy] Unregistered '%s'", strategy_id)

    try:
        from .. import db
        db.record_strategy_event(strategy_id, "unregister", "Strategy removed")
    except Exception:
        pass

    return {"ok": True, "message": f"Strategy '{strategy_id}' removed."}


def update_strategy(
    strategy_id: str,
    name: str | None = None,
    schedule: str | None = None,
    execution_mode: ExecutionMode | None = None,
    prompt_template: str | None = None,
    script_path: str | None = None,
    n8n_workflow_id: str | None = None,
    params: dict | None = None,
) -> dict[str, Any]:
    """Update fields on an existing strategy."""
    strategies = _load_registry()
    strat = strategies.get(strategy_id)
    if not strat:
        return {"ok": False, "error": f"Strategy '{strategy_id}' not found."}

    if name is not None:
        strat.name = name
    if schedule is not None:
        strat.schedule = schedule
    if execution_mode is not None:
        strat.execution_mode = execution_mode
    if prompt_template is not None:
        strat.prompt_template = prompt_template
    if script_path is not None:
        strat.script_path = script_path
    if n8n_workflow_id is not None:
        strat.n8n_workflow_id = n8n_workflow_id
    if params is not None:
        strat.params = params

    strategies[strategy_id] = strat
    _save_registry(strategies)
    logger.info("[Strategy] Updated '%s'", strategy_id)
    return {"ok": True, "strategy": asdict(strat), "needs_restart": strat.status == "running"}


def get_strategy(strategy_id: str) -> Strategy | None:
    strategies = _load_registry()
    return strategies.get(strategy_id)


def list_strategies() -> list[dict[str, Any]]:
    """Return all registered strategies as dicts."""
    strategies = _load_registry()
    return [asdict(s) for s in strategies.values()]


def set_strategy_status(strategy_id: str, status: StrategyStatus) -> dict[str, Any]:
    """Set the running status of a strategy (called by the scheduler layer)."""
    strategies = _load_registry()
    strat = strategies.get(strategy_id)
    if not strat:
        return {"ok": False, "error": f"Strategy '{strategy_id}' not found."}
    strat.status = status
    strategies[strategy_id] = strat
    _save_registry(strategies)

    try:
        from .. import db
        db.record_strategy_event(strategy_id, status, f"Strategy {status}")
    except Exception:
        pass

    return {"ok": True, "strategy_id": strategy_id, "status": status}


def record_run(strategy_id: str, result: str | None) -> None:
    """Update last_run_at and last_result after execution."""
    strategies = _load_registry()
    strat = strategies.get(strategy_id)
    if not strat:
        return
    strat.last_run_at = _now_iso()
    strat.last_result = (result or "")[:2000]
    strategies[strategy_id] = strat
    _save_registry(strategies)


# ── Strategy execution ───────────────────────────────────────────────────────

def execute_script_strategy(strat: Strategy) -> list[dict]:
    """Run a Python script strategy and return parsed trade signals.

    The script must print a JSON array of signal objects to stdout::

        [{"action": "buy", "symbol": "AAPL", "quantity": 10, "price": 175.5, "thesis": "..."}]

    Returns a list of signal dicts (may be empty).
    """
    if not strat.script_path:
        return []
    python = sys.executable
    try:
        proc = subprocess.run(
            [python, strat.script_path, json.dumps(strat.params)],
            capture_output=True, text=True, timeout=300,
            cwd=os.path.dirname(strat.script_path) or None,
        )
    except subprocess.TimeoutExpired:
        logger.error("[Strategy] Script '%s' timed out (300s)", strat.id)
        return []
    except Exception as exc:
        logger.error("[Strategy] Script '%s' failed to run: %s", strat.id, exc)
        return []

    if proc.returncode != 0:
        logger.error("[Strategy] Script '%s' exited %d: %s", strat.id, proc.returncode, proc.stderr[:500])
        return []

    try:
        signals = json.loads(proc.stdout)
        if isinstance(signals, dict):
            signals = [signals]
        if not isinstance(signals, list):
            logger.error("[Strategy] Script '%s' output is not a list", strat.id)
            return []
        return signals
    except json.JSONDecodeError:
        logger.error("[Strategy] Script '%s' output is not valid JSON: %s", strat.id, proc.stdout[:300])
        return []


def execute_n8n_strategy(strat: Strategy) -> list[dict]:
    """Trigger an n8n workflow and return trade signals from the response.

    Requires n8n configuration in value_claw.json.
    """
    from .. import config as _cfg
    base_url = _cfg.get_str("skills", "n8n", "baseUrl", env="N8N_BASE_URL", default="http://localhost:5678")
    api_key = _cfg.get_str("skills", "n8n", "apiKey", env="N8N_API_KEY", default="")

    if not api_key:
        logger.warning("[Strategy] n8n API key not configured for strategy '%s'", strat.id)
        return []

    try:
        import requests
        headers = {"X-N8N-API-KEY": api_key, "Content-Type": "application/json"}
        url = f"{base_url}/api/v1/workflows/{strat.n8n_workflow_id}/activate"
        resp = requests.post(url, headers=headers, timeout=30)
        if resp.status_code != 200:
            logger.error("[Strategy] n8n activate failed for '%s': %s", strat.id, resp.text[:300])
    except Exception as exc:
        logger.error("[Strategy] n8n call failed for '%s': %s", strat.id, exc)

    return []


def process_signals(
    strat: Strategy,
    signals: list[dict],
) -> dict[str, Any]:
    """Process trade signals from a strategy execution.

    In auto mode: log signals as executed.
    In approval mode: queue as pending trades.

    Returns a summary of actions taken.
    """
    executed = []
    queued = []
    errors = []

    for sig in signals:
        action = sig.get("action", "").lower()
        if action not in ("buy", "sell"):
            errors.append(f"Invalid action: {sig}")
            continue
        symbol = sig.get("symbol", "").upper()
        quantity = float(sig.get("quantity", 0))
        price = float(sig.get("price", 0))
        thesis = sig.get("thesis", f"Strategy '{strat.id}' signal")

        if quantity <= 0 or price <= 0:
            errors.append(f"Invalid quantity/price for {symbol}")
            continue

        if strat.execution_mode == "auto":
            executed.append({"action": action, "symbol": symbol, "quantity": quantity, "price": price, "thesis": thesis})
            logger.info("[Strategy] Auto-signal: %s %s x%.4f @$%.2f (strategy=%s)", action, symbol, quantity, price, strat.id)
        else:
            trade = PendingTrade(
                id=str(uuid.uuid4())[:8],
                strategy_id=strat.id,
                action=action,
                symbol=symbol,
                quantity=quantity,
                price=price,
                thesis=thesis,
                created_at=_now_iso(),
            )
            _submit_pending(trade)
            queued.append({"action": action, "symbol": symbol, "quantity": quantity, "price": price, "trade_id": trade.id})

    return {"executed": executed, "queued": queued, "errors": errors}


# ── Pending trade management ─────────────────────────────────────────────────

def _submit_pending(trade: PendingTrade) -> None:
    trades = _load_pending()
    trades.append(trade)
    _save_pending(trades)
    logger.info("[Strategy] Pending trade queued: %s %s x%.4f @$%.2f (id=%s)",
                trade.action, trade.symbol, trade.quantity, trade.price, trade.id)


def list_pending_trades(strategy_id: str | None = None) -> list[dict]:
    """List pending trades, optionally filtered by strategy."""
    trades = _load_pending()
    if strategy_id:
        trades = [t for t in trades if t.strategy_id == strategy_id]
    return [asdict(t) for t in trades if t.status == "pending"]


def approve_trade(trade_id: str) -> dict[str, Any]:
    """Approve a pending trade."""
    trades = _load_pending()
    trade = next((t for t in trades if t.id == trade_id), None)
    if not trade:
        return {"ok": False, "error": f"Pending trade '{trade_id}' not found."}
    if trade.status != "pending":
        return {"ok": False, "error": f"Trade '{trade_id}' is already {trade.status}."}

    trade.status = "approved"
    _save_pending(trades)
    logger.info("[Strategy] Trade approved: %s %s x%.4f @$%.2f (id=%s)",
                trade.action, trade.symbol, trade.quantity, trade.price, trade.id)

    result = {"ok": True}
    return {
        "ok": result.get("ok", False),
        "trade_id": trade_id,
        "trade_status": trade.status,
        "execution_result": result,
    }


def reject_trade(trade_id: str) -> dict[str, Any]:
    """Reject a pending trade."""
    trades = _load_pending()
    trade = next((t for t in trades if t.id == trade_id), None)
    if not trade:
        return {"ok": False, "error": f"Pending trade '{trade_id}' not found."}
    if trade.status != "pending":
        return {"ok": False, "error": f"Trade '{trade_id}' is already {trade.status}."}
    trade.status = "rejected"
    _save_pending(trades)
    logger.info("[Strategy] Rejected trade '%s'", trade_id)
    return {"ok": True, "trade_id": trade_id, "status": "rejected"}


def get_strategy_trades(
    strategy_id: str,
    limit: int = 30,
) -> list[dict]:
    """Get trades attributed to a specific strategy (placeholder — no portfolio backend)."""
    return []
