"""
Portfolio management for value_claw.

Two fixed portfolios: US Stocks and Crypto (BTC + ETH).
Each portfolio has a fixed allowed-symbols list (stocks only, no options).
The agent can only rebalance within those symbols.
Each portfolio has two tracks: live (real trading) and simulate (paper trading).
Only one portfolio is active at a time; mode can be switched between live/simulate.

Core accounting rules (like a real PM):
  - buy() deducts cash, adds/accumulates holding, logs trade
  - sell() adds cash, reduces/removes holding, logs trade
  - Every trade is recorded in a persistent trade ledger for audit

Risk management:
  - Max single-position size (default 25% of portfolio value)
  - Insufficient-cash guard on buys
  - Options contracts rejected

Performance analytics:
  - Total return, P&L, cost basis tracking
  - Sharpe ratio, max drawdown from snapshot history
  - Benchmark comparison (SPY for us-stocks, BTC-USD for crypto)

Storage: ~/.value_claw/context/portfolios/state.json
Snapshots: ~/.value_claw/context/portfolios/snapshots/{portfolio_id}_{mode}.json
Trades: ~/.value_claw/context/portfolios/trades/{portfolio_id}_{mode}.jsonl
"""

from __future__ import annotations

import json
import logging
import math
import os
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Literal

logger = logging.getLogger(__name__)

Mode = Literal["live", "simulate"]
PortfolioId = Literal["us-stocks", "crypto"]


PORTFOLIO_DEFS: dict[str, dict[str, Any]] = {
    "us-stocks": {"name": "US Stocks", "currency": "USD"},
    "crypto": {"name": "Crypto", "currency": "USD"},
}

BENCHMARK: dict[str, str] = {
    "us-stocks": "SPY",
    "crypto": "BTC-USD",
}


# ── Data models ───────────────────────────────────────────────────────────────

@dataclass
class Holding:
    symbol: str
    quantity: float
    cost_basis: float
    added_at: str = ""

    def __post_init__(self):
        self.symbol = self.symbol.upper()
        if not self.added_at:
            self.added_at = _now_iso()


@dataclass
class Track:
    """One mode (live or simulate) within a portfolio."""
    cash_balance: float = 0.0
    holdings: list[Holding] = field(default_factory=list)
    updated_at: str = ""


@dataclass
class Portfolio:
    id: str
    name: str
    currency: str
    live: Track = field(default_factory=Track)
    simulate: Track = field(default_factory=Track)
    created_at: str = ""

    def __post_init__(self):
        if not self.created_at:
            self.created_at = _now_iso()

    def track(self, mode: Mode) -> Track:
        return self.live if mode == "live" else self.simulate


@dataclass
class Snapshot:
    timestamp: str
    total_value: float
    cash_balance: float
    holdings_value: float
    total_cost: float
    pnl: float
    positions: dict[str, dict]


@dataclass
class Trade:
    """Immutable record of a single buy or sell execution."""
    timestamp: str
    portfolio_id: str
    mode: str
    side: str            # "buy" or "sell"
    symbol: str
    quantity: float
    price: float
    total_cost: float    # quantity * price
    cash_before: float
    cash_after: float
    thesis: str = ""     # investment thesis / reason
    strategy_id: str = ""  # which strategy generated this trade (empty = manual)


@dataclass
class State:
    active_portfolio: PortfolioId = "us-stocks"
    active_mode: Mode = "simulate"
    portfolios: dict[str, Portfolio] = field(default_factory=dict)

    def __post_init__(self):
        for pid, pdef in PORTFOLIO_DEFS.items():
            if pid not in self.portfolios:
                self.portfolios[pid] = Portfolio(id=pid, name=pdef["name"], currency=pdef["currency"])


# ── Helpers ───────────────────────────────────────────────────────────────────

def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _data_dir() -> str:
    from .. import config as _cfg
    d = os.path.join(str(_cfg.VALUE_CLAW_HOME), "context", "portfolios")
    os.makedirs(d, exist_ok=True)
    return d


def _state_file() -> str:
    return os.path.join(_data_dir(), "state.json")


def _snapshots_dir() -> str:
    d = os.path.join(_data_dir(), "snapshots")
    os.makedirs(d, exist_ok=True)
    return d


def _snapshot_file(portfolio_id: str, mode: Mode) -> str:
    return os.path.join(_snapshots_dir(), f"{portfolio_id}_{mode}.json")


def _trades_dir() -> str:
    d = os.path.join(_data_dir(), "trades")
    os.makedirs(d, exist_ok=True)
    return d


