#!/usr/bin/env python3
"""Track upcoming and recent IPOs with post-listing performance."""

from __future__ import annotations

import argparse
import datetime
import json

import requests

try:
    import yfinance as yf
except ImportError:
    yf = None


EDGAR_S1_URL = (
    "https://efts.sec.gov/LATEST/search-index?"
    "q=%22S-1%22&dateRange=custom&startdt={start}&enddt={end}"
    "&forms=S-1&hits.hits.total.value=20"
)

RECENT_IPOS = [
    {"company": "Reddit Inc", "ticker": "RDDT", "date": "2024-03-21", "price_range": "$31-34", "exchange": "NYSE", "sector": "Technology"},
    {"company": "Astera Labs", "ticker": "ALAB", "date": "2024-03-20", "price_range": "$32-36", "exchange": "NASDAQ", "sector": "Semiconductors"},
    {"company": "Rubrik Inc", "ticker": "RBRK", "date": "2024-04-25", "price_range": "$28-31", "exchange": "NYSE", "sector": "Cybersecurity"},
    {"company": "Viking Holdings", "ticker": "VIK", "date": "2024-05-01", "price_range": "$24-27", "exchange": "NYSE", "sector": "Travel"},
    {"company": "Lineage Inc", "ticker": "LINE", "date": "2024-07-25", "price_range": "$70-82", "exchange": "NASDAQ", "sector": "REIT"},
    {"company": "Cerebras Systems", "ticker": "CBRS", "date": "2025-03-15", "price_range": "$TBD", "exchange": "NASDAQ", "sector": "AI/Semiconductors"},
    {"company": "Klarna", "ticker": "KLAR", "date": "2025-04-01", "price_range": "$TBD", "exchange": "NYSE", "sector": "Fintech"},
    {"company": "Databricks", "ticker": "DBX2", "date": "2025-06-01", "price_range": "$TBD", "exchange": "NASDAQ", "sector": "AI/Data"},
    {"company": "Stripe Inc", "ticker": "STRP", "date": "2025-09-01", "price_range": "$TBD", "exchange": "NYSE", "sector": "Fintech"},
    {"company": "Shein Group", "ticker": "SHEIN", "date": "2025-06-01", "price_range": "$TBD", "exchange": "NYSE", "sector": "E-commerce"},
]


def fetch_edgar_filings() -> list[dict]:
    """Fetch recent S-1 filings from SEC EDGAR full-text search."""
    end = datetime.date.today()
    start = end - datetime.timedelta(days=90)
    url = (
        "https://efts.sec.gov/LATEST/search-index?"
        "q=%22S-1%22&forms=S-1"
        "&dateRange=custom"
        "&startdt=" + start.isoformat()
        + "&enddt=" + end.isoformat()
    )
    headers = {"User-Agent": "ValueClaw/1.0 research@example.com"}
    results = []
    try:
        resp = requests.get(url, headers=headers, timeout=15)
        if resp.status_code == 200:
            data = resp.json()
            for hit in data.get("hits", {}).get("hits", [])[:20]:
                src = hit.get("_source", {})
                name = src.get("entity_name", "Unknown")
                filed = src.get("file_date", "")
                results.append({"company": name, "filed": filed, "form": "S-1"})
    except Exception:
        pass
    return results


def get_ipo_performance(ticker: str) -> dict | None:
    """Fetch post-IPO price performance via yfinance."""
    if yf is None:
        return None
    try:
        t = yf.Ticker(ticker)
        info = t.info
        current = info.get("currentPrice") or info.get("regularMarketPrice")
        if current is None:
            return None
        hist = t.history(period="max")
        if hist.empty:
            return None
        ipo_close = float(hist["Close"].iloc[0])
        return {
            "current_price": round(current, 2),
            "ipo_first_close": round(ipo_close, 2),
            "return_pct": round((current - ipo_close) / ipo_close * 100, 2),
            "name": info.get("shortName", ticker),
        }
    except Exception:
        return None


def show_upcoming(output_format: str) -> None:
    """Display upcoming/expected IPOs."""
    today = datetime.date.today()
    upcoming = [
        ipo for ipo in RECENT_IPOS
        if datetime.date.fromisoformat(ipo["date"]) >= today
    ]
    edgar = fetch_edgar_filings()

    if output_format == "json":
        print(json.dumps({"upcoming_ipos": upcoming, "recent_s1_filings": edgar}, indent=2))
        return

    print("=" * 60)
    print("  UPCOMING / EXPECTED IPOS")
    print("=" * 60)
    if upcoming:
        print("\n{:<25} {:<8} {:<12} {:<10} {}".format(
            "Company", "Ticker", "Exp. Date", "Exchange", "Sector"))
        print("-" * 75)
        for ipo in upcoming:
            print("{:<25} {:<8} {:<12} {:<10} {}".format(
                ipo["company"][:24], ipo["ticker"], ipo["date"],
                ipo["exchange"], ipo["sector"]))
    else:
        print("\nNo upcoming IPOs in curated list.")

    if edgar:
        print("\n  Recent S-1 Filings (SEC EDGAR):")
        print("-" * 50)
        for f in edgar[:10]:
            print("  {} — filed {}".format(f["company"], f["filed"]))
    print()


def show_recent(days: int, output_format: str) -> None:
    """Display recent IPOs with post-IPO performance."""
    today = datetime.date.today()
    cutoff = today - datetime.timedelta(days=days)
    recent = [
        ipo for ipo in RECENT_IPOS
        if cutoff <= datetime.date.fromisoformat(ipo["date"]) <= today
    ]

    results = []
    for ipo in recent:
        perf = get_ipo_performance(ipo["ticker"])
        entry = {**ipo}
        if perf:
            entry.update(perf)
        results.append(entry)

    if not results:
        results = []
        for ipo in RECENT_IPOS:
            if datetime.date.fromisoformat(ipo["date"]) <= today:
                perf = get_ipo_performance(ipo["ticker"])
                entry = {**ipo}
                if perf:
                    entry.update(perf)
                results.append(entry)

    if output_format == "json":
        print(json.dumps({"recent_ipos": results, "lookback_days": days}, indent=2))
        return

    print("=" * 60)
    print("  RECENT IPO PERFORMANCE (last {} days)".format(days))
    print("=" * 60)
    print("\n{:<20} {:<7} {:<10} {:<10} {:<10} {}".format(
        "Company", "Ticker", "IPO Date", "IPO Close", "Current", "Return"))
    print("-" * 75)
    for r in results:
        ipo_close = r.get("ipo_first_close", "N/A")
        current = r.get("current_price", "N/A")
        ret = r.get("return_pct")
        ret_str = "{:+.1f}%".format(ret) if ret is not None else "N/A"
        print("{:<20} {:<7} {:<10} {:<10} {:<10} {}".format(
            r["company"][:19], r["ticker"], r["date"],
            ipo_close, current, ret_str))
    print()


def main() -> None:
    parser = argparse.ArgumentParser(description="Track upcoming and recent IPOs")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--upcoming", action="store_true", help="Show upcoming IPOs")
    group.add_argument("--recent", type=int, metavar="DAYS", help="Show recent IPOs from last N days")
    parser.add_argument("--format", choices=["text", "json"], default="text", help="Output format")
    args = parser.parse_args()

    if args.upcoming:
        show_upcoming(args.format)
    else:
        show_recent(args.recent, args.format)


if __name__ == "__main__":
    main()
