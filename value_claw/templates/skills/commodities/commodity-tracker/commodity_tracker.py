#!/usr/bin/env python3
"""Track prices for major commodities via yfinance futures data."""

from __future__ import annotations

import argparse
import json
import os
import sys

try:
    import yfinance as yf
except ImportError:
    print("Error: yfinance not installed. Run: pip install yfinance", file=sys.stderr)
    sys.exit(1)


DATA_DIR = os.path.expanduser("~/.value_claw/commodity-tracker")

COMMODITY_MAP = {
    "oil": {"symbol": "CL=F", "name": "WTI Crude Oil", "unit": "$/bbl"},
    "gold": {"symbol": "GC=F", "name": "Gold", "unit": "$/oz"},
    "silver": {"symbol": "SI=F", "name": "Silver", "unit": "$/oz"},
    "copper": {"symbol": "HG=F", "name": "Copper", "unit": "$/lb"},
    "natgas": {"symbol": "NG=F", "name": "Natural Gas", "unit": "$/MMBtu"},
    "corn": {"symbol": "ZC=F", "name": "Corn", "unit": "c/bu"},
    "wheat": {"symbol": "ZW=F", "name": "Wheat", "unit": "c/bu"},
    "soybeans": {"symbol": "ZS=F", "name": "Soybeans", "unit": "c/bu"},
}


def pct_change(current: float, previous: float) -> float | None:
    if previous and previous != 0:
        return round((current / previous - 1) * 100, 2)
    return None


def fetch_commodity(key: str) -> dict:
    meta = COMMODITY_MAP[key]
    ticker = yf.Ticker(meta["symbol"])
    info = ticker.info
    price = info.get("regularMarketPrice") or info.get("previousClose")

    hist_1y = ticker.history(period="1y")
    hist_ytd = ticker.history(period="ytd")

    daily_chg = None
    weekly_chg = None
    monthly_chg = None
    ytd_chg = None

    if not hist_1y.empty:
        closes = hist_1y["Close"].tolist()
        if len(closes) >= 2:
            daily_chg = pct_change(closes[-1], closes[-2])
        if len(closes) >= 5:
            weekly_chg = pct_change(closes[-1], closes[-5])
        if len(closes) >= 21:
            monthly_chg = pct_change(closes[-1], closes[-21])

    if not hist_ytd.empty:
        ytd_closes = hist_ytd["Close"].tolist()
        if len(ytd_closes) >= 2:
            ytd_chg = pct_change(ytd_closes[-1], ytd_closes[0])

    return {
        "key": key,
        "name": meta["name"],
        "symbol": meta["symbol"],
        "unit": meta["unit"],
        "price": round(price, 2) if price else None,
        "daily_chg_pct": daily_chg,
        "weekly_chg_pct": weekly_chg,
        "monthly_chg_pct": monthly_chg,
        "ytd_chg_pct": ytd_chg,
        "52w_high": info.get("fiftyTwoWeekHigh"),
        "52w_low": info.get("fiftyTwoWeekLow"),
    }


def format_text(results: list[dict]) -> str:
    lines = ["Commodity Tracker", "=" * 65]
    header = f"  {'Name':<20s} {'Price':>10s} {'Daily':>8s} {'Week':>8s} {'Month':>8s} {'YTD':>8s}"
    lines.append(header)
    lines.append("  " + "-" * 62)
    for r in results:
        if "error" in r:
            lines.append(f"  {r.get('name', r['key']):<20s} ERROR: {r['error']}")
            continue
        p = f"{r['price']}" if r.get("price") is not None else "N/A"
        d = f"{r['daily_chg_pct']:+.2f}%" if r.get("daily_chg_pct") is not None else "N/A"
        w = f"{r['weekly_chg_pct']:+.2f}%" if r.get("weekly_chg_pct") is not None else "N/A"
        m = f"{r['monthly_chg_pct']:+.2f}%" if r.get("monthly_chg_pct") is not None else "N/A"
        y = f"{r['ytd_chg_pct']:+.2f}%" if r.get("ytd_chg_pct") is not None else "N/A"
        lines.append(f"  {r['name']:<20s} {p:>10s} {d:>8s} {w:>8s} {m:>8s} {y:>8s}")
    lines.append("")
    for r in results:
        if "error" not in r and r.get("52w_low") is not None:
            lines.append(
                f"  {r['name']}: 52w {r['52w_low']} - {r['52w_high']} {r['unit']}"
            )
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Commodity price tracker.")
    parser.add_argument(
        "--commodities", nargs="+", choices=list(COMMODITY_MAP.keys()),
        help="Commodities to track",
    )
    parser.add_argument("--all", action="store_true", help="Track all commodities")
    parser.add_argument("--format", choices=["text", "json"], default="text")
    args = parser.parse_args()

    if not args.commodities and not args.all:
        args.all = True

    keys = list(COMMODITY_MAP.keys()) if args.all else args.commodities
    os.makedirs(DATA_DIR, exist_ok=True)

    results = []
    for key in keys:
        try:
            results.append(fetch_commodity(key))
        except Exception as exc:
            results.append({"key": key, "name": COMMODITY_MAP[key]["name"], "error": str(exc)})

    if args.format == "json":
        print(json.dumps(results, indent=2))
    else:
        print(format_text(results))


if __name__ == "__main__":
    main()