def _trades_file(portfolio_id: str, mode: Mode) -> str:
    return os.path.join(_trades_dir(), f"{portfolio_id}_{mode}.jsonl")


def _log_trade(trade: Trade) -> None:
    """Append a trade record to the JSONL ledger and PostgreSQL."""
    path = _trades_file(trade.portfolio_id, trade.mode)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(asdict(trade), ensure_ascii=False) + "\n")

    try:
        from .. import db
        db.record_trade(
            timestamp=trade.timestamp,
            portfolio_id=trade.portfolio_id,
            mode=trade.mode,
            side=trade.side,
            symbol=trade.symbol,
            quantity=trade.quantity,
            price=trade.price,
            total_cost=trade.total_cost,
            cash_before=trade.cash_before,
            cash_after=trade.cash_after,
            thesis=trade.thesis,
            strategy_id=trade.strategy_id,
        )
    except Exception:
        pass


def get_trades(
    portfolio_id: str | None = None,
    mode: Mode | None = None,
    limit: int = 50,
) -> list[dict]:
    """Return recent trades from the ledger (newest first)."""
    state = _load_state()
    pid = portfolio_id or state.active_portfolio
    m = mode or state.active_mode
    path = _trades_file(pid, m)
    if not os.path.exists(path):
        return []
    trades = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                trades.append(json.loads(line))
    return list(reversed(trades[-limit:]))


# ── Persistence ───────────────────────────────────────────────────────────────

def _load_state() -> State:
    path = _state_file()
    if not os.path.exists(path):
        state = State()
        _save_state(state)
        return state
    try:
        with open(path, "r", encoding="utf-8") as f:
            raw = json.load(f)
    except (OSError, json.JSONDecodeError) as exc:
        logger.error("[Portfolio] Failed to load state: %s", exc)
        return State()

    state = State(
        active_portfolio=raw.get("active_portfolio", "us-stocks"),
        active_mode=raw.get("active_mode", "simulate"),
    )
    for pid in PORTFOLIO_DEFS:
        praw = raw.get("portfolios", {}).get(pid, {})
        p = Portfolio(
            id=pid,
            name=PORTFOLIO_DEFS[pid]["name"],
            currency=PORTFOLIO_DEFS[pid]["currency"],
            created_at=praw.get("created_at", _now_iso()),
        )
        for mode_name in ("live", "simulate"):
            traw = praw.get(mode_name, {})
            track = Track(
                cash_balance=traw.get("cash_balance", 0.0),
                holdings=[Holding(**h) for h in traw.get("holdings", [])],
                updated_at=traw.get("updated_at", ""),
            )
            if mode_name == "live":
                p.live = track
            else:
                p.simulate = track
        state.portfolios[pid] = p
    return state


def _save_state(state: State) -> None:
    data: dict[str, Any] = {
        "active_portfolio": state.active_portfolio,
        "active_mode": state.active_mode,
        "portfolios": {},
    }
    for pid, p in state.portfolios.items():
        data["portfolios"][pid] = {
            "created_at": p.created_at,
            "live": {
                "cash_balance": p.live.cash_balance,
                "holdings": [asdict(h) for h in p.live.holdings],
                "updated_at": p.live.updated_at,
            },
            "simulate": {
                "cash_balance": p.simulate.cash_balance,
                "holdings": [asdict(h) for h in p.simulate.holdings],
                "updated_at": p.simulate.updated_at,
            },
        }
    path = _state_file()
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def _load_snapshots(portfolio_id: str, mode: Mode) -> list[Snapshot]:
    path = _snapshot_file(portfolio_id, mode)
    if not os.path.exists(path):
        return []
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return [Snapshot(**s) for s in data.get("snapshots", [])]
    except (OSError, json.JSONDecodeError):
        return []


def _save_snapshots(portfolio_id: str, mode: Mode, snapshots: list[Snapshot]) -> None:
    path = _snapshot_file(portfolio_id, mode)
    data = {"snapshots": [asdict(s) for s in snapshots]}
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


# ── Price fetching ────────────────────────────────────────────────────────────

_price_cache: dict[str, tuple[float, float]] = {}
_CACHE_TTL = 60


