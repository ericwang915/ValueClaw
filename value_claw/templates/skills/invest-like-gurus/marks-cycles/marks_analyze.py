#!/usr/bin/env python3
"""Howard Marks cycle analysis -- market temperature gauge and pendulum positioning."""

from __future__ import annotations

import argparse
import csv
import io
import json
from datetime import datetime, timezone

import requests

FRED_HY_OAS = "https://fred.stlouisfed.org/graph/fredgraph.csv?id=BAMLH0A0HYM2&cosd=2015-01-01"

ZONES = [
    (80, "EUPHORIA", "Extreme greed -- time to be defensive"),
    (60, "OPTIMISM", "Above-average enthusiasm -- reduce risk"),
    (40, "NEUTRAL", "Fair pricing -- stay disciplined"),
    (20, "CAUTION", "Below-average sentiment -- lean bullish"),
    (0, "FEAR", "Extreme pessimism -- time to be aggressive"),
]


def fetch_market_data(index: str) -> dict:
    """Fetch market data for temperature gauge inputs."""
    try:
        import yfinance as yf
    except ImportError:
        return {"error": "yfinance not installed"}
    data = {}
    try:
        idx = yf.Ticker(index)
        info = idx.info or {}
        hist = idx.history(period="2y")
        data["price"] = round(float(info.get("currentPrice") or info.get("regularMarketPrice")
                                     or info.get("previousClose", 0)), 2)
        data["pe"] = info.get("trailingPE")
        data["forwardPE"] = info.get("forwardPE")
        if not hist.empty and len(hist) >= 252:
            data["return1y"] = round((float(hist["Close"].iloc[-1]) / float(hist["Close"].iloc[-252]) - 1) * 100, 1)
    except Exception:
        pass
    try:
        vh = yf.Ticker("^VIX").history(period="2y")
        if not vh.empty:
            v = float(vh["Close"].iloc[-1])
            data["vix"] = round(v, 1)
            data["vixPercentile"] = round((vh["Close"] <= v).sum() / len(vh) * 100, 0)
    except Exception:
        pass
    try:
        v9 = yf.Ticker("^VIX9D").history(period="5d")
        if not v9.empty and data.get("vix"):
            data["vixTermSpread"] = round(data["vix"] - float(v9["Close"].iloc[-1]), 2)
    except Exception:
        pass
    try:
        th = yf.Ticker("TQQQ").history(period="3mo")
        if not th.empty and len(th) >= 20:
            recent = float(th["Volume"].iloc[-5:].mean())
            avg = float(th["Volume"].iloc[:-5].mean())
            if avg > 0:
                data["leveragedETFRelVol"] = round(recent / avg, 2)
    except Exception:
        pass
    return data


def fetch_credit_spreads() -> float | None:
    try:
        resp = requests.get(FRED_HY_OAS, timeout=15)
        resp.raise_for_status()
        reader = csv.reader(io.StringIO(resp.text))
        next(reader)
        rows = [(r[0], r[1]) for r in reader if len(r) >= 2 and r[1] != "."]
        return float(rows[-1][1]) if rows else None
    except Exception:
        return None


def compute_temperature(data: dict, hy_oas: float | None) -> dict:
    """Compute Market Temperature (0-100) from multiple inputs."""
    sc = {}
    sc["vixSignal"] = round(min(max(100 - data.get("vixPercentile", 50), 0), 100))
    pe = data.get("pe")
    sc["valuation"] = (90 if pe and pe > 30 else 75 if pe and pe > 25
                       else 55 if pe and pe > 20 else 35 if pe and pe > 15 else 15) if pe else 50
    sc["creditSpreads"] = (85 if hy_oas and hy_oas < 3 else 65 if hy_oas and hy_oas < 4
                           else 45 if hy_oas and hy_oas < 5 else 25 if hy_oas and hy_oas < 7
                           else 10) if hy_oas else 50
    lv = data.get("leveragedETFRelVol", 1.0)
    sc["leverageProxy"] = 80 if lv > 1.5 else 60 if lv > 1.2 else 40 if lv > 0.8 else 20

    temp = round(sum(sc.values()) / len(sc))
    zone, pendulum = "NEUTRAL", "Fair pricing -- stay disciplined"
    for threshold, z, p in ZONES:
        if temp >= threshold:
            zone, pendulum = z, p
            break

    contrarian = []
    if temp >= 75:
        contrarian = ["Reduce equity exposure", "Raise cash / increase quality", "Avoid leveraged positions"]
    elif temp <= 25:
        contrarian = ["Increase equity exposure", "Buy quality at distressed prices", "Deploy cash reserves"]

    return {
        "temperature": temp, "zone": zone, "pendulum": pendulum,
        "componentScores": sc, "contrarianSignals": contrarian,
        "hyOAS": round(hy_oas, 2) if hy_oas else None,
    }


def format_text(index: str, data: dict, temp: dict) -> str:
    lines = ["Howard Marks Market Cycle Analysis", "=" * 60,
             "Timestamp: %s  |  Index: %s\n" % (datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"), index)]
    lines.append("--- Market Temperature: %d/100 ---" % temp["temperature"])
    lines.append("  Zone:     %s" % temp["zone"])
    lines.append("  Pendulum: %s\n" % temp["pendulum"])
    lines.append("--- Inputs ---")
    for label, key in [("Price", "price"), ("P/E", "pe"), ("Fwd P/E", "forwardPE"),
                       ("1Y Return", "return1y"), ("VIX", "vix"), ("VIX Pctile", "vixPercentile"),
                       ("Lev ETF rVol", "leveragedETFRelVol")]:
        lines.append("  %-14s %s" % (label, data.get(key, "N/A")))
    lines.append("  HY Spread      %s%%" % (temp.get("hyOAS") or "N/A"))
    lines.append("\n--- Component Scores ---")
    for k, v in temp["componentScores"].items():
        lines.append("  %-20s %d/100" % (k, v))
    if temp["contrarianSignals"]:
        lines.append("\n--- Contrarian Signals ---")
        for s in temp["contrarianSignals"]:
            lines.append("  * %s" % s)
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Howard Marks cycle analysis -- market temperature gauge")
    parser.add_argument("--index", default="SPY", help="Market index ETF (default: SPY)")
    parser.add_argument("--format", choices=["text", "json"], default="text")
    args = parser.parse_args()
    index = args.index.upper()
    md = fetch_market_data(index)
    hy = fetch_credit_spreads()
    temp = compute_temperature(md, hy)
    if args.format == "json":
        print(json.dumps({"index": index, "marketData": md, "temperature": temp}, indent=2, default=str))
    else:
        print(format_text(index, md, temp))


if __name__ == "__main__":
    main()
