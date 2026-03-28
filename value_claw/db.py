"""
PostgreSQL persistence layer for value_claw.

All portfolio operations, trades, snapshots, and strategy events are
recorded in a local PostgreSQL database for audit trail, analytics,
and dashboard visualization.

Tables
------
- ``trades``             — every buy/sell execution
- ``portfolio_snapshots``— periodic portfolio value snapshots
- ``portfolio_events``   — cash deposits, withdrawals, mode switches
- ``strategy_events``    — strategy start/stop/register/delete
- ``daily_values``       — aggregated end-of-day portfolio values (materialized by snapshot inserts)

Connection
----------
Configured via ``value_claw.json`` key ``database.url`` or env ``DATABASE_URL``::

    "database": {
        "url": "postgresql://user:pass@localhost:5432/value_claw"
    }

If no database is configured, all ``record_*`` functions silently no-op
so the rest of the system keeps working with JSON files alone.
"""

from __future__ import annotations

import logging
import os
from contextlib import contextmanager
from datetime import date, datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)

_engine = None
_SessionLocal = None
_Base = None
_initialized = False

# ── Lazy SQLAlchemy imports (only when DB is configured) ─────────────────────

def _get_sa():
    """Lazy-import SQLAlchemy to avoid hard dependency."""
    import sqlalchemy as sa
    return sa


def _get_orm():
    from sqlalchemy import orm
    return orm


# ── Models ───────────────────────────────────────────────────────────────────