def fetch_prices(symbols: list[str]) -> dict[str, float | None]:
    """Fetch current prices via yfinance. Returns {symbol: price}."""
    now = time.time()
    result: dict[str, float | None] = {}
    to_fetch: list[str] = []

    for sym in symbols:
        sym = sym.upper()
        if sym in _price_cache:
            cached_price, cached_time = _price_cache[sym]
            if now - cached_time < _CACHE_TTL:
                result[sym] = cached_price
                continue
        to_fetch.append(sym)

    if to_fetch:
        try:
            import yfinance as yf
            tickers = yf.Tickers(" ".join(to_fetch))
            for sym in to_fetch:
                try:
                    info = tickers.tickers[sym].fast_info
                    price = info.get("lastPrice") or info.get("last_price")
                    if price and price == price:
                        result[sym] = round(float(price), 4)
                        _price_cache[sym] = (result[sym], now)
                    else:
                        result[sym] = None
                except Exception:
                    result[sym] = None
        except ImportError:
            logger.warning("[Portfolio] yfinance not installed")
            for sym in to_fetch:
                result[sym] = None
        except Exception as exc:
            logger.warning("[Portfolio] Price fetch error: %s", exc)
            for sym in to_fetch:
                result.setdefault(sym, None)

    return result


# ── State queries ─────────────────────────────────────────────────────────────

def get_status() -> dict[str, Any]:
    """Return global portfolio status: active portfolio, mode, summaries."""
    state = _load_state()
    result: dict[str, Any] = {
        "active_portfolio": state.active_portfolio,
        "active_mode": state.active_mode,
        "portfolios": {},
    }
    for pid, p in state.portfolios.items():
        pinfo: dict[str, Any] = {
            "name": p.name,
            "currency": p.currency,
            "tracks": {},
        }
        for mode_name in ("live", "simulate"):
            t = p.track(mode_name)
            total_cost = sum(h.quantity * h.cost_basis for h in t.holdings)
            pinfo["tracks"][mode_name] = {
                "cash_balance": round(t.cash_balance, 2),
                "holdings_count": len(t.holdings),
                "total_cost": round(total_cost, 2),
                "updated_at": t.updated_at,
            }
        result["portfolios"][pid] = pinfo
    return result


def get_portfolio_detail(portfolio_id: str, mode: Mode | None = None) -> dict[str, Any] | None:
    """Get portfolio detail with live prices for a specific mode."""
    state = _load_state()
    if portfolio_id not in state.portfolios:
        return None
    p = state.portfolios[portfolio_id]
    if mode is None:
        mode = state.active_mode

    t = p.track(mode)
    symbols = [h.symbol for h in t.holdings]
    prices = fetch_prices(symbols) if symbols else {}

    positions = []
    holdings_value = 0.0
    total_cost = 0.0

    for h in t.holdings:
        price = prices.get(h.symbol)
        mkt_val = h.quantity * price if price else None
        cost_val = h.quantity * h.cost_basis
        pnl = (mkt_val - cost_val) if mkt_val is not None else None
        pnl_pct = (pnl / cost_val * 100) if pnl is not None and cost_val else None

        if mkt_val is not None:
            holdings_value += mkt_val
        total_cost += cost_val

        positions.append({
            "symbol": h.symbol,
            "quantity": h.quantity,
            "cost_basis": h.cost_basis,
            "current_price": price,
            "market_value": round(mkt_val, 2) if mkt_val is not None else None,
            "pnl": round(pnl, 2) if pnl is not None else None,
            "pnl_pct": round(pnl_pct, 2) if pnl_pct is not None else None,
            "added_at": h.added_at,
        })

    total_value = t.cash_balance + holdings_value
    total_pnl = total_value - total_cost - t.cash_balance if holdings_value else None

    return {
        "id": portfolio_id,
        "name": p.name,
        "currency": p.currency,
        "mode": mode,
        "cash_balance": round(t.cash_balance, 2),
        "positions": positions,
        "holdings_value": round(holdings_value, 2),
        "total_value": round(total_value, 2),
        "total_cost": round(total_cost, 2),
        "total_pnl": round(total_pnl, 2) if total_pnl is not None else None,
        "total_pnl_pct": round(total_pnl / total_cost * 100, 2) if total_pnl and total_cost else None,
        "updated_at": t.updated_at,
    }


# ── State mutations ───────────────────────────────────────────────────────────

def switch_portfolio(portfolio_id: str) -> dict[str, Any]:
    """Switch the active portfolio. Returns new status."""
    if portfolio_id not in PORTFOLIO_DEFS:
        return {"ok": False, "error": f"Invalid portfolio. Choose from: {', '.join(PORTFOLIO_DEFS)}"}
    state = _load_state()
    state.active_portfolio = portfolio_id
    _save_state(state)
    logger.info("[Portfolio] Switched active portfolio to '%s'", portfolio_id)
    return {"ok": True, "active_portfolio": portfolio_id, "active_mode": state.active_mode}


