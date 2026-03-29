#!/usr/bin/env python3
"""Technical and fundamental FX pair analysis with carry trade signals."""

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


DATA_DIR = os.path.expanduser("~/.value_claw/fx-analysis")

CENTRAL_BANK_RATES = {
    "USD": 5.25, "EUR": 4.25, "GBP": 5.00, "JPY": 0.25,
    "CHF": 1.50, "AUD": 4.35, "CAD": 4.50, "NZD": 5.50,
    "CNH": 3.45, "CNY": 3.45, "SEK": 3.50, "NOK": 4.50,
}


def to_yf_symbol(pair: str) -> str:
    pair = pair.upper().replace("/", "")
    if not pair.endswith("=X"):
        pair = pair + "=X"
    return pair


def compute_rsi(closes: list[float], period: int = 14) -> float | None:
    if len(closes) < period + 1:
        return None
    deltas = [closes[i] - closes[i - 1] for i in range(1, len(closes))]
    recent = deltas[-(period):]
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
    return round(sum(closes[-period:]) / period, 6)


def compute_bollinger(closes: list[float], period: int = 20, num_std: float = 2.0) -> dict | None:
    if len(closes) < period:
        return None
    window = closes[-period:]
    sma = sum(window) / period
    variance = sum((x - sma) ** 2 for x in window) / period
    std = variance ** 0.5
    return {
        "upper": round(sma + num_std * std, 6),
        "middle": round(sma, 6),
        "lower": round(sma - num_std * std, 6),
        "bandwidth": round((num_std * 2 * std) / sma * 100, 4),
    }


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


def analyze_pair(pair: str, period: str = "6mo") -> dict:
    raw = pair.upper().replace("/", "").replace("=X", "")
    base, quote = raw[:3], raw[3:]
    symbol = to_yf_symbol(raw)
    ticker = yf.Ticker(symbol)
    hist = ticker.history(period=period)

    if hist.empty:
        return {"pair": raw, "error": "No data returned"}

    closes = hist["Close"].tolist()
    current = closes[-1]
    info = ticker.info

    base_rate = CENTRAL_BANK_RATES.get(base)
    quote_rate = CENTRAL_BANK_RATES.get(quote)
    rate_diff = round(base_rate - quote_rate, 2) if base_rate is not None and quote_rate is not None else None

    carry_signal = None
    if rate_diff is not None:
        if rate_diff > 1.5:
            carry_signal = "Positive carry favors long"
        elif rate_diff < -1.5:
            carry_signal = "Positive carry favors short"
        else:
            carry_signal = "Neutral carry"

    return {
        "pair": raw,
        "current_rate": round(current, 6),
        "period": period,
        "data_points": len(closes),
        "rsi_14": compute_rsi(closes),
        "sma_20": compute_sma(closes, 20),
        "sma_50": compute_sma(closes, 50),
        "sma_200": compute_sma(closes, 200),
        "bollinger": compute_bollinger(closes),
        "hist_volatility_pct": compute_volatility(closes),
        "52w_high": info.get("fiftyTwoWeekHigh"),
        "52w_low": info.get("fiftyTwoWeekLow"),
        "base_currency": base,
        "quote_currency": quote,
        "base_rate_pct": base_rate,
        "quote_rate_pct": quote_rate,
        "rate_differential": rate_diff,
        "carry_signal": carry_signal,
    }


def format_text(data: dict) -> str:
    if "error" in data:
        return f"{data['pair']}: ERROR - {data['error']}"
    lines = [
        f"FX Analysis: {data['pair']}",
        "=" * 45,
        f"  Current Rate:   {data['current_rate']}",
        f"  Period:         {data['period']} ({data['data_points']} bars)",
        "",
        "  Technical Indicators:",
        f"    RSI(14):      {data.get('rsi_14', 'N/A')}",
        f"    SMA(20):      {data.get('sma_20', 'N/A')}",
        f"    SMA(50):      {data.get('sma_50', 'N/A')}",
        f"    SMA(200):     {data.get('sma_200', 'N/A')}",
    ]
    bb = data.get("bollinger")
    if bb:
        lines.append(f"    Bollinger:    {bb['lower']} / {bb['middle']} / {bb['upper']}")
        lines.append(f"    BB Width:     {bb['bandwidth']}%")
    lines.extend([
        f"    Volatility:   {data.get('hist_volatility_pct', 'N/A')}% annualized",
        f"    52w Range:    {data.get('52w_low', '?')} - {data.get('52w_high', '?')}",
        "",
        "  Carry Trade:",
        f"    {data['base_currency']} rate:  {data.get('base_rate_pct', 'N/A')}%",
        f"    {data['quote_currency']} rate:  {data.get('quote_rate_pct', 'N/A')}%",
        f"    Differential: {data.get('rate_differential', 'N/A')}%",
        f"    Signal:       {data.get('carry_signal', 'N/A')}",
    ])
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="FX technical and fundamental analysis.")
    parser.add_argument("--pair", required=True, help="Currency pair (e.g. EURUSD)")
    parser.add_argument("--period", default="6mo", help="Lookback period (1mo,3mo,6mo,1y)")
    parser.add_argument("--format", choices=["text", "json"], default="text")
    args = parser.parse_args()

    os.makedirs(DATA_DIR, exist_ok=True)
    result = analyze_pair(args.pair, args.period)

    if args.format == "json":
        print(json.dumps(result, indent=2))
    else:
        print(format_text(result))


if __name__ == "__main__":
    main()
