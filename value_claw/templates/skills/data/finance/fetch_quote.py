#!/usr/bin/env python3
"""Fetch financial quotes from Yahoo Finance."""

import argparse
import json
import sys

try:
    import yfinance as yf
except ImportError:
    print("Error: yfinance not installed.  Run: pip install yfinance", file=sys.stderr)
    sys.exit(1)


def fetch_quote(symbol: str, history: str | None = None) -> dict:
    ticker = yf.Ticker(symbol)
    info = ticker.info

    result = {
        "symbol": symbol.upper(),
        "name": info.get("shortName") or info.get("longName", symbol),
        "price": info.get("currentPrice") or info.get("regularMarketPrice"),
        "currency": info.get("currency", "USD"),
        "change": info.get("regularMarketChange"),
        "changePercent": info.get("regularMarketChangePercent"),
        "dayHigh": info.get("dayHigh"),
        "dayLow": info.get("dayLow"),
        "volume": info.get("volume"),
        "marketCap": info.get("marketCap"),
        "fiftyTwoWeekHigh": info.get("fiftyTwoWeekHigh"),
        "fiftyTwoWeekLow": info.get("fiftyTwoWeekLow"),
    }

    if history:
        hist = ticker.history(period=history)
        if not hist.empty:
            records = []
            for date, row in hist.iterrows():
                records.append({
                    "date": date.strftime("%Y-%m-%d"),
                    "close": round(row["Close"], 2),
                    "volume": int(row["Volume"]),
                })
            result["history"] = records

    return result


def format_text(data: dict) -> str:
    lines = [f"{data['name']} ({data['symbol']})"]
    price = data.get("price")
    if price is not None:
        ccy = data.get("currency", "")
        change = data.get("change")
        pct = data.get("changePercent")
        change_str = ""
        if change is not None and pct is not None:
            sign = "+" if change >= 0 else ""
            change_str = f"  {sign}{change:.2f} ({sign}{pct:.2f}%)"
        lines.append(f"  Price: {ccy} {price:.2f}{change_str}")

    for label, key in [("Day Range", None), ("52-Week", None),
                       ("Volume", "volume"), ("Market Cap", "marketCap")]:
        if key and data.get(key) is not None:
            val = data[key]
            if val >= 1e12:
                lines.append(f"  {label}: {val/1e12:.2f}T")
            elif val >= 1e9:
                lines.append(f"  {label}: {val/1e9:.2f}B")
            elif val >= 1e6:
                lines.append(f"  {label}: {val/1e6:.2f}M")
            else:
                lines.append(f"  {label}: {val:,.0f}")

    lo, hi = data.get("dayLow"), data.get("dayHigh")
    if lo and hi:
        lines.append(f"  Day Range: {lo:.2f} - {hi:.2f}")

    lo52, hi52 = data.get("fiftyTwoWeekLow"), data.get("fiftyTwoWeekHigh")
    if lo52 and hi52:
        lines.append(f"  52-Week: {lo52:.2f} - {hi52:.2f}")

    if "history" in data:
        lines.append(f"  History ({len(data['history'])} points):")
        for h in data["history"][-5:]:
            lines.append(f"    {h['date']}: {h['close']}")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Fetch financial quotes.")
    parser.add_argument("symbols", nargs="+", help="Ticker symbols (e.g. TSLA AAPL BTC-USD)")
    parser.add_argument("--format", choices=["text", "json"], default="text")
    parser.add_argument("--history", default=None, help="Price history period (1d,5d,1mo,3mo,6mo,1y,5y,max)")
    args = parser.parse_args()

    results = []
    for sym in args.symbols:
        try:
            data = fetch_quote(sym.strip(), history=args.history)
            results.append(data)
        except Exception as exc:
            results.append({"symbol": sym, "error": str(exc)})

    if args.format == "json":
        print(json.dumps(results, indent=2))
    else:
        for data in results:
            if "error" in data:
                print(f"{data['symbol']}: Error — {data['error']}")
            else:
                print(format_text(data))
            print()


if __name__ == "__main__":
    main()