def switch_mode(mode: str) -> dict[str, Any]:
    """Switch between live and simulate mode."""
    if mode not in ("live", "simulate"):
        return {"ok": False, "error": "Mode must be 'live' or 'simulate'."}
    state = _load_state()
    state.active_mode = mode
    _save_state(state)
    logger.info("[Portfolio] Switched mode to '%s'", mode)
    return {"ok": True, "active_portfolio": state.active_portfolio, "active_mode": mode}


def top_up(amount: float, portfolio_id: str | None = None, mode: Mode | None = None) -> dict[str, Any]:
    """Add cash to a portfolio track."""
    if amount <= 0:
        return {"ok": False, "error": "Amount must be positive."}
    state = _load_state()
    pid = portfolio_id or state.active_portfolio
    m = mode or state.active_mode
    if pid not in state.portfolios:
        return {"ok": False, "error": f"Portfolio '{pid}' not found."}

    t = state.portfolios[pid].track(m)
    t.cash_balance += amount
    t.updated_at = _now_iso()
    _save_state(state)
    logger.info("[Portfolio] Top up $%.2f to %s/%s. Balance: $%.2f", amount, pid, m, t.cash_balance)

    try:
        from .. import db
        db.record_portfolio_event(pid, m, "topup", amount, f"Balance: ${t.cash_balance:.2f}")
    except Exception:
        pass

    return {"ok": True, "portfolio": pid, "mode": m, "cash_balance": round(t.cash_balance, 2)}


def cash_out(amount: float, portfolio_id: str | None = None, mode: Mode | None = None) -> dict[str, Any]:
    """Withdraw cash from a portfolio track."""
    if amount <= 0:
        return {"ok": False, "error": "Amount must be positive."}
    state = _load_state()
    pid = portfolio_id or state.active_portfolio
    m = mode or state.active_mode
    if pid not in state.portfolios:
        return {"ok": False, "error": f"Portfolio '{pid}' not found."}

    t = state.portfolios[pid].track(m)
    if amount > t.cash_balance:
        return {"ok": False, "error": f"Insufficient cash. Available: ${t.cash_balance:.2f}"}
    t.cash_balance -= amount
    t.updated_at = _now_iso()
    _save_state(state)
    logger.info("[Portfolio] Cash out $%.2f from %s/%s. Balance: $%.2f", amount, pid, m, t.cash_balance)

    try:
        from .. import db
        db.record_portfolio_event(pid, m, "cashout", amount, f"Balance: ${t.cash_balance:.2f}")
    except Exception:
        pass

    return {"ok": True, "portfolio": pid, "mode": m, "cash_balance": round(t.cash_balance, 2)}


def _looks_like_option(symbol: str) -> bool:
    """Reject symbols that look like options contracts (e.g. AAPL230120C00150000)."""
    import re
    if re.match(r'^[A-Z]{1,6}\d{6}[CP]\d{8}$', symbol):
        return True
    if re.search(r'\d{2,}[CP]\d', symbol):
        return True
    return False


# ── Risk management helpers ───────────────────────────────────────────────────

def _max_position_pct() -> float:
    """Max single-position size as % of total portfolio value."""
    try:
        from .. import config as _cfg
        return float(_cfg.get("portfolio", "maxPositionPct", default=25))
    except Exception:
        return 25.0


def _check_buy_risk(
    state: State, pid: str, mode: Mode,
    symbol: str, quantity: float, price: float,
) -> str | None:
    """Pre-trade risk check. Returns error message or None if OK."""
    t = state.portfolios[pid].track(mode)
    trade_value = quantity * price

    if trade_value > t.cash_balance:
        return (
            f"Insufficient cash. Trade costs ${trade_value:,.2f} "
            f"but only ${t.cash_balance:,.2f} available."
        )

    symbols = [h.symbol for h in t.holdings]
    if symbols:
        prices = fetch_prices(symbols)
        holdings_value = sum(
            h.quantity * (prices.get(h.symbol) or h.cost_basis)
            for h in t.holdings
        )
    else:
        holdings_value = 0.0

    total_value = t.cash_balance + holdings_value
    if total_value <= 0:
        return None

    existing = next((h for h in t.holdings if h.symbol == symbol), None)
    new_position_value = trade_value
    if existing:
        existing_price = fetch_prices([symbol]).get(symbol) or existing.cost_basis
        new_position_value += existing.quantity * existing_price

    max_pct = _max_position_pct()
    position_pct = (new_position_value / total_value) * 100
    if position_pct > max_pct:
        return (
            f"Position size {position_pct:.1f}% would exceed the "
            f"{max_pct:.0f}% limit. Reduce quantity or increase cash."
        )

    return None


