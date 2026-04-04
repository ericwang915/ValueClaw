#!/usr/bin/env python3
"""Peter Lynch GARP framework -- PEG screening, stock classification, ten-bagger potential."""

from __future__ import annotations

import argparse
import json

CATEGORIES = {
    "slow_grower": "Slow Grower (<5% growth, large cap, often dividends)",
    "stalwart": "Stalwart (5-15% growth, large cap, steady performer)",
    "fast_grower": "Fast Grower (>15% growth, small/mid cap -- ten-bagger source)",
    "cyclical": "Cyclical (earnings tied to economic cycles)",
    "turnaround": "Turnaround (depressed company with recovery potential)",
    "asset_play": "Asset Play (hidden value not reflected in price)",
}


def fetch_lynch_data(ticker: str) -> dict:
    """Fetch data and classify stock using Lynch framework."""
    try:
        import yfinance as yf
    except ImportError:
        return {"ticker": ticker, "error": "yfinance not installed"}
    try:
        stock = yf.Ticker(ticker)
        info = stock.info or {}
    except Exception as exc:
        return {"ticker": ticker, "error": str(exc)}

    price = info.get("currentPrice") or info.get("regularMarketPrice") or info.get("previousClose")
    mcap = info.get("marketCap", 0)
    cap_b = mcap / 1e9 if mcap else 0
    trailing_pe = info.get("trailingPE")
    forward_pe = info.get("forwardPE")
    eg = info.get("earningsGrowth")
    rg = info.get("revenueGrowth")
    eg_pct = (eg * 100 if eg is not None and abs(eg) < 5 else eg) if eg is not None else None
    peg = round(trailing_pe / eg_pct, 2) if trailing_pe and eg_pct and eg_pct > 0 else None
    bv, sh = info.get("bookValue", 0), info.get("sharesOutstanding", 0)
    equity = bv * sh if bv else None
    debt_ratio = round(info.get("totalDebt", 0) / equity, 2) if equity and equity > 0 else None
    inst = info.get("heldPercentInstitutions")
    inst_pct = round(inst * 100, 1) if inst else None
    div_y = info.get("dividendYield")
    div_pct = round(div_y * 100, 2) if div_y else None

    cat = _classify(eg_pct, cap_b, trailing_pe, div_pct, debt_ratio)
    tb = _ten_bagger(cat, cap_b, eg_pct, peg, inst_pct)

    return {
        "ticker": ticker.upper(), "name": info.get("shortName", ticker),
        "price": round(price, 2) if price else None, "marketCapB": round(cap_b, 2),
        "category": cat, "categoryDescription": CATEGORIES.get(cat, ""),
        "trailingPE": round(trailing_pe, 2) if trailing_pe else None,
        "forwardPE": round(forward_pe, 2) if forward_pe else None,
        "earningsGrowthPct": round(eg_pct, 1) if eg_pct else None,
        "revenueGrowthPct": round(rg * 100, 1) if rg else None,
        "peg": peg, "debtRatio": debt_ratio,
        "institutionalPct": inst_pct, "dividendYieldPct": div_pct, "tenBagger": tb,
    }


def _classify(eg_pct, cap_b, pe, div_pct, debt_ratio) -> str:
    if pe is not None and pe < 0:
        return "turnaround"
    g = eg_pct or 0
    if cap_b > 50 and g < 5:
        return "slow_grower"
    if g > 15 and cap_b < 20:
        return "fast_grower"
    if cap_b > 10 and 5 <= g <= 15:
        return "stalwart"
    if g > 15 and cap_b >= 20:
        return "stalwart"
    if g < 5 and cap_b <= 10:
        return "asset_play"
    return "stalwart"


def _ten_bagger(cat, cap_b, eg_pct, peg, inst_pct) -> dict:
    g = eg_pct or 0
    crit = {
        "smallOrMidCap": cap_b < 20, "highGrowth": g > 15,
        "lowPEG": peg is not None and peg < 1.5,
        "underFollowed": inst_pct is not None and inst_pct < 60,
        "fastGrowerCategory": cat == "fast_grower",
    }
    met = sum(1 for v in crit.values() if v)
    signal = ("STRONG TEN-BAGGER CANDIDATE" if met >= 4
              else "MODERATE TEN-BAGGER POTENTIAL" if met >= 3
              else "LOW TEN-BAGGER POTENTIAL")
    return {"signal": signal, "criteriaMet": met, "criteriaTotal": len(crit), "details": crit}


def format_text(results: list[dict]) -> str:
    lines = []
    for r in results:
        if "error" in r:
            lines.append("%s: ERROR - %s\n" % (r["ticker"], r["error"]))
            continue
        lines.append("=" * 60)
        lines.append("  %s -- %s" % (r["ticker"], r.get("name", "")))
        lines.append("  Category: %s" % r["categoryDescription"])
        lines.append("=" * 60)
        for label, key in [
            ("Price", "price"), ("Market Cap", "marketCapB"), ("Trailing P/E", "trailingPE"),
            ("Forward P/E", "forwardPE"), ("Earnings Growth", "earningsGrowthPct"),
            ("Revenue Growth", "revenueGrowthPct"), ("PEG Ratio", "peg"),
            ("Debt Ratio", "debtRatio"), ("Institutional %", "institutionalPct"),
            ("Dividend Yield", "dividendYieldPct"),
        ]:
            v = r.get(key)
            lines.append("  %-18s %s" % (label, v if v is not None else "N/A"))
        tb = r.get("tenBagger", {})
        lines.append("\n--- Ten-Bagger Screen: %s ---" % tb.get("signal", "N/A"))
        lines.append("  Criteria met: %d/%d" % (tb.get("criteriaMet", 0), tb.get("criteriaTotal", 0)))
        for k, v in tb.get("details", {}).items():
            lines.append("    %s %s" % ("[x]" if v else "[ ]", k))
        lines.append("")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Peter Lynch GARP -- PEG, classification, ten-bagger")
    parser.add_argument("--tickers", nargs="+", required=True, help="Tickers to analyze")
    parser.add_argument("--format", choices=["text", "json"], default="text")
    args = parser.parse_args()
    results = [fetch_lynch_data(t.upper()) for t in args.tickers]
    if args.format == "json":
        print(json.dumps(results, indent=2, default=str))
    else:
        print(format_text(results))


if __name__ == "__main__":
    main()
