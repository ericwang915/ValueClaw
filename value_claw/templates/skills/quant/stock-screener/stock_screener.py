#!/usr/bin/env python3
"""Multi-criteria stock screener over a curated large-cap universe."""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime

DATA_DIR = os.path.expanduser("~/.value_claw/stock_screener")

UNIVERSE = [
    "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA", "BRK-B",
    "UNH", "JNJ", "V", "XOM", "JPM", "PG", "MA", "HD", "CVX", "MRK",
    "ABBV", "LLY", "PEP", "KO", "COST", "AVGO", "WMT", "MCD", "CSCO",
    "TMO", "ACN", "ABT", "DHR", "NEE", "LIN", "TXN", "PM", "UNP",
    "RTX", "LOW", "HON", "ORCL", "AMGN", "COP", "SBUX", "INTC",
    "IBM", "CAT", "BA", "GE", "AMD", "QCOM",
]


def _ensure_dir() -> None:
    os.makedirs(DATA_DIR, exist_ok=True)


def parse_cap(value: str) -> float | None:
    """Parse market cap string like '10B' or '500M' to a number."""
    if not value:
        return None
    value = value.strip().upper()
    multiplier = 1
    if value.endswith("B"):
        multiplier = 1e9
        value = value[:-1]
    elif value.endswith("M"):
        multiplier = 1e6
        value = value[:-1]
    elif value.endswith("T"):
        multiplier = 1e12
        value = value[:-1]
    try:
        return float(value) * multiplier
    except ValueError:
        return None


def fetch_metrics(ticker: str) -> dict | None:
    """Fetch key fundamental metrics for a single ticker."""
    try:
        import yfinance as yf
    except ImportError:
        print("yfinance not installed. Run: pip install yfinance", file=sys.stderr)
        sys.exit(1)

    try:
        info = yf.Ticker(ticker).info or {}
    except Exception:
        return None

    mcap = info.get("marketCap")
    if not mcap:
        return None

    return {
        "ticker": ticker,
        "name": info.get("shortName", ticker),
        "market_cap": mcap,
        "market_cap_b": round(mcap / 1e9, 1),
        "trailing_pe": info.get("trailingPE"),
        "forward_pe": info.get("forwardPE"),
        "revenue_growth_pct": round(info["revenueGrowth"] * 100, 1) if info.get("revenueGrowth") else None,
        "op_margin_pct": round(info["operatingMargins"] * 100, 1) if info.get("operatingMargins") else None,
        "gross_margin_pct": round(info["grossMargins"] * 100, 1) if info.get("grossMargins") else None,
        "dividend_yield_pct": round(info["dividendYield"] * 100, 2) if info.get("dividendYield") else None,
        "sector": info.get("sector", ""),
    }


def compute_score(m: dict) -> float:
    """Composite score: higher is better. Blend of growth, margin, inverse PE."""
    score = 0.0
    growth = m.get("revenue_growth_pct")
    if growth is not None and growth > 0:
        score += min(growth, 50)
    margin = m.get("op_margin_pct")
    if margin is not None and margin > 0:
        score += min(margin, 40)
    pe = m.get("trailing_pe")
    if pe is not None and pe > 0:
        score += max(0, 30 - pe)
    return round(score, 2)


def format_text(results: list[dict]) -> str:
    """Render screener results as a text table."""
    lines = [
        "=" * 90,
        "  STOCK SCREENER RESULTS (%d matches)" % len(results),
        "  Generated: %s" % datetime.now().strftime("%Y-%m-%d %H:%M"),
        "=" * 90,
        "",
        "%-7s %-18s %8s %8s %8s %8s %7s" % (
            "Ticker", "Name", "Cap($B)", "P/E", "Grw%", "Mgn%", "Score"),
        "-" * 90,
    ]
    for r in results:
        pe_str = ("%.1f" % r["trailing_pe"]) if r.get("trailing_pe") else "N/A"
        gr_str = ("%.1f" % r["revenue_growth_pct"]) if r.get("revenue_growth_pct") is not None else "N/A"
        mg_str = ("%.1f" % r["op_margin_pct"]) if r.get("op_margin_pct") is not None else "N/A"
        lines.append(
            "%-7s %-18s %8.1f %8s %8s %8s %7.1f"
            % (r["ticker"], r["name"][:18], r["market_cap_b"], pe_str, gr_str, mg_str, r["score"])
        )
    lines.append("-" * 90)
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Multi-Criteria Stock Screener")
    parser.add_argument("--max-pe", type=float, default=None)
    parser.add_argument("--min-growth", type=float, default=None)
    parser.add_argument("--min-margin", type=float, default=None)
    parser.add_argument("--min-cap", default=None, help="e.g. 10B")
    parser.add_argument("--max-cap", default=None, help="e.g. 500B")
    parser.add_argument("--sort-by", default="score",
                        choices=["score", "pe", "growth", "margin"])
    parser.add_argument("--format", choices=["text", "json"], default="text")
    args = parser.parse_args()

    _ensure_dir()
    min_cap = parse_cap(args.min_cap) if args.min_cap else None
    max_cap = parse_cap(args.max_cap) if args.max_cap else None

    print("Screening %d stocks..." % len(UNIVERSE))
    results: list[dict] = []
    for i, ticker in enumerate(UNIVERSE):
        sys.stdout.write("\r  [%d/%d] %s...   " % (i + 1, len(UNIVERSE), ticker))
        sys.stdout.flush()
        m = fetch_metrics(ticker)
        if m is None:
            continue
        if args.max_pe and m.get("trailing_pe") and m["trailing_pe"] > args.max_pe:
            continue
        if args.min_growth and (m.get("revenue_growth_pct") is None or m["revenue_growth_pct"] < args.min_growth):
            continue
        if args.min_margin and (m.get("op_margin_pct") is None or m["op_margin_pct"] < args.min_margin):
            continue
        if min_cap and m["market_cap"] < min_cap:
            continue
        if max_cap and m["market_cap"] > max_cap:
            continue
        m["score"] = compute_score(m)
        results.append(m)

    print("\r  Screening complete. %d matches found.       " % len(results))

    sort_keys = {"score": "score", "pe": "trailing_pe", "growth": "revenue_growth_pct", "margin": "op_margin_pct"}
    key = sort_keys[args.sort_by]
    results.sort(key=lambda r: r.get(key) or 0, reverse=(args.sort_by != "pe"))

    if args.format == "json":
        print(json.dumps(results, indent=2))
    else:
        print(format_text(results))

    cache_path = os.path.join(DATA_DIR, "last_screen.json")
    with open(cache_path, "w", encoding="utf-8") as fh:
        json.dump(results, fh, indent=2)
    print("Cached to: %s" % cache_path)


if __name__ == "__main__":
    main()