# ── Buy / Sell (proper accounting) ────────────────────────────────────────────

def buy(
    symbol: str,
    quantity: float,
    price: float,
    portfolio_id: str | None = None,
    mode: Mode | None = None,
    thesis: str = "",
    strategy_id: str = "",
) -> dict[str, Any]:
    """Buy shares: deduct cash, add/accumulate holding, log trade.

    This is the primary trade function. The agent should use this
    instead of add_holding for all purchases.
    """
    if quantity <= 0:
        return {"ok": False, "error": "Quantity must be positive."}
    if price <= 0:
        return {"ok": False, "error": "Price must be positive."}

    state = _load_state()
    pid = portfolio_id or state.active_portfolio
    m = mode or state.active_mode
    if pid not in state.portfolios:
        return {"ok": False, "error": f"Portfolio '{pid}' not found."}

    symbol = symbol.upper()
    if _looks_like_option(symbol):
        return {"ok": False, "error": f"'{symbol}' looks like an options contract. Only stocks/ETFs are supported."}

    risk_err = _check_buy_risk(state, pid, m, symbol, quantity, price)
    if risk_err:
        return {"ok": False, "error": risk_err}

    t = state.portfolios[pid].track(m)
    trade_value = round(quantity * price, 2)
    cash_before = t.cash_balance

    t.cash_balance = round(t.cash_balance - trade_value, 2)

    existing = next((h for h in t.holdings if h.symbol == symbol), None)
    if existing:
        total_qty = existing.quantity + quantity
        total_cost = existing.quantity * existing.cost_basis + quantity * price
        existing.cost_basis = round(total_cost / total_qty, 4) if total_qty else 0
        existing.quantity = round(total_qty, 6)
    else:
        t.holdings.append(Holding(symbol=symbol, quantity=quantity, cost_basis=price))

    t.updated_at = _now_iso()
    _save_state(state)

    trade = Trade(
        timestamp=_now_iso(), portfolio_id=pid, mode=m, side="buy",
        symbol=symbol, quantity=quantity, price=price,
        total_cost=trade_value, cash_before=cash_before,
        cash_after=t.cash_balance, thesis=thesis,
        strategy_id=strategy_id,
    )
    _log_trade(trade)
    logger.info("[Portfolio] BUY %s x%.4f @$%.2f = $%.2f (%s/%s) strategy=%s",
                symbol, quantity, price, trade_value, pid, m, strategy_id or "manual")

    return {
        "ok": True, "side": "buy", "symbol": symbol,
        "quantity": quantity, "price": price, "total_cost": trade_value,
        "cash_remaining": t.cash_balance,
    }


def sell(
    symbol: str,
    quantity: float,
    price: float,
    portfolio_id: str | None = None,
    mode: Mode | None = None,
    thesis: str = "",
    strategy_id: str = "",
) -> dict[str, Any]:
    """Sell shares: add cash, reduce/remove holding, log trade.

    Partial sells are supported. If quantity >= held quantity,
    the entire position is closed.
    """
    if quantity <= 0:
        return {"ok": False, "error": "Quantity must be positive."}
    if price <= 0:
        return {"ok": False, "error": "Price must be positive."}

    state = _load_state()
    pid = portfolio_id or state.active_portfolio
    m = mode or state.active_mode
    if pid not in state.portfolios:
        return {"ok": False, "error": f"Portfolio '{pid}' not found."}

    symbol = symbol.upper()
    t = state.portfolios[pid].track(m)

    existing = next((h for h in t.holdings if h.symbol == symbol), None)
    if not existing:
        return {"ok": False, "error": f"No position in '{symbol}' to sell."}

    actual_qty = min(quantity, existing.quantity)
    proceeds = round(actual_qty * price, 2)
    cost_basis_for_sold = actual_qty * existing.cost_basis
    realized_pnl = round(proceeds - cost_basis_for_sold, 2)
    cash_before = t.cash_balance

    t.cash_balance = round(t.cash_balance + proceeds, 2)

    remaining_qty = round(existing.quantity - actual_qty, 6)
    if remaining_qty <= 0.000001:
        t.holdings = [h for h in t.holdings if h.symbol != symbol]
        remaining_qty = 0
    else:
        existing.quantity = remaining_qty

    t.updated_at = _now_iso()
    _save_state(state)

    trade = Trade(
        timestamp=_now_iso(), portfolio_id=pid, mode=m, side="sell",
        symbol=symbol, quantity=actual_qty, price=price,
        total_cost=proceeds, cash_before=cash_before,
        cash_after=t.cash_balance, thesis=thesis,
        strategy_id=strategy_id,
    )
    _log_trade(trade)
    logger.info(
        "[Portfolio] SELL %s x%.4f @$%.2f = $%.2f (P&L: $%.2f) (%s/%s) strategy=%s",
        symbol, actual_qty, price, proceeds, realized_pnl, pid, m, strategy_id or "manual",
    )

    return {
        "ok": True, "side": "sell", "symbol": symbol,
        "quantity_sold": actual_qty, "price": price, "proceeds": proceeds,
        "realized_pnl": realized_pnl, "remaining_quantity": remaining_qty,
        "cash_balance": t.cash_balance,
    }


