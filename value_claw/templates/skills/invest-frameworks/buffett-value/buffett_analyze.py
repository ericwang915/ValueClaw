#!/usr/bin/env python3
"""Warren Buffett value investing framework -- moat, owner earnings, margin of safety."""

from __future__ import annotations

import argparse
import json


def fetch_buffett_data(ticker: str) -> dict:
    """Fetch fundamentals and compute Buffett metrics via yfinance."""
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
    market_cap = info.get("marketCap", 0)
    net_income = info.get("netIncomeToCommon")
    depreciation = capex = None

    try:
        cf = stock.cashflow
        if cf is not None and not cf.empty:
            if "Depreciation And Amortization" in cf.index:
                depreciation = int(cf.loc["Depreciation And Amortization"].iloc[0])
            if "Capital Expenditure" in cf.index:
                capex = int(cf.loc["Capital Expenditure"].iloc[0])
    except Exception:
        pass

    owner_earnings = None
    if net_income is not None and depreciation is not None and capex is not None:
        owner_earnings = net_income + depreciation - abs(capex)

    roe = info.get("returnOnEquity")
    roe_pct = round(roe * 100, 1) if roe is not None else None
    total_debt = info.get("totalDebt", 0)
    bv, shares = info.get("bookValue", 0), info.get("sharesOutstanding", 0)
    equity = bv * shares if bv else None
    de_ratio = round(total_debt / equity, 2) if equity and equity > 0 else None
    fcf = info.get("freeCashflow")
    fcf_yield = round((fcf / market_cap) * 100, 2) if fcf and market_cap else None
    trailing_pe = info.get("trailingPE")
    eg = info.get("earningsGrowth")
    rev_growth = info.get("revenueGrowth")

    rev_consistent = None
    try:
        fin = stock.financials
        if fin is not None and "Total Revenue" in fin.index:
            revs = fin.loc["Total Revenue"].dropna().tolist()
            if len(revs) >= 3:
                ups = sum(1 for i in range(len(revs) - 1) if revs[i] >= revs[i + 1])
                rev_consistent = round(ups / (len(revs) - 1) * 100, 0)
    except Exception:
        pass

    score, breakdown = _compute_score(roe_pct, de_ratio, rev_consistent, trailing_pe, eg)

    return {
        "ticker": ticker.upper(), "name": info.get("shortName", ticker),
        "price": round(price, 2) if price else None,
        "marketCapB": round(market_cap / 1e9, 2) if market_cap else None,
        "ownerEarnings": owner_earnings, "roePct": roe_pct, "debtToEquity": de_ratio,
        "fcfYieldPct": fcf_yield, "revenueConsistencyPct": rev_consistent,
        "grossMarginPct": round(info["grossMargins"] * 100, 1) if info.get("grossMargins") else None,
        "opMarginPct": round(info["operatingMargins"] * 100, 1) if info.get("operatingMargins") else None,
        "trailingPE": round(trailing_pe, 2) if trailing_pe else None,
        "forwardPE": round(info["forwardPE"], 2) if info.get("forwardPE") else None,
        "earningsGrowth": round(eg * 100, 1) if eg else None,
        "revGrowth": round(rev_growth * 100, 1) if rev_growth else None,
        "score": score, "scoreBreakdown": breakdown,
        "note": "Durable Moat and Management Quality are LLM-evaluated (set to 0).",
    }


def _compute_score(roe_pct, de_ratio, rev_consistent, trailing_pe, earnings_growth):
    """Compute Buffett score (0-100) from data-driven factors."""
    bd = {}
    bd["consistentEarnings"] = (
        15 if rev_consistent and rev_consistent >= 75
        else 8 if rev_consistent and rev_consistent >= 50 else 0
    )
    bd["lowDebt"] = (
        15 if de_ratio is not None and de_ratio < 0.5
        else 10 if de_ratio is not None and de_ratio < 1.0
        else 5 if de_ratio is not None and de_ratio < 2.0 else 0
    )
    bd["highROE"] = (
        15 if roe_pct and roe_pct >= 20
        else 10 if roe_pct and roe_pct >= 15
        else 5 if roe_pct and roe_pct >= 10 else 0
    )
    if trailing_pe and earnings_growth:
        eg = earnings_growth * 100 if abs(earnings_growth) < 1 else earnings_growth
        peg = trailing_pe / eg if eg > 0 else 99
        bd["reasonableValuation"] = (
            20 if peg < 1.0 else 15 if peg < 1.5 else 8 if peg < 2.5 else 0
        )
    else:
        bd["reasonableValuation"] = 0
    bd["durableMoat"] = 0
    bd["managementQuality"] = 0
    return sum(bd.values()), bd


def _fmt(n):
    if n is None:
        return "N/A"
    if abs(n) >= 1e9:
        return "$%.2fB" % (n / 1e9)
    if abs(n) >= 1e6:
        return "$%.1fM" % (n / 1e6)
    return "${:,}".format(int(n))


def format_text(results: list[dict]) -> str:
    """Render results as a human-readable report."""
    lines = []
    for r in results:
        if "error" in r:
            lines.append("%s: ERROR - %s\n" % (r["ticker"], r["error"]))
            continue
        lines.append("=" * 60)
        lines.append("  %s -- %s  |  Buffett Score: %s/100 (data-only)" % (
            r["ticker"], r.get("name", ""), r["score"]))
        lines.append("=" * 60)
        for label, key in [
            ("Price", "price"), ("Market Cap", "marketCapB"), ("ROE", "roePct"),
            ("Debt/Equity", "debtToEquity"), ("FCF Yield", "fcfYieldPct"),
            ("Gross Margin", "grossMarginPct"), ("Op Margin", "opMarginPct"),
            ("Rev Consistency", "revenueConsistencyPct"), ("Trailing P/E", "trailingPE"),
        ]:
            val = r.get(key)
            lines.append("  %-18s %s" % (label, val if val is not None else "N/A"))
        lines.append("  Owner Earnings     %s" % _fmt(r.get("ownerEarnings")))
        lines.append("\n--- Score Breakdown ---")
        for k, v in r.get("scoreBreakdown", {}).items():
            lines.append("  %-25s %d" % (k, v))
        lines.append("  %-25s %d/100\n" % ("TOTAL (data-only)", r["score"]))
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Warren Buffett value investing analysis")
    parser.add_argument("--tickers", nargs="+", required=True, help="Tickers to analyze")
    parser.add_argument("--format", choices=["text", "json"], default="text")
    args = parser.parse_args()
    results = [fetch_buffett_data(t.upper()) for t in args.tickers]
    if args.format == "json":
        print(json.dumps(results, indent=2, default=str))
    else:
        print(format_text(results))


if __name__ == "__main__":
    main()
