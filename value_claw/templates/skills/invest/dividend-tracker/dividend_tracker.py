#!/usr/bin/env python3
"""Dividend analysis — yield, growth, payout ratio, ex-dates, aristocrats."""

from __future__ import annotations

import argparse
import datetime
import json
import sys

try:
    import yfinance as yf
except ImportError:
    print("Error: yfinance not installed.  Run: pip install yfinance", file=sys.stderr)
    sys.exit(1)

ARISTOCRATS = [
    "JNJ", "KO", "PG", "PEP", "MMM", "ABT", "ABBV", "CL", "EMR", "GPC",
    "ITW", "SWK", "BDX", "TGT", "WMT", "MCD", "SYY", "AFL", "ADP", "ED",
    "XOM", "CVX", "LOW", "SHW", "CB", "BEN", "CAT", "DOV", "HRL", "NUE",
]


def compute_div_cagr(dividends, years: int = 5) -> float | None:
    """Compute annualized dividend growth rate over the given period."""
    if dividends is None or dividends.empty:
        return None
    cutoff = datetime.datetime.now() - datetime.timedelta(days=years * 365)
    recent = dividends[dividends.index >= cutoff]
    if len(recent) < 2:
        return None
    annual = recent.resample("YE").sum()
    annual = annual[annual > 0]
    if len(annual) < 2:
        return None
    first_val = float(annual.iloc[0])
    last_val = float(annual.iloc[-1])
    if first_val <= 0:
        return None
    n = len(annual) - 1
    return (pow(last_val / first_val, 1.0 / n) - 1) * 100


def analyze_ticker(symbol: str) -> dict:
    """Fetch dividend data for a single ticker."""
    t = yf.Ticker(symbol)
    info = t.info
    divs = t.dividends

    annual_div = info.get("dividendRate")
    div_yield = info.get("dividendYield")
    payout = info.get("payoutRatio")
    ex_date_ts = info.get("exDividendDate")

    ex_date = None
    if ex_date_ts:
        try:
            ex_date = datetime.datetime.fromtimestamp(ex_date_ts).strftime("%Y-%m-%d")
        except (TypeError, OSError):
            pass

    cagr_5y = compute_div_cagr(divs, years=5)
    is_aristocrat = symbol.upper() in ARISTOCRATS

    consecutive = 0
    if divs is not None and not divs.empty:
        annual = divs.resample("YE").sum()
        annual = annual[annual > 0]
        if len(annual) >= 2:
            for i in range(len(annual) - 1, 0, -1):
                if float(annual.iloc[i]) >= float(annual.iloc[i - 1]):
                    consecutive += 1
                else:
                    break

    return {
        "symbol": symbol.upper(),
        "name": info.get("shortName", symbol),
        "price": info.get("currentPrice") or info.get("regularMarketPrice"),
        "annual_dividend": round(annual_div, 4) if annual_div else None,
        "dividend_yield_pct": round(div_yield * 100, 2) if div_yield else None,
        "payout_ratio_pct": round(payout * 100, 1) if payout else None,
        "ex_dividend_date": ex_date,
        "cagr_5y_pct": round(cagr_5y, 2) if cagr_5y is not None else None,
        "consecutive_increase_years": consecutive,
        "is_aristocrat": is_aristocrat,
    }


def format_text(results: list[dict]) -> str:
    lines = ["=" * 60, "  DIVIDEND ANALYSIS", "=" * 60, ""]
    hdr = "{:<7} {:<18} {:>7} {:>8} {:>8} {:>8} {:>12} {:>5}".format(
        "Ticker", "Name", "Yield%", "Annual", "Payout%", "CAGR5Y", "Ex-Date", "Arst")
    lines.append(hdr)
    lines.append("-" * 85)
    for r in results:
        yld = "{:.2f}".format(r["dividend_yield_pct"]) if r["dividend_yield_pct"] else "N/A"
        ann = "{:.2f}".format(r["annual_dividend"]) if r["annual_dividend"] else "N/A"
        pay = "{:.1f}".format(r["payout_ratio_pct"]) if r["payout_ratio_pct"] else "N/A"
        cagr = "{:.1f}".format(r["cagr_5y_pct"]) if r["cagr_5y_pct"] is not None else "N/A"
        ex_d = r["ex_dividend_date"] or "N/A"
        arst = "Yes" if r["is_aristocrat"] else "No"
        lines.append("{:<7} {:<18} {:>7} {:>8} {:>8} {:>8} {:>12} {:>5}".format(
            r["symbol"], r["name"][:17], yld, ann, pay, cagr, ex_d, arst))
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Dividend analysis and aristocrats screening")
    parser.add_argument("--tickers", nargs="+", required=True, help="Tickers to analyze")
    parser.add_argument("--aristocrats", action="store_true", help="Filter for 25+ year aristocrats")
    parser.add_argument("--format", choices=["text", "json"], default="text", help="Output format")
    args = parser.parse_args()

    results = []
    for sym in args.tickers:
        try:
            data = analyze_ticker(sym.strip())
            results.append(data)
        except Exception as exc:
            results.append({"symbol": sym.upper(), "error": str(exc)})

    if args.aristocrats:
        results = [r for r in results if r.get("is_aristocrat")]

    if args.format == "json":
        print(json.dumps(results, indent=2))
    else:
        print(format_text(results))


if __name__ == "__main__":
    main()
