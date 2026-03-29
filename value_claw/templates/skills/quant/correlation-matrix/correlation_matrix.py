#!/usr/bin/env python3
"""Asset correlation matrix — compute and optionally visualize as heatmap."""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime

import numpy as np

DATA_DIR = os.path.expanduser("~/.value_claw/correlation_matrix")


def _ensure_dir() -> None:
    os.makedirs(DATA_DIR, exist_ok=True)


def fetch_returns(tickers: list[str], period: str) -> tuple[list[str], dict[str, np.ndarray]]:
    """Fetch daily returns for multiple tickers. Returns (common_dates, {ticker: returns})."""
    try:
        import yfinance as yf
    except ImportError:
        print("yfinance not installed. Run: pip install yfinance", file=sys.stderr)
        sys.exit(1)

    price_data: dict[str, dict[str, float]] = {}
    for ticker in tickers:
        df = yf.download(ticker, period=period, progress=False)
        if df.empty:
            print("Warning: no data for %s, skipping." % ticker, file=sys.stderr)
            continue
        closes = {}
        for idx, row in df.iterrows():
            date_str = idx.strftime("%Y-%m-%d")
            val = row["Close"]
            if hasattr(val, "item"):
                val = val.item()
            closes[date_str] = float(val)
        price_data[ticker] = closes

    if len(price_data) < 2:
        print("Need at least 2 tickers with data.", file=sys.stderr)
        sys.exit(1)

    all_dates = set.intersection(*(set(d.keys()) for d in price_data.values()))
    common_dates = sorted(all_dates)

    returns: dict[str, np.ndarray] = {}
    for ticker, closes in price_data.items():
        prices = np.array([closes[d] for d in common_dates])
        daily_ret = np.diff(prices) / prices[:-1]
        returns[ticker] = daily_ret

    return common_dates[1:], returns


def compute_correlation(returns: dict[str, np.ndarray]) -> tuple[list[str], np.ndarray]:
    """Compute correlation matrix from returns dict."""
    tickers = list(returns.keys())
    matrix = np.column_stack([returns[t] for t in tickers])
    corr = np.corrcoef(matrix, rowvar=False)
    return tickers, corr


def generate_heatmap(tickers: list[str], corr: np.ndarray, path: str) -> None:
    """Generate and save a correlation heatmap PNG."""
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        print("matplotlib not installed. Run: pip install matplotlib", file=sys.stderr)
        return

    fig, ax = plt.subplots(figsize=(max(6, len(tickers)), max(5, len(tickers) - 1)))
    im = ax.imshow(corr, cmap="RdYlGn", vmin=-1, vmax=1)
    ax.set_xticks(range(len(tickers)))
    ax.set_yticks(range(len(tickers)))
    ax.set_xticklabels(tickers, rotation=45, ha="right")
    ax.set_yticklabels(tickers)

    for i in range(len(tickers)):
        for j in range(len(tickers)):
            ax.text(j, i, "%.2f" % corr[i, j], ha="center", va="center",
                    color="black", fontsize=8)

    fig.colorbar(im)
    ax.set_title("Return Correlation Matrix")
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)
    print("Heatmap saved to: %s" % path)


def format_text(tickers: list[str], corr: np.ndarray, period: str) -> str:
    """Render correlation matrix as a text table."""
    col_w = 8
    lines = [
        "=" * (10 + col_w * len(tickers)),
        "  CORRELATION MATRIX (daily returns, period: %s)" % period,
        "  Generated: %s" % datetime.now().strftime("%Y-%m-%d %H:%M"),
        "=" * (10 + col_w * len(tickers)),
        "",
    ]

    header = "%-8s" % "" + "".join("%8s" % t for t in tickers)
    lines.append(header)
    lines.append("-" * len(header))

    for i, t in enumerate(tickers):
        row_str = "%-8s" % t
        for j in range(len(tickers)):
            row_str += "%8.3f" % corr[i][j]
        lines.append(row_str)

    lines.append("")

    pairs = []
    for i in range(len(tickers)):
        for j in range(i + 1, len(tickers)):
            pairs.append((tickers[i], tickers[j], corr[i][j]))
    pairs.sort(key=lambda x: x[2])

    lines.append("  Most correlated:  %s / %s (%.3f)" % (pairs[-1][0], pairs[-1][1], pairs[-1][2]))
    lines.append("  Least correlated: %s / %s (%.3f)" % (pairs[0][0], pairs[0][1], pairs[0][2]))
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Asset Correlation Matrix")
    parser.add_argument("--tickers", nargs="+", required=True, help="Tickers (at least 2)")
    parser.add_argument("--period", default="1y", help="Lookback period (e.g. 1y, 6mo)")
    parser.add_argument("--chart", action="store_true", help="Generate heatmap PNG")
    parser.add_argument("--format", choices=["text", "json"], default="text")
    args = parser.parse_args()

    if len(args.tickers) < 2:
        print("Need at least 2 tickers.", file=sys.stderr)
        sys.exit(1)

    _ensure_dir()
    tickers_upper = [t.upper() for t in args.tickers]
    print("Fetching daily returns for %d tickers (period: %s)..." % (len(tickers_upper), args.period))
    dates, returns = fetch_returns(tickers_upper, args.period)
    print("  %d common trading days." % len(dates))

    tickers_out, corr = compute_correlation(returns)

    if args.chart:
        chart_path = os.path.join(DATA_DIR, "heatmap.png")
        generate_heatmap(tickers_out, corr, chart_path)

    if args.format == "json":
        output = {
            "tickers": tickers_out,
            "period": args.period,
            "observations": len(dates),
            "matrix": [[round(float(corr[i][j]), 4) for j in range(len(tickers_out))]
                       for i in range(len(tickers_out))],
        }
        print(json.dumps(output, indent=2))
    else:
        print(format_text(tickers_out, corr, args.period))

    cache_path = os.path.join(DATA_DIR, "last_correlation.json")
    with open(cache_path, "w", encoding="utf-8") as fh:
        json.dump({
            "tickers": tickers_out,
            "period": args.period,
            "observations": len(dates),
            "matrix": corr.tolist(),
        }, fh, indent=2)
    print("Cached to: %s" % cache_path)


if __name__ == "__main__":
    main()