# ── Legacy holdings management (kept for dashboard/API compatibility) ─────────

def add_holding(
    symbol: str, quantity: float, cost_basis: float,
    portfolio_id: str | None = None, mode: Mode | None = None,
) -> dict[str, Any]:
    """Add or accumulate a holding (dashboard use). For agent trades, use buy()."""
    state = _load_state()
    pid = portfolio_id or state.active_portfolio
    m = mode or state.active_mode
    if pid not in state.portfolios:
        return {"ok": False, "error": f"Portfolio '{pid}' not found."}

    symbol = symbol.upper()
    if _looks_like_option(symbol):
        return {"ok": False, "error": f"'{symbol}' looks like an options contract. Only stocks are supported."}

    t = state.portfolios[pid].track(m)

    existing = next((h for h in t.holdings if h.symbol == symbol), None)
    if existing:
        total_qty = existing.quantity + quantity
        total_cost = existing.quantity * existing.cost_basis + quantity * cost_basis
        existing.cost_basis = round(total_cost / total_qty, 4) if total_qty else 0
        existing.quantity = total_qty
    else:
        t.holdings.append(Holding(symbol=symbol, quantity=quantity, cost_basis=cost_basis))

    t.updated_at = _now_iso()
    _save_state(state)
    return {"ok": True, "symbol": symbol, "quantity": quantity, "cost_basis": cost_basis}


def remove_holding(
    symbol: str, portfolio_id: str | None = None, mode: Mode | None = None,
) -> dict[str, Any]:
    """Remove a holding entirely."""
    state = _load_state()
    pid = portfolio_id or state.active_portfolio
    m = mode or state.active_mode
    if pid not in state.portfolios:
        return {"ok": False, "error": f"Portfolio '{pid}' not found."}

    t = state.portfolios[pid].track(m)
    symbol = symbol.upper()
    before = len(t.holdings)
    t.holdings = [h for h in t.holdings if h.symbol != symbol]
    if len(t.holdings) == before:
        return {"ok": False, "error": f"Holding '{symbol}' not found."}

    t.updated_at = _now_iso()
    _save_state(state)
    return {"ok": True, "symbol": symbol, "removed": True}


def update_holding(
    symbol: str, quantity: float | None = None, cost_basis: float | None = None,
    portfolio_id: str | None = None, mode: Mode | None = None,
) -> dict[str, Any]:
    """Update a holding's quantity and/or cost basis."""
    state = _load_state()
    pid = portfolio_id or state.active_portfolio
    m = mode or state.active_mode
    if pid not in state.portfolios:
        return {"ok": False, "error": f"Portfolio '{pid}' not found."}

    t = state.portfolios[pid].track(m)
    symbol = symbol.upper()
    h = next((h for h in t.holdings if h.symbol == symbol), None)
    if h is None:
        return {"ok": False, "error": f"Holding '{symbol}' not found."}

    if quantity is not None:
        h.quantity = quantity
    if cost_basis is not None:
        h.cost_basis = cost_basis

    t.updated_at = _now_iso()
    _save_state(state)
    return {"ok": True, "symbol": symbol, "quantity": h.quantity, "cost_basis": h.cost_basis}


# ── Snapshots ─────────────────────────────────────────────────────────────────

