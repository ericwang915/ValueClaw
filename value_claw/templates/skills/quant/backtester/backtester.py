#!/usr/bin/env python3
"""Simple strategy backtester — SMA crossover, momentum, buy-and-hold."""

from __future__ import annotations

import argparse
import json
import math
import os
import sys
from datetime import datetime

import numpy as np

DATA_DIR = os.path.expanduser("~/.value_claw/backtester")


def _ensure_dir() -> None:
    os.makedirs(DATA_DIR, exist_ok=True)


def fetch_prices(ticker: str, start: str, end: str) -> tuple[list[str], np.ndarray]:
    """Fetch daily close prices via yfinance. Returns (dates, prices)."""
    try:
        import yfinance as yf
    except ImportError:
        print("yfinance not installed. Run: pip install yfinance", file=sys.stderr)
        sys.exit(1)

    df = yf.download(ticker, start=start, end=end, progress=False)
    if df.empty:
        print("No data returned for %s" % ticker, file=sys.stderr)
        sys.exit(1)

    dates = [d.strftime("%Y-%m-%d") for d in df.index]
    closes = df["Close"].values.flatten().astype(float)
    return dates, closes


def strategy_buy_hold(prices: np.ndarray) -> np.ndarray:
    """Buy-and-hold: always in the market."""
    returns = np.diff(prices) / prices[:-1]
    return returns


def strategy_sma_cross(prices: np.ndarray, fast: int, slow: int) -> tuple[np.ndarray, int]:
    """SMA crossover: long when fast > slow, flat otherwise."""
    n = len(prices)
    signals = np.zeros(n)
    for i in range(slow, n):
        fast_avg = prices[i - fast:i].mean()
        slow_avg = prices[i - slow:i].mean()
        signals[i] = 1.0 if fast_avg > slow_avg else 0.0

    daily_ret = np.diff(prices) / prices[:-1]
    strat_ret = daily_ret * signals[1:]
    trades = int(np.sum(np.abs(np.diff(signals[slow:])) > 0))
    return strat_ret, trades


def strategy_momentum(prices: np.ndarray, lookback: int) -> tuple[np.ndarray, int]:
    """Momentum: long if price > price N days ago, flat otherwise."""
    n = len(prices)
    signals = np.zeros(n)
    for i in range(lookback, n):
        signals[i] = 1.0 if prices[i] > prices[i - lookback] else 0.0

    daily_ret = np.diff(prices) / prices[:-1]
    strat_ret = daily_ret * signals[1:]
    trades = int(np.sum(np.abs(np.diff(signals[lookback:])) > 0))
    return strat_ret, trades


def compute_metrics(returns: np.ndarray, num_trades: int) -> dict:
    """Compute performance metrics from a return series."""
    total_ret = float(np.prod(1 + returns) - 1)
    n_days = len(returns)
    annual_ret = float((1 + total_ret) ** (252 / max(n_days, 1)) - 1)

    std = float(np.std(returns)) if n_days > 1 else 0
    sharpe = float((np.mean(returns) / std) * math.sqrt(252)) if std > 0 else 0

    cumulative = np.cumprod(1 + returns)
    running_max = np.maximum.accumulate(cumulative)
    drawdowns = (cumulative - running_max) / running_max
    max_dd = float(np.min(drawdowns))

    return {
        "total_return_pct": round(total_ret * 100, 2),
        "annual_return_pct": round(annual_ret * 100, 2),
        "sharpe_ratio": round(sharpe, 3),
        "max_drawdown_pct": round(max_dd * 100, 2),
        "num_trades": num_trades,
        "trading_days": n_days,
    }


def format_text(ticker: str, strat_name: str, strat_metrics: dict, bh_metrics: dict) -> str:
    """Render backtest results as text."""
    lines = [
        "=" * 60,
        "  BACKTEST RESULTS: %s" % ticker,
        "  Strategy: %s" % strat_name,
        "  Generated: %s" % datetime.now().strftime("%Y-%m-%d %H:%M"),
        "=" * 60,
        "",
        "%-24s %14s %14s" % ("Metric", "Strategy", "Buy & Hold"),
        "-" * 60,
    ]
    keys = [
        ("total_return_pct", "Total Return"),
        ("annual_return_pct", "Annual Return"),
        ("sharpe_ratio", "Sharpe Ratio"),
        ("max_drawdown_pct", "Max Drawdown"),
        ("num_trades", "Trades"),
        ("trading_days", "Trading Days"),
    ]
    for key, label in keys:
        sv = strat_metrics[key]
        bv = bh_metrics[key]
        fmt = "%+.2f%%" if "pct" in key else "%.3f" if "sharpe" in key else "%d"
        lines.append(
            "%-24s %14s %14s" % (label, fmt % sv, fmt % bv)
        )

    lines.append("-" * 60)
    excess = strat_metrics["total_return_pct"] - bh_metrics["total_return_pct"]
    lines.append("  Excess return vs buy-and-hold: %+.2f%%" % excess)
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Simple Strategy Backtester")
    parser.add_argument("--ticker", required=True, help="Stock ticker")
    parser.add_argument("--start", default="2020-01-01", help="Start date (YYYY-MM-DD)")
    parser.add_argument("--end", default="2025-01-01", help="End date (YYYY-MM-DD)")
    parser.add_argument("--strategy", default="sma_cross",
                        choices=["sma_cross", "momentum", "buy_hold"])
    parser.add_argument("--fast", type=int, default=20, help="Fast SMA period")
    parser.add_argument("--slow", type=int, default=50, help="Slow SMA period")
    parser.add_argument("--lookback", type=int, default=60, help="Momentum lookback")
    parser.add_argument("--format", choices=["text", "json"], default="text")
    args = parser.parse_args()

    _ensure_dir()
    ticker = args.ticker.upper()
    print("Fetching price data for %s (%s to %s)..." % (ticker, args.start, args.end))
    dates, prices = fetch_prices(ticker, args.start, args.end)
    print("  %d trading days loaded." % len(prices))

    bh_returns = strategy_buy_hold(prices)
    bh_metrics = compute_metrics(bh_returns, 1)

    if args.strategy == "buy_hold":
        strat_returns, trades = bh_returns, 1
        strat_label = "Buy & Hold"
    elif args.strategy == "sma_cross":
        strat_returns, trades = strategy_sma_cross(prices, args.fast, args.slow)
        strat_label = "SMA Cross (%d/%d)" % (args.fast, args.slow)
    elif args.strategy == "momentum":
        strat_returns, trades = strategy_momentum(prices, args.lookback)
        strat_label = "Momentum (%d day)" % args.lookback
    else:
        print("Unknown strategy: %s" % args.strategy, file=sys.stderr)
        sys.exit(1)

    strat_metrics = compute_metrics(strat_returns, trades)

    output = {
        "ticker": ticker,
        "strategy": strat_label,
        "period": {"start": args.start, "end": args.end},
        "strategy_metrics": strat_metrics,
        "benchmark_metrics": bh_metrics,
    }

    if args.format == "json":
        print(json.dumps(output, indent=2))
    else:
        print(format_text(ticker, strat_label, strat_metrics, bh_metrics))

    cache_path = os.path.join(DATA_DIR, "last_backtest.json")
    with open(cache_path, "w", encoding="utf-8") as fh:
        json.dump(output, fh, indent=2)
    print("Cached to: %s" % cache_path)


if __name__ == "__main__":
    main()
