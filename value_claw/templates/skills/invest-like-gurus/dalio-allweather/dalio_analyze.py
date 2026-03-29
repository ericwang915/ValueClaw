#!/usr/bin/env python3
"""Ray Dalio All-Weather portfolio -- risk parity allocation and economic regime analysis."""

from __future__ import annotations

import argparse
import csv
import io
import json
from datetime import datetime, timezone

import requests

ENVIRONMENTS = {
    "rising_growth": ("Rising Growth", ["Stocks", "Corporate Bonds", "Commodities"]),
    "falling_growth": ("Falling Growth", ["Long Bonds", "TIPS"]),
    "rising_inflation": ("Rising Inflation", ["TIPS", "Commodities", "Gold"]),
    "falling_inflation": ("Falling Inflation", ["Stocks", "Long Bonds"]),
}

AW_TARGET = {"SPY": 0.30, "TLT": 0.40, "TIP": 0.15, "GLD": 0.075, "DBC": 0.075}

FRED_GDP = "https://fred.stlouisfed.org/graph/fredgraph.csv?id=A191RL1Q225SBEA&cosd=2020-01-01"
FRED_CPI = "https://fred.stlouisfed.org/graph/fredgraph.csv?id=CPIAUCSL&cosd=2020-01-01"


def fetch_asset_data(tickers: list[str]) -> dict[str, dict]:
    """Fetch performance data for each asset ETF."""
    try:
        import yfinance as yf
    except ImportError:
        return {t: {"error": "yfinance not installed"} for t in tickers}

    results = {}
    for ticker in tickers:
        try:
            hist = yf.Ticker(ticker).history(period="6mo")
            if hist.empty:
                results[ticker] = {"error": "No data"}
                continue
            cur = float(hist["Close"].iloc[-1])
            vol = float(hist["Close"].pct_change().std() * (252 ** 0.5) * 100)
            r1m = ((cur / float(hist["Close"].iloc[-21])) - 1) * 100 if len(hist) >= 21 else None
            r3m = ((cur / float(hist["Close"].iloc[-63])) - 1) * 100 if len(hist) >= 63 else None
            results[ticker] = {
                "ticker": ticker, "price": round(cur, 2),
                "annualizedVol": round(vol, 2),
                "return1m": round(r1m, 2) if r1m is not None else None,
                "return3m": round(r3m, 2) if r3m is not None else None,
            }
        except Exception as exc:
            results[ticker] = {"error": str(exc)}
    return results


def _fred(url: str) -> list[tuple[str, float]]:
    try:
        resp = requests.get(url, timeout=15)
        resp.raise_for_status()
        reader = csv.reader(io.StringIO(resp.text))
        next(reader)
        return [(r[0], float(r[1])) for r in reader if len(r) >= 2 and r[1] != "."]
    except Exception:
        return []


def detect_regime() -> dict:
    """Detect current economic regime from FRED data."""
    gdp = _fred(FRED_GDP)
    cpi = _fred(FRED_CPI)
    growth = "unknown"
    if len(gdp) >= 2:
        growth = "rising" if gdp[-1][1] > gdp[-2][1] else "falling"
    inflation = "unknown"
    current_yoy = None
    if len(cpi) >= 13:
        current_yoy = ((cpi[-1][1] - cpi[-13][1]) / cpi[-13][1]) * 100
        if len(cpi) >= 25:
            prior_yoy = ((cpi[-13][1] - cpi[-25][1]) / cpi[-25][1]) * 100
            inflation = "rising" if current_yoy > prior_yoy else "falling"
        else:
            inflation = "rising" if current_yoy > 3.0 else "falling"
    key = "%s_growth" % growth
    label, assets = ENVIRONMENTS.get(key, ENVIRONMENTS["rising_growth"])
    return {
        "growthTrend": growth, "inflationTrend": inflation,
        "inflationYoY": round(current_yoy, 2) if current_yoy else None,
        "regime": label, "favoredAssets": assets,
    }


def compute_risk_parity(asset_data: dict[str, dict]) -> dict[str, float]:
    """Compute simplified risk-parity weights (inverse volatility)."""
    inv = {t: 1.0 / d["annualizedVol"] for t, d in asset_data.items()
           if d.get("annualizedVol") and d["annualizedVol"] > 0}
    total = sum(inv.values())
    return {t: round(v / total, 4) for t, v in inv.items()} if total else {}


def format_text(assets: dict, regime: dict, rp: dict) -> str:
    """Render All-Weather analysis as readable text."""
    lines = ["Dalio All-Weather Analysis", "=" * 65,
             "Timestamp: %s\n" % datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")]
    lines.append("--- Economic Regime ---")
    lines.append("  Growth:     %s  |  Inflation: %s" % (regime["growthTrend"], regime["inflationTrend"]))
    if regime.get("inflationYoY") is not None:
        lines.append("  CPI YoY:    %.2f%%" % regime["inflationYoY"])
    lines.append("  Regime:     %s" % regime["regime"])
    lines.append("  Favored:    %s\n" % ", ".join(regime["favoredAssets"]))
    lines.append("%-6s %8s %8s %8s %8s" % ("Ticker", "Price", "1m Ret", "3m Ret", "Vol"))
    lines.append("-" * 46)
    for t, d in assets.items():
        if "error" in d:
            lines.append("%-6s ERROR: %s" % (t, d["error"]))
        else:
            lines.append("%-6s %8.2f %+7.2f%% %+7.2f%% %7.2f%%" % (
                t, d["price"], d.get("return1m") or 0, d.get("return3m") or 0, d["annualizedVol"]))
    lines.append("\n--- Risk-Parity vs All-Weather Target ---")
    lines.append("%-6s %10s %10s %10s" % ("Ticker", "RP Wt", "AW Target", "Diff"))
    for t in assets:
        r, tgt = rp.get(t, 0), AW_TARGET.get(t, 0)
        lines.append("%-6s %9.1f%% %9.1f%% %+9.1f%%" % (t, r * 100, tgt * 100, (r - tgt) * 100))
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Ray Dalio All-Weather portfolio analysis")
    parser.add_argument("--assets", nargs="+", default=["SPY", "TLT", "TIP", "GLD"])
    parser.add_argument("--format", choices=["text", "json"], default="text")
    args = parser.parse_args()
    tickers = [t.upper() for t in args.assets]
    assets = fetch_asset_data(tickers)
    regime = detect_regime()
    rp = compute_risk_parity(assets)
    if args.format == "json":
        print(json.dumps({"regime": regime, "assets": assets,
                          "riskParityWeights": rp, "allWeatherTarget": AW_TARGET}, indent=2, default=str))
    else:
        print(format_text(assets, regime, rp))


if __name__ == "__main__":
    main()