def _define_models():
    """Define SQLAlchemy ORM models. Called once at init time."""
    sa = _get_sa()
    orm = _get_orm()
    Base = orm.declarative_base()

    class TradeRecord(Base):
        __tablename__ = "trades"
        id = sa.Column(sa.Integer, primary_key=True, autoincrement=True)
        timestamp = sa.Column(sa.DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
        portfolio_id = sa.Column(sa.String(50), nullable=False, index=True)
        mode = sa.Column(sa.String(20), nullable=False)
        side = sa.Column(sa.String(10), nullable=False)
        symbol = sa.Column(sa.String(20), nullable=False, index=True)
        quantity = sa.Column(sa.Float, nullable=False)
        price = sa.Column(sa.Float, nullable=False)
        total_cost = sa.Column(sa.Float, nullable=False)
        cash_before = sa.Column(sa.Float, nullable=False)
        cash_after = sa.Column(sa.Float, nullable=False)
        thesis = sa.Column(sa.Text, default="")
        strategy_id = sa.Column(sa.String(100), default="", index=True)

    class PortfolioSnapshot(Base):
        __tablename__ = "portfolio_snapshots"
        id = sa.Column(sa.Integer, primary_key=True, autoincrement=True)
        timestamp = sa.Column(sa.DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
        portfolio_id = sa.Column(sa.String(50), nullable=False, index=True)
        mode = sa.Column(sa.String(20), nullable=False)
        total_value = sa.Column(sa.Float, nullable=False)
        cash_balance = sa.Column(sa.Float, nullable=False)
        holdings_value = sa.Column(sa.Float, nullable=False)
        total_cost = sa.Column(sa.Float, nullable=False)
        pnl = sa.Column(sa.Float, nullable=False)
        positions_json = sa.Column(sa.Text, default="{}")

    class PortfolioEvent(Base):
        __tablename__ = "portfolio_events"
        id = sa.Column(sa.Integer, primary_key=True, autoincrement=True)
        timestamp = sa.Column(sa.DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
        portfolio_id = sa.Column(sa.String(50), nullable=False, index=True)
        mode = sa.Column(sa.String(20), nullable=False)
        event_type = sa.Column(sa.String(50), nullable=False, index=True)
        amount = sa.Column(sa.Float, default=0)
        details = sa.Column(sa.Text, default="")

    class StrategyEvent(Base):
        __tablename__ = "strategy_events"
        id = sa.Column(sa.Integer, primary_key=True, autoincrement=True)
        timestamp = sa.Column(sa.DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
        strategy_id = sa.Column(sa.String(100), nullable=False, index=True)
        event_type = sa.Column(sa.String(50), nullable=False)
        details = sa.Column(sa.Text, default="")

    class DailyValue(Base):
        __tablename__ = "daily_values"
        id = sa.Column(sa.Integer, primary_key=True, autoincrement=True)
        date = sa.Column(sa.Date, nullable=False, index=True)
        portfolio_id = sa.Column(sa.String(50), nullable=False, index=True)
        mode = sa.Column(sa.String(20), nullable=False)
        total_value = sa.Column(sa.Float, nullable=False)
        cash_balance = sa.Column(sa.Float, nullable=False)
        holdings_value = sa.Column(sa.Float, nullable=False)
        pnl = sa.Column(sa.Float, nullable=False)
        __table_args__ = (
            sa.UniqueConstraint("date", "portfolio_id", "mode", name="uq_daily_value"),
        )

    return Base, TradeRecord, PortfolioSnapshot, PortfolioEvent, StrategyEvent, DailyValue


# ── Module-level model references (set after init) ──────────────────────────

TradeRecord = None
PortfolioSnapshot = None
PortfolioEvent = None
StrategyEvent = None
DailyValue = None


# ── Connection management ────────────────────────────────────────────────────

def _get_database_url() -> str | None:
    """Read the database URL from config or environment."""
    url = os.environ.get("DATABASE_URL")
    if url:
        return url
    try:
        from . import config
        url = config.get("database", "url", default="")
        return url if url else None
    except Exception:
        return None


def init_db(url: str | None = None) -> bool:
    """Initialize the database connection and create tables.

    Returns True if the database was successfully initialized.
    """
    global _engine, _SessionLocal, _Base, _initialized
    global TradeRecord, PortfolioSnapshot, PortfolioEvent, StrategyEvent, DailyValue

    db_url = url or _get_database_url()
    if not db_url:
        logger.info("[DB] No database URL configured — PostgreSQL logging disabled.")
        return False

    try:
        sa = _get_sa()
        orm = _get_orm()

        engine_kwargs: dict[str, Any] = {"pool_pre_ping": True}
        if not db_url.startswith("sqlite"):
            engine_kwargs.update(pool_size=5, max_overflow=10)
        _engine = sa.create_engine(db_url, **engine_kwargs)

        _Base, TradeRecord, PortfolioSnapshot, PortfolioEvent, StrategyEvent, DailyValue = _define_models()
        _Base.metadata.create_all(_engine)

        _SessionLocal = orm.sessionmaker(bind=_engine)
        _initialized = True
        logger.info("[DB] PostgreSQL initialized: %s", db_url.split("@")[-1] if "@" in db_url else db_url)
        return True

    except Exception as exc:
        logger.warning("[DB] Failed to initialize PostgreSQL: %s", exc)
        _initialized = False
        return False


def is_initialized() -> bool:
    return _initialized


@contextmanager
def get_session():
    """Context manager that yields a SQLAlchemy session."""
    if not _initialized or _SessionLocal is None:
        yield None
        return
    session = _SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


# ── Recording functions (called from portfolio.py, strategy.py) ──────────────

def record_trade(
    timestamp: str,
    portfolio_id: str,
    mode: str,
    side: str,
    symbol: str,
    quantity: float,
    price: float,
    total_cost: float,
    cash_before: float,
    cash_after: float,
    thesis: str = "",
    strategy_id: str = "",
) -> None:
    """Record a trade in the database."""
    if not _initialized:
        return
    try:
        with get_session() as session:
            if session is None:
                return
            session.add(TradeRecord(
                timestamp=_parse_ts(timestamp),
                portfolio_id=portfolio_id,
                mode=mode,
                side=side,
                symbol=symbol,
                quantity=quantity,
                price=price,
                total_cost=total_cost,
                cash_before=cash_before,
                cash_after=cash_after,
                thesis=thesis,
                strategy_id=strategy_id,
            ))
    except Exception as exc:
        logger.debug("[DB] Failed to record trade: %s", exc)


def record_snapshot(
    timestamp: str,
    portfolio_id: str,
    mode: str,
    total_value: float,
    cash_balance: float,
    holdings_value: float,
    total_cost: float,
    pnl: float,
    positions: dict | None = None,
) -> None:
    """Record a portfolio snapshot and update the daily_values table."""
    if not _initialized:
        return
    import json
    try:
        ts = _parse_ts(timestamp)
        with get_session() as session:
            if session is None:
                return
            session.add(PortfolioSnapshot(
                timestamp=ts,
                portfolio_id=portfolio_id,
                mode=mode,
                total_value=total_value,
                cash_balance=cash_balance,
                holdings_value=holdings_value,
                total_cost=total_cost,
                pnl=pnl,
                positions_json=json.dumps(positions or {}),
            ))
            _upsert_daily_value(session, ts.date(), portfolio_id, mode,
                                total_value, cash_balance, holdings_value, pnl)
    except Exception as exc:
        logger.debug("[DB] Failed to record snapshot: %s", exc)


def record_portfolio_event(
    portfolio_id: str,
    mode: str,
    event_type: str,
    amount: float = 0,
    details: str = "",
) -> None:
    """Record a portfolio event (topup, cashout, switch, etc.)."""
    if not _initialized:
        return
    try:
        with get_session() as session:
            if session is None:
                return
            session.add(PortfolioEvent(
                portfolio_id=portfolio_id,
                mode=mode,
                event_type=event_type,
                amount=amount,
                details=details,
            ))
    except Exception as exc:
        logger.debug("[DB] Failed to record portfolio event: %s", exc)


def record_strategy_event(
    strategy_id: str,
    event_type: str,
    details: str = "",
) -> None:
    """Record a strategy lifecycle event."""
    if not _initialized:
        return
    try:
        with get_session() as session:
            if session is None:
                return
            session.add(StrategyEvent(
                strategy_id=strategy_id,
                event_type=event_type,
                details=details,
            ))
    except Exception as exc:
        logger.debug("[DB] Failed to record strategy event: %s", exc)


# ── Query functions (for API/dashboard) ──────────────────────────────────────

def get_daily_values(
    portfolio_id: str,
    mode: str,
    days: int = 90,
) -> list[dict[str, Any]]:
    """Get daily portfolio values for charting."""
    if not _initialized:
        return []
    try:
        sa = _get_sa()
        cutoff = date.today().toordinal() - days
        cutoff_date = date.fromordinal(cutoff)
        with get_session() as session:
            if session is None:
                return []
            rows = (
                session.query(DailyValue)
                .filter(
                    DailyValue.portfolio_id == portfolio_id,
                    DailyValue.mode == mode,
                    DailyValue.date >= cutoff_date,
                )
                .order_by(DailyValue.date)
                .all()
            )
            return [
                {
                    "date": row.date.isoformat(),
                    "total_value": row.total_value,
                    "cash_balance": row.cash_balance,
                    "holdings_value": row.holdings_value,
                    "pnl": row.pnl,
                }
                for row in rows
            ]
    except Exception as exc:
        logger.debug("[DB] Failed to get daily values: %s", exc)
        return []


def get_trades_from_db(
    portfolio_id: str | None = None,
    mode: str | None = None,
    strategy_id: str | None = None,
    limit: int = 100,
    offset: int = 0,
) -> list[dict[str, Any]]:
    """Query trades with optional filters."""
    if not _initialized:
        return []
    try:
        with get_session() as session:
            if session is None:
                return []
            q = session.query(TradeRecord).order_by(TradeRecord.timestamp.desc())
            if portfolio_id:
                q = q.filter(TradeRecord.portfolio_id == portfolio_id)
            if mode:
                q = q.filter(TradeRecord.mode == mode)
            if strategy_id:
                q = q.filter(TradeRecord.strategy_id == strategy_id)
            rows = q.offset(offset).limit(limit).all()
            return [
                {
                    "id": row.id,
                    "timestamp": row.timestamp.isoformat() if row.timestamp else "",
                    "portfolio_id": row.portfolio_id,
                    "mode": row.mode,
                    "side": row.side,
                    "symbol": row.symbol,
                    "quantity": row.quantity,
                    "price": row.price,
                    "total_cost": row.total_cost,
                    "cash_before": row.cash_before,
                    "cash_after": row.cash_after,
                    "thesis": row.thesis,
                    "strategy_id": row.strategy_id,
                }
                for row in rows
            ]
    except Exception as exc:
        logger.debug("[DB] Failed to query trades: %s", exc)
        return []


def get_portfolio_events(
    portfolio_id: str | None = None,
    event_type: str | None = None,
    limit: int = 100,
) -> list[dict[str, Any]]:
    """Query portfolio events."""
    if not _initialized:
        return []
    try:
        with get_session() as session:
            if session is None:
                return []
            q = session.query(PortfolioEvent).order_by(PortfolioEvent.timestamp.desc())
            if portfolio_id:
                q = q.filter(PortfolioEvent.portfolio_id == portfolio_id)
            if event_type:
                q = q.filter(PortfolioEvent.event_type == event_type)
            rows = q.limit(limit).all()
            return [
                {
                    "id": row.id,
                    "timestamp": row.timestamp.isoformat() if row.timestamp else "",
                    "portfolio_id": row.portfolio_id,
                    "mode": row.mode,
                    "event_type": row.event_type,
                    "amount": row.amount,
                    "details": row.details,
                }
                for row in rows
            ]
    except Exception as exc:
        logger.debug("[DB] Failed to query portfolio events: %s", exc)
        return []


def get_strategy_events(
    strategy_id: str | None = None,
    limit: int = 100,
) -> list[dict[str, Any]]:
    """Query strategy events."""
    if not _initialized:
        return []
    try:
        with get_session() as session:
            if session is None:
                return []
            q = session.query(StrategyEvent).order_by(StrategyEvent.timestamp.desc())
            if strategy_id:
                q = q.filter(StrategyEvent.strategy_id == strategy_id)
            rows = q.limit(limit).all()
            return [
                {
                    "id": row.id,
                    "timestamp": row.timestamp.isoformat() if row.timestamp else "",
                    "strategy_id": row.strategy_id,
                    "event_type": row.event_type,
                    "details": row.details,
                }
                for row in rows
            ]
    except Exception as exc:
        logger.debug("[DB] Failed to query strategy events: %s", exc)
        return []


def get_snapshots_from_db(
    portfolio_id: str,
    mode: str,
    days: int = 30,
    limit: int = 500,
) -> list[dict[str, Any]]:
    """Query snapshots from the database."""
    if not _initialized:
        return []
    try:
        sa = _get_sa()
        cutoff = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0)
        from datetime import timedelta
        cutoff = cutoff - timedelta(days=days)
        with get_session() as session:
            if session is None:
                return []
            rows = (
                session.query(PortfolioSnapshot)
                .filter(
                    PortfolioSnapshot.portfolio_id == portfolio_id,
                    PortfolioSnapshot.mode == mode,
                    PortfolioSnapshot.timestamp >= cutoff,
                )
                .order_by(PortfolioSnapshot.timestamp)
                .limit(limit)
                .all()
            )
            return [
                {
                    "timestamp": row.timestamp.isoformat() if row.timestamp else "",
                    "total_value": row.total_value,
                    "cash_balance": row.cash_balance,
                    "holdings_value": row.holdings_value,
                    "pnl": row.pnl,
                }
                for row in rows
            ]
    except Exception as exc:
        logger.debug("[DB] Failed to query snapshots: %s", exc)
        return []


# ── Internal helpers ─────────────────────────────────────────────────────────

def _parse_ts(ts_str: str) -> datetime:
    """Parse an ISO timestamp string into a datetime."""
    try:
        return datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        return datetime.now(timezone.utc)


def _upsert_daily_value(
    session,
    day: date,
    portfolio_id: str,
    mode: str,
    total_value: float,
    cash_balance: float,
    holdings_value: float,
    pnl: float,
) -> None:
    """Insert or update the daily_values row for a given date/portfolio/mode."""
    existing = (
        session.query(DailyValue)
        .filter(
            DailyValue.date == day,
            DailyValue.portfolio_id == portfolio_id,
            DailyValue.mode == mode,
        )
        .first()
    )
    if existing:
        existing.total_value = total_value
        existing.cash_balance = cash_balance
        existing.holdings_value = holdings_value
        existing.pnl = pnl
    else:
        session.add(DailyValue(
            date=day,
            portfolio_id=portfolio_id,
            mode=mode,
            total_value=total_value,
            cash_balance=cash_balance,
            holdings_value=holdings_value,
            pnl=pnl,
        ))
