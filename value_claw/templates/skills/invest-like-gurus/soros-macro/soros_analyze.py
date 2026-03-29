#!/usr/bin/env python3
"""George Soros reflexivity and macro trading framework -- boom/bust cycle analysis."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone


def fetch_price_data(symbol: str) -> dict:
    """Fetch price history and compute momentum/volatility indicators."""
    try:
        import yfinance as yf
    except ImportError:
        return {"symbol": symbol, "error": "yfinance not installed"}

    try:
        asset = yf.Ticker(symbol)
        hist = asset.history(period="1y")
        info = asset.info or {}
    except Exception as exc:
        return {"symbol": symbol, "error": str(exc)}

    if hist.empty or len(hist) < 20:
        return {"symbol": symbol, "error": "Insufficient price data"}

    close = hist["Close"]
    current = float(close.iloc[-1])
    vol_30d = float(close.pct_change().dropna().iloc[-30:].std() * (252 ** 0.5) * 100)

    delta = close.diff()
    gain = delta.clip(lower=0).rolling(14).mean()
    loss = (-delta.clip(upper=0)).rolling(14).mean()
    rsi = float((100 - (100 / (1 + gain / loss))).iloc[-1])

    ma50 = float(close.rolling(50).mean().iloc[-1]) if len(close) >= 50 else None
    ma200 = float(close.rolling(200).mean().iloc[-1]) if len(close) >= 200 else None
    trend_strength = 0.0
    if ma50 is not None and ma200 is not None:
        spread = ((ma50 - ma200) / ma200) * 100
        trend_strength = min(abs(spread) * 3, 25)
        if spread < 0:
            trend_strength = -trend_strength
    ret_6m = ((current / float(close.iloc[-126])) - 1) * 100 if len(close) >= 126 else None

    return {
        "symbol": symbol.upper(), "name": info.get("shortName", symbol),
        "price": round(current, 2), "rsi14": round(rsi, 1),
        "volatility30d": round(vol_30d, 1),
        "ma50": round(ma50, 2) if ma50 else None,
        "ma200": round(ma200, 2) if ma200 else None,
        "return6m": round(ret_6m, 1) if ret_6m else None,
        "trendStrength": round(abs(trend_strength), 1),
        "trendDirection": "bullish" if trend_strength > 0 else "bearish",
    }


def fetch_macro_signals() -> dict:
    """Fetch VIX, DXY proxies for macro context."""
    try:
        import yfinance as yf
    except ImportError:
        return {}

    signals = {}
    try:
        vix_hist = yf.Ticker("^VIX").history(period="1y")
        if not vix_hist.empty:
            v = float(vix_hist["Close"].iloc[-1])
            signals["vix"] = round(v, 1)
            signals["vixPercentile"] = round((vix_hist["Close"] <= v).sum() / len(vix_hist) * 100, 0)
    except Exception:
        pass
    try:
        dh = yf.Ticker("UUP").history(period="6mo")
        if not dh.empty and len(dh) >= 21:
            cur, prev = float(dh["Close"].iloc[-1]), float(dh["Close"].iloc[-21])
            signals["dxyProxy"] = round(cur, 2)
            signals["dxyChange1m"] = round(((cur - prev) / prev) * 100, 2)
    except Exception:
        pass
    return signals


def compute_reflexivity_score(price_data: dict, macro: dict) -> dict:
    """Compute reflexivity risk score (0-100)."""
    bd = {"trendStrength": min(round(price_data.get("trendStrength", 0)), 25)}
    vix = macro.get("vix", 20)
    vol_signal = "low" if vix < 15 else ("elevated" if vix < 25 else "high")
    bd["leverageCreditConditions"] = 0
    bd["narrativeStrength"] = 0
    bd["policyResponseProbability"] = 0
    total = sum(bd.values())
    if total >= 75:
        regime = "LATE-STAGE BOOM / BUST RISK"
    elif total >= 50:
        regime = "ACTIVE REFLEXIVE TREND"
    elif total >= 25:
        regime = "MILD REFLEXIVITY"
    else:
        regime = "LOW REFLEXIVITY"
    return {
        "score": total, "maxScore": 100, "regime": regime,
        "volatilityRegime": vol_signal, "breakdown": bd,
        "note": "leverageCreditConditions, narrativeStrength, policyResponseProbability are LLM-evaluated (0-25 each).",
    }


def format_text(pd: dict, macro: dict, score: dict) -> str:
    """Render Soros reflexivity analysis as readable text."""
    lines = ["Soros Reflexivity Analysis", "=" * 60,
             "Timestamp: %s\n" % datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")]
    if "error" in pd:
        lines.append("ERROR: %s" % pd["error"])
        return "\n".join(lines)
    lines.append("--- %s (%s) ---" % (pd["symbol"], pd.get("name", "")))
    for label, key, sfx in [
        ("Price", "price", "$"), ("RSI(14)", "rsi14", ""), ("30d Vol", "volatility30d", "%"),
        ("50d MA", "ma50", "$"), ("200d MA", "ma200", "$"), ("6m Return", "return6m", "%"),
    ]:
        v = pd.get(key)
        lines.append("  %-14s %s%s" % (label, ("$" if sfx == "$" and v else ""), v if v is not None else "N/A"))
    lines.append("  Trend          %s (strength: %s/25)\n" % (pd["trendDirection"], pd["trendStrength"]))
    lines.append("--- Macro Context ---")
    lines.append("  VIX: %s (pctile: %s%%)  |  DXY: %s (1m: %s%%)" % (
        macro.get("vix", "N/A"), macro.get("vixPercentile", "N/A"),
        macro.get("dxyProxy", "N/A"), macro.get("dxyChange1m", "N/A")))
    lines.append("  Vol Regime: %s\n" % score["volatilityRegime"])
    lines.append("--- Reflexivity Score: %d/100 --- Regime: %s" % (score["score"], score["regime"]))
    for k, v in score["breakdown"].items():
        lines.append("  %-35s %d" % (k, v))
    lines.append("\nLLM-evaluated (0-25 each): leverageCreditConditions, narrativeStrength, policyResponseProbability")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Soros reflexivity and macro trading analysis")
    parser.add_argument("--market", default=None, help="Market index ETF (e.g., SPY)")
    parser.add_argument("--ticker", default=None, help="Individual stock ticker")
    parser.add_argument("--currency", default=None, help="Currency pair proxy (e.g., USDJPY)")
    parser.add_argument("--format", choices=["text", "json"], default="text")
    args = parser.parse_args()

    symbol = args.market or args.ticker
    if args.currency:
        symbol = "%s=X" % args.currency.upper()
    if not symbol:
        parser.print_help()
        print("\nSpecify --market, --ticker, or --currency", file=sys.stderr)
        sys.exit(1)

    pd = fetch_price_data(symbol)
    macro = fetch_macro_signals()
    score = compute_reflexivity_score(pd, macro)
    if args.format == "json":
        print(json.dumps({"priceData": pd, "macro": macro, "reflexivityScore": score}, indent=2, default=str))
    else:
        print(format_text(pd, macro, score))


if __name__ == "__main__":
    main()
