#!/usr/bin/env python3
"""Sector rotation analysis — relative strength, momentum, business cycle."""

from __future__ import annotations

import argparse
import json
import sys

try:
    import yfinance as yf
except ImportError:
    print("Error: yfinance not installed.  Run: pip install yfinance", file=sys.stderr)
    sys.exit(1)

SECTORS = {
    "XLK": "Technology",
    "XLF": "Financials",
    "XLE": "Energy",
    "XLV": "Healthcare",
    "XLY": "Consumer Disc.",
    "XLP": "Consumer Staples",
    "XLI": "Industrials",
    "XLB": "Materials",
    "XLRE": "Real Estate",
    "XLC": "Communication",
    "XLU": "Utilities",
}

CYCLE_MAP = {
    "Early": ["XLF", "XLY", "XLRE", "XLI"],
    "Mid": ["XLK", "XLI", "XLB", "XLC"],
    "Late": ["XLE", "XLB", "XLP"],
    "Recession": ["XLU", "XLV", "XLP"],
}

PERIOD_MAP = {"1m": "1mo", "3m": "3mo", "6m": "6mo", "1y": "1y"}


def compute_rsi(closes, window: int = 14) -> float | None:
    """Compute RSI from a list of closing prices."""
    if len(closes) < window + 1:
        return None
    deltas = [closes[i] - closes[i - 1] for i in range(1, len(closes))]
    gains = [d if d > 0 else 0.0 for d in deltas[-window:]]
    losses = [-d if d < 0 else 0.0 for d in deltas[-window:]]
    avg_gain = sum(gains) / window
    avg_loss = sum(losses) / window
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return round(100 - (100 / (1 + rs)), 1)


def compute_returns(ticker: str, yf_period: str) -> dict:
    """Compute return and RSI for a sector ETF."""
    t = yf.Ticker(ticker)
    hist = t.history(period=yf_period)
    if hist.empty or len(hist) < 2:
        return {"return_pct": None, "rsi": None}
    closes = hist["Close"].tolist()
    ret = (closes[-1] - closes[0]) / closes[0] * 100
    rsi = compute_rsi(closes)
    return {"return_pct": round(ret, 2), "rsi": rsi, "last_price": round(closes[-1], 2)}


def analyze_sectors(period: str) -> list[dict]:
    """Analyze all sectors and compute relative strength vs SPY."""
    yf_period = PERIOD_MAP.get(period, "3mo")

    spy_data = compute_returns("SPY", yf_period)
    spy_ret = spy_data.get("return_pct") or 0.0

    results = []
    for etf, name in SECTORS.items():
        data = compute_returns(etf, yf_period)
        ret = data.get("return_pct")
        rel_strength = round(ret - spy_ret, 2) if ret is not None else None
        cycle_phases = [phase for phase, etfs in CYCLE_MAP.items() if etf in etfs]
        results.append({
            "etf": etf,
            "sector": name,
            "return_pct": ret,
            "relative_strength": rel_strength,
            "rsi": data.get("rsi"),
            "last_price": data.get("last_price"),
            "cycle_phases": cycle_phases,
        })

    results.sort(key=lambda x: x["return_pct"] or -999, reverse=True)

    for i, r in enumerate(results):
        r["rank"] = i + 1

    return results, spy_ret


def infer_cycle(results: list[dict]) -> str:
    """Infer business cycle phase from leading sectors."""
    top3_etfs = {r["etf"] for r in results[:3]}
    scores = {}
    for phase, etfs in CYCLE_MAP.items():
        overlap = len(top3_etfs & set(etfs))
        scores[phase] = overlap
    best = max(scores, key=scores.get)
    return best


def format_text(results: list[dict], spy_ret: float, period: str) -> str:
    lines = ["=" * 75, "  SECTOR ROTATION ANALYSIS (period: {})".format(period), "=" * 75, ""]
    lines.append("  SPY Return: {:.2f}%".format(spy_ret))
    lines.append("")
    hdr = "{:>4} {:<6} {:<18} {:>8} {:>10} {:>6} {:>8} {}".format(
        "Rank", "ETF", "Sector", "Return%", "RelStr%", "RSI", "Price", "Cycle")
    lines.append(hdr)
    lines.append("-" * 80)
    for r in results:
        ret = "{:.2f}".format(r["return_pct"]) if r["return_pct"] is not None else "N/A"
        rs = "{:+.2f}".format(r["relative_strength"]) if r["relative_strength"] is not None else "N/A"
        rsi = "{:.0f}".format(r["rsi"]) if r["rsi"] is not None else "N/A"
        price = "{:.2f}".format(r["last_price"]) if r["last_price"] else "N/A"
        cycle = "/".join(r["cycle_phases"]) if r["cycle_phases"] else "-"
        lines.append("{:>4} {:<6} {:<18} {:>8} {:>10} {:>6} {:>8} {}".format(
            r["rank"], r["etf"], r["sector"], ret, rs, rsi, price, cycle))

    phase = infer_cycle(results)
    lines.append("")
    lines.append("  Inferred Cycle Phase: {}".format(phase))
    lines.append("  Leading: {}".format(", ".join(r["sector"] for r in results[:3])))
    lines.append("  Lagging: {}".format(", ".join(r["sector"] for r in results[-3:])))
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Sector rotation analysis")
    parser.add_argument("--period", choices=["1m", "3m", "6m", "1y"], default="3m", help="Lookback period")
    parser.add_argument("--format", choices=["text", "json"], default="text", help="Output format")
    args = parser.parse_args()

    results, spy_ret = analyze_sectors(args.period)

    if args.format == "json":
        output = {
            "period": args.period,
            "spy_return_pct": spy_ret,
            "cycle_phase": infer_cycle(results),
            "sectors": results,
        }
        print(json.dumps(output, indent=2))
    else:
        print(format_text(results, spy_ret, args.period))


if __name__ == "__main__":
    main()