def take_snapshot(portfolio_id: str, mode: Mode) -> Snapshot | None:
    """Fetch prices and record a snapshot for one portfolio/mode."""
    state = _load_state()
    if portfolio_id not in state.portfolios:
        return None
    p = state.portfolios[portfolio_id]
    t = p.track(mode)

    if not t.holdings and t.cash_balance == 0:
        return None

    symbols = [h.symbol for h in t.holdings]
    prices = fetch_prices(symbols) if symbols else {}

    holdings_value = 0.0
    total_cost = 0.0
    positions: dict[str, dict] = {}

    for h in t.holdings:
        price = prices.get(h.symbol)
        cost_val = h.quantity * h.cost_basis
        total_cost += cost_val
        if price is not None:
            mkt_val = h.quantity * price
            holdings_value += mkt_val
            pnl = mkt_val - cost_val
            positions[h.symbol] = {
                "price": price,
                "value": round(mkt_val, 2),
                "pnl": round(pnl, 2),
                "pnl_pct": round(pnl / cost_val * 100, 2) if cost_val else 0,
            }

    total_value = t.cash_balance + holdings_value

    snapshot = Snapshot(
        timestamp=_now_iso(),
        total_value=round(total_value, 2),
        cash_balance=round(t.cash_balance, 2),
        holdings_value=round(holdings_value, 2),
        total_cost=round(total_cost, 2),
        pnl=round(holdings_value - total_cost, 2),
        positions=positions,
    )

    existing = _load_snapshots(portfolio_id, mode)
    existing.append(snapshot)
    if len(existing) > 2000:
        existing = existing[-2000:]
    _save_snapshots(portfolio_id, mode, existing)

    logger.info("[Portfolio] Snapshot %s/%s: value=%.2f pnl=%.2f", portfolio_id, mode, total_value, holdings_value - total_cost)

    try:
        from .. import db
        db.record_snapshot(
            timestamp=snapshot.timestamp,
            portfolio_id=portfolio_id,
            mode=mode,
            total_value=snapshot.total_value,
            cash_balance=snapshot.cash_balance,
            holdings_value=snapshot.holdings_value,
            total_cost=snapshot.total_cost,
            pnl=snapshot.pnl,
            positions=snapshot.positions,
        )
    except Exception:
        pass

    return snapshot


def take_all_snapshots() -> int:
    """Snapshot all portfolio/mode combinations that have data."""
    count = 0
    for pid in PORTFOLIO_DEFS:
        for mode in ("live", "simulate"):
            if take_snapshot(pid, mode) is not None:
                count += 1
    return count


def get_snapshots(portfolio_id: str, mode: Mode, days: int = 30) -> list[dict[str, Any]]:
    """Return snapshot time series for charting."""
    snapshots = _load_snapshots(portfolio_id, mode)
    if not snapshots:
        return []

    if days > 0:
        cutoff = datetime.now(timezone.utc).timestamp() - days * 86400
        filtered = []
        for s in snapshots:
            try:
                ts = datetime.fromisoformat(s.timestamp).timestamp()
                if ts >= cutoff:
                    filtered.append(s)
            except (ValueError, TypeError):
                filtered.append(s)
        snapshots = filtered

    return [
        {
            "timestamp": s.timestamp,
            "total_value": s.total_value,
            "cash_balance": s.cash_balance,
            "holdings_value": s.holdings_value,
            "total_cost": s.total_cost,
            "pnl": s.pnl,
        }
        for s in snapshots
    ]


# ── Performance analytics ─────────────────────────────────────────────────────

def get_performance(
    portfolio_id: str | None = None,
    mode: Mode | None = None,
    days: int = 90,
) -> dict[str, Any]:
    """Compute portfolio performance metrics from snapshot history.

    Returns total return, annualized return, Sharpe ratio, max drawdown,
    and benchmark comparison. Metrics that require >=2 snapshots return
    None when insufficient data exists.
    """
    state = _load_state()
    pid = portfolio_id or state.active_portfolio
    m = mode or state.active_mode

    snaps = _load_snapshots(pid, m)
    if not snaps:
        return {"ok": True, "portfolio": pid, "mode": m, "message": "No snapshot data yet."}

    if days > 0:
        cutoff = datetime.now(timezone.utc).timestamp() - days * 86400
        snaps = [s for s in snaps if _ts(s.timestamp) >= cutoff]

    values = [s.total_value for s in snaps if s.total_value > 0]
    if len(values) < 2:
        detail = get_portfolio_detail(pid, m)
        return {
            "ok": True, "portfolio": pid, "mode": m,
            "total_value": detail["total_value"] if detail else 0,
            "message": "Need at least 2 snapshots for performance metrics.",
        }

    first_val = values[0]
    last_val = values[-1]
    total_return_pct = ((last_val / first_val) - 1) * 100

    first_ts = _ts(snaps[0].timestamp)
    last_ts = _ts(snaps[-1].timestamp)
    elapsed_days = max((last_ts - first_ts) / 86400, 1)
    ann_return_pct = ((last_val / first_val) ** (365.25 / elapsed_days) - 1) * 100

    daily_returns = []
    for i in range(1, len(values)):
        if values[i - 1] > 0:
            daily_returns.append(values[i] / values[i - 1] - 1)

    sharpe = _sharpe_ratio(daily_returns, elapsed_days, len(values))
    max_dd = _max_drawdown(values)

    bench_return = _benchmark_return(pid, days)

    return {
        "ok": True,
        "portfolio": pid,
        "mode": m,
        "period_days": round(elapsed_days, 1),
        "snapshots_count": len(values),
        "start_value": round(first_val, 2),
        "end_value": round(last_val, 2),
        "total_return_pct": round(total_return_pct, 2),
        "annualized_return_pct": round(ann_return_pct, 2),
        "sharpe_ratio": round(sharpe, 2) if sharpe is not None else None,
        "max_drawdown_pct": round(max_dd, 2) if max_dd is not None else None,
        "benchmark": BENCHMARK.get(pid, "SPY"),
        "benchmark_return_pct": round(bench_return, 2) if bench_return is not None else None,
        "alpha_pct": round(total_return_pct - bench_return, 2) if bench_return is not None else None,
    }


