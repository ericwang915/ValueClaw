#!/usr/bin/env python3
"""Real-time and historical FX rates for major currency pairs."""

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


DATA_DIR = os.path.expanduser("~/.value_claw/fx-rates")

DEFAULT_PAIRS = ["EURUSD", "GBPUSD", "USDJPY", "USDCHF", "AUDUSD", "USDCAD"]


def to_yf_symbol(pair: str) -> str:
    pair = pair.upper().replace("/", "")
    if not pair.endswith("=X"):
        pair = pair + "=X"
    return pair


def fetch_pair(pair: str, history: str | None = None) -> dict:
    symbol = to_yf_symbol(pair)
    ticker = yf.Ticker(symbol)
    info = ticker.info
    price = info.get("regularMarketPrice") or info.get("previousClose")
    prev_close = info.get("previousClose") or info.get("regularMarketPreviousClose")

    change = None
    change_pct = None
    if price is not None and prev_close is not None and prev_close != 0:
        change = round(price - prev_close, 6)
        change_pct = round(change / prev_close * 100, 4)

    result = {
        "pair": pair.upper().replace("/", "").replace("=X", ""),
        "symbol": symbol,
        "rate": price,
        "prev_close": prev_close,
        "change": change,
        "change_pct": change_pct,
        "day_high": info.get("dayHigh"),
        "day_low": info.get("dayLow"),
        "52w_high": info.get("fiftyTwoWeekHigh"),
        "52w_low": info.get("fiftyTwoWeekLow"),
    }

    if history:
        hist = ticker.history(period=history)
        if not hist.empty:
            records = []
            for date, row in hist.iterrows():
                records.append({
                    "date": date.strftime("%Y-%m-%d"),
                    "close": round(row["Close"], 6),
                })
            result["history"] = records

    return result


def format_text(results: list[dict]) -> str:
    lines = ["FX Rates", "=" * 55]
    for r in results:
        if "error" in r:
            lines.append(f"  {r['pair']}: ERROR - {r['error']}")
            continue
        sign = "+" if (r.get("change") or 0) >= 0 else ""
        chg = f"{sign}{r['change']}" if r.get("change") is not None else "N/A"
        pct = f"{sign}{r['change_pct']}%" if r.get("change_pct") is not None else ""
        lines.append(f"\n  {r['pair']}")
        lines.append(f"    Rate:       {r.get('rate', 'N/A')}")
        lines.append(f"    Change:     {chg} ({pct})")
        lines.append(f"    Day Range:  {r.get('day_low', '?')} - {r.get('day_high', '?')}")
        lines.append(f"    52w Range:  {r.get('52w_low', '?')} - {r.get('52w_high', '?')}")
        if r.get("history"):
            lines.append(f"    History ({len(r['history'])} points):")
            for h in r["history"][-5:]:
                lines.append(f"      {h['date']}: {h['close']}")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="FX rates for major currency pairs.")
    parser.add_argument("--pairs", nargs="+", default=DEFAULT_PAIRS, help="Currency pairs")
    parser.add_argument("--history", default=None, help="History period (1d,5d,1mo,3mo,6mo,1y)")
    parser.add_argument("--format", choices=["text", "json"], default="text")
    args = parser.parse_args()

    os.makedirs(DATA_DIR, exist_ok=True)
    results = []
    for pair in args.pairs:
        try:
            results.append(fetch_pair(pair, args.history))
        except Exception as exc:
            results.append({"pair": pair, "error": str(exc)})

    if args.format == "json":
        print(json.dumps(results, indent=2))
    else:
        print(format_text(results))


if __name__ == "__main__":
    main()
