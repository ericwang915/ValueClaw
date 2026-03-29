#!/usr/bin/env python3
"""In-depth commodity analysis with technicals and seasonal patterns."""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections import defaultdict

try:
    import yfinance as yf
except ImportError:
    print("Error: yfinance not installed. Run: pip install yfinance", file=sys.stderr)
    sys.exit(1)


DATA_DIR = os.path.expanduser("~/.value_claw/commodity-analysis")

COMMODITY_MAP = {
    "oil": {"symbol": "CL=F", "name": "WTI Crude Oil"},
    "gold": {"symbol": "GC=F", "name": "Gold"},
    "silver": {"symbol": "SI=F", "name": "Silver"},
    "copper": {"symbol": "HG=F", "name": "Copper"},
    "natgas": {"symbol": "NG=F", "name": "Natural Gas"},
    "corn": {"symbol": "ZC=F", "name": "Corn"},
    "wheat": {"symbol": "ZW=F", "name": "Wheat"},
    "soybeans": {"symbol": "ZS=F", "name": "Soybeans"},
}


def compute_rsi(closes: list[float], period: int = 14) -> float | None:
    if len(closes) < period + 1:
        return None
    deltas = [closes[i] - closes[i - 1] for i in range(1, len(closes))]
    recent = deltas[-period:]
    gains = [d for d in recent if d > 0]
    losses = [-d for d in recent if d < 0]
    avg_gain = sum(gains) / period if gains else 0
    avg_loss = sum(losses) / period if losses else 0
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return round(100 - (100 / (1 + rs)), 2)


def compute_sma(closes: list[float], period: int) -> float | None:
    if len(closes) < period:
        return None
    return round(sum(closes[-period:]) / period, 4)


def compute_volatility(closes: list[float], period: int = 20) -> float | None:
    if len(closes) < period + 1:
        return None
    returns = [
        (closes[i] / closes[i - 1]) - 1
        for i in range(len(closes) - period, len(closes))
    ]
    avg = sum(returns) / len(returns)
    var = sum((r - avg) ** 2 for r in returns) / len(returns)
    daily_vol = var ** 0.5
    return round(daily_vol * (252 ** 0.5) * 100, 2)


def compute_seasonal(hist) -> dict[int, float]:
    """Average monthly return over available history."""
    monthly_returns: dict[int, list[float]] = defaultdict(list)
    monthly = hist["Close"].resample("ME").last().dropna()
    values = monthly.tolist()
    indices = monthly.index.tolist()

    for i in range(1, len(values)):
        if values[i - 1] != 0:
            ret = (values[i] / values[i - 1] - 1) * 100
            month = indices[i].month
            monthly_returns[month].append(ret)

    return {
        m: round(sum(rets) / len(rets), 2)
        for m, rets in sorted(monthly_returns.items())
        if rets
    }


def analyze_commodity(key: str) -> dict:
    meta = COMMODITY_MAP[key]
    ticker = yf.Ticker(meta["symbol"])
    info = ticker.info
    price = info.get("regularMarketPrice") or info.get("previousClose")

    hist_1y = ticker.history(period="1y")
    hist_5y = ticker.history(period="5y")

    closes_1y = hist_1y["Close"].tolist() if not hist_1y.empty else []
    current = closes_1y[-1] if closes_1y else price

    seasonal = compute_seasonal(hist_5y) if not hist_5y.empty else {}

    return {
        "commodity": key,
        "name": meta["name"],
        "symbol": meta["symbol"],
        "price": round(current, 4) if current else None,
        "rsi_14": compute_rsi(closes_1y),
        "sma_20": compute_sma(closes_1y, 20),
        "sma_50": compute_sma(closes_1y, 50),
        "sma_200": compute_sma(closes_1y, 200),
        "hist_volatility_pct": compute_volatility(closes_1y),
        "52w_high": info.get("fiftyTwoWeekHigh"),
        "52w_low": info.get("fiftyTwoWeekLow"),
        "seasonal_avg_monthly_return_pct": seasonal,
    }


MONTH_NAMES = [
    "", "Jan", "Feb", "Mar", "Apr", "May", "Jun",
    "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
]


def format_text(data: dict) -> str:
    if "error" in data:
        return f"{data.get('name', data['commodity'])}: ERROR - {data['error']}"
    lines = [
        f"Commodity Analysis: {data['name']} ({data['symbol']})",
        "=" * 50,
        f"  Price:         {data.get('price', 'N/A')}",
        f"  52w Range:     {data.get('52w_low', '?')} - {data.get('52w_high', '?')}",
        "",
        "  Technical Indicators:",
        f"    RSI(14):     {data.get('rsi_14', 'N/A')}",
        f"    SMA(20):     {data.get('sma_20', 'N/A')}",
        f"    SMA(50):     {data.get('sma_50', 'N/A')}",
        f"    SMA(200):    {data.get('sma_200', 'N/A')}",
        f"    Volatility:  {data.get('hist_volatility_pct', 'N/A')}% annualized",
    ]

    seasonal = data.get("seasonal_avg_monthly_return_pct", {})
    if seasonal:
        lines.append("\n  Seasonal Pattern (avg monthly return, 5y):")
        for m, ret in seasonal.items():
            sign = "+" if ret >= 0 else ""
            bar = "*" * max(0, int(abs(ret) * 2))
            lines.append(f"    {MONTH_NAMES[m]:>3s}: {sign}{ret:>6.2f}%  {bar}")

    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="In-depth commodity analysis.")
    parser.add_argument(
        "--commodity", required=True, choices=list(COMMODITY_MAP.keys()),
        help="Commodity to analyze",
    )
    parser.add_argument("--format", choices=["text", "json"], default="text")
    args = parser.parse_args()

    os.makedirs(DATA_DIR, exist_ok=True)

    try:
        result = analyze_commodity(args.commodity)
    except Exception as exc:
        result = {"commodity": args.commodity, "name": COMMODITY_MAP[args.commodity]["name"], "error": str(exc)}

    if args.format == "json":
        print(json.dumps(result, indent=2))
    else:
        print(format_text(result))


if __name__ == "__main__":
    main()