def _ts(iso_str: str) -> float:
    """Parse ISO timestamp to Unix epoch."""
    try:
        return datetime.fromisoformat(iso_str).timestamp()
    except (ValueError, TypeError):
        return 0.0


def _sharpe_ratio(
    returns: list[float],
    period_days: float,
    n_observations: int,
    risk_free_annual: float = 0.05,
) -> float | None:
    """Annualized Sharpe ratio. Returns None if insufficient data."""
    if len(returns) < 5:
        return None
    avg_interval_days = period_days / max(n_observations - 1, 1)
    periods_per_year = 365.25 / max(avg_interval_days, 0.01)
    rf_per_period = (1 + risk_free_annual) ** (1 / periods_per_year) - 1

    excess = [r - rf_per_period for r in returns]
    mean_excess = sum(excess) / len(excess)
    variance = sum((r - mean_excess) ** 2 for r in excess) / len(excess)
    std = math.sqrt(variance)
    if std < 1e-10:
        return None
    return (mean_excess / std) * math.sqrt(periods_per_year)


def _max_drawdown(values: list[float]) -> float | None:
    """Max drawdown as a positive percentage (e.g. 15.2 means -15.2%)."""
    if len(values) < 2:
        return None
    peak = values[0]
    max_dd = 0.0
    for v in values[1:]:
        if v > peak:
            peak = v
        dd = (peak - v) / peak * 100 if peak > 0 else 0
        if dd > max_dd:
            max_dd = dd
    return max_dd


def _benchmark_return(portfolio_id: str, days: int) -> float | None:
    """Fetch benchmark total return over the given period."""
    bench = BENCHMARK.get(portfolio_id)
    if not bench:
        return None
    try:
        from datetime import timedelta

        import yfinance as yf
        end = datetime.now(timezone.utc)
        start = end - timedelta(days=days)
        data = yf.download(bench, start=start.strftime("%Y-%m-%d"), end=end.strftime("%Y-%m-%d"), progress=False)
        if data.empty or len(data) < 2:
            return None
        first_close = float(data["Close"].iloc[0])
        last_close = float(data["Close"].iloc[-1])
        if first_close <= 0:
            return None
        return ((last_close / first_close) - 1) * 100
    except Exception:
        return None


def get_portfolio_summary(
    portfolio_id: str | None = None,
    mode: Mode | None = None,
) -> str:
    """Human-readable portfolio summary for the agent to use in responses."""
    detail = get_portfolio_detail(portfolio_id, mode)
    if not detail:
        return "Portfolio not found."

    lines = [
        f"**{detail['name']}** ({detail['mode']} mode)",
        f"Cash: ${detail['cash_balance']:,.2f}",
        f"Holdings value: ${detail['holdings_value']:,.2f}",
        f"Total value: ${detail['total_value']:,.2f}",
    ]
    if detail.get("total_pnl") is not None:
        lines.append(f"Unrealized P&L: ${detail['total_pnl']:,.2f} ({detail.get('total_pnl_pct', 0):.1f}%)")

    if detail.get("positions"):
        lines.append(f"\nPositions ({len(detail['positions'])}):")
        for pos in sorted(detail["positions"], key=lambda p: p.get("market_value") or 0, reverse=True):
            pnl_str = f" P&L: ${pos['pnl']:+,.2f}" if pos.get("pnl") is not None else ""
            price_str = f"@${pos['current_price']:,.2f}" if pos.get("current_price") else ""
            lines.append(
                f"  {pos['symbol']}: {pos['quantity']}sh {price_str}"
                f" = ${pos.get('market_value', 0):,.2f}{pnl_str}"
            )
    else:
        lines.append("\nNo positions held.")

    return "\n".join(lines)
