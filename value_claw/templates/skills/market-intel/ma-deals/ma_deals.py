#!/usr/bin/env python3
"""M&A deal tracker and merger arbitrage analysis."""

from __future__ import annotations

import argparse
import datetime
import json

try:
    import yfinance as yf
except ImportError:
    yf = None

PENDING_DEALS = [
    {"acquirer": "Capital One", "target": "Discover Financial", "target_ticker": "DFS",
     "offer_price": 140.30, "deal_type": "stock", "expected_close": "2025-05-01",
     "sector": "Financials"},
    {"acquirer": "Synopsys", "target": "Ansys", "target_ticker": "ANSS",
     "offer_price": 390.00, "deal_type": "cash+stock", "expected_close": "2025-06-30",
     "sector": "Technology"},
    {"acquirer": "Diamondback Energy", "target": "Endeavor Energy", "target_ticker": "FANG",
     "offer_price": 0.0, "deal_type": "stock", "expected_close": "2025-03-01",
     "sector": "Energy"},
    {"acquirer": "Johnson & Johnson", "target": "Intra-Cellular", "target_ticker": "ITCI",
     "offer_price": 132.00, "deal_type": "cash", "expected_close": "2025-06-30",
     "sector": "Healthcare"},
    {"acquirer": "Hewlett Packard Enterprise", "target": "Juniper Networks", "target_ticker": "JNPR",
     "offer_price": 40.00, "deal_type": "cash", "expected_close": "2025-06-30",
     "sector": "Technology"},
    {"acquirer": "Mars Inc", "target": "Kellanova", "target_ticker": "K",
     "offer_price": 83.50, "deal_type": "cash", "expected_close": "2025-06-30",
     "sector": "Consumer Staples"},
    {"acquirer": "Eli Lilly", "target": "Morphic Holding", "target_ticker": "MORF",
     "offer_price": 57.00, "deal_type": "cash", "expected_close": "2025-03-01",
     "sector": "Healthcare"},
    {"acquirer": "Alphabet", "target": "Wiz", "target_ticker": "GOOGL",
     "offer_price": 0.0, "deal_type": "cash", "expected_close": "2025-09-01",
     "sector": "Technology"},
]

RECENT_DEALS = [
    {"acquirer": "Broadcom", "target": "VMware", "completed": "2023-11-22",
     "value_bn": 69.0, "deal_type": "cash+stock", "sector": "Technology"},
    {"acquirer": "Exxon Mobil", "target": "Pioneer Natural", "completed": "2024-05-03",
     "value_bn": 59.5, "deal_type": "stock", "sector": "Energy"},
    {"acquirer": "Cisco", "target": "Splunk", "completed": "2024-03-18",
     "value_bn": 28.0, "deal_type": "cash", "sector": "Technology"},
    {"acquirer": "AbbVie", "target": "ImmunoGen", "completed": "2024-02-12",
     "value_bn": 10.1, "deal_type": "cash", "sector": "Healthcare"},
]


def get_current_price(ticker: str) -> float | None:
    """Fetch current price via yfinance."""
    if yf is None:
        return None
    try:
        t = yf.Ticker(ticker)
        info = t.info
        return info.get("currentPrice") or info.get("regularMarketPrice")
    except Exception:
        return None


def compute_spread(offer: float, current: float, close_date: str) -> dict:
    """Compute spread and annualized return."""
    if offer <= 0 or current is None or current <= 0:
        return {"spread_pct": None, "annualized_pct": None}
    spread = (offer - current) / current * 100
    try:
        exp = datetime.date.fromisoformat(close_date)
        days = (exp - datetime.date.today()).days
        if days <= 0:
            days = 1
        annualized = spread * (365 / days)
    except (ValueError, ZeroDivisionError):
        annualized = None
    return {"spread_pct": round(spread, 2), "annualized_pct": round(annualized, 2) if annualized else None}


def show_pending(output_format: str) -> None:
    """Show pending deals with live arbitrage spreads."""
    results = []
    for deal in PENDING_DEALS:
        current = get_current_price(deal["target_ticker"])
        spread_info = compute_spread(deal["offer_price"], current, deal["expected_close"])
        entry = {
            **deal,
            "current_price": round(current, 2) if current else None,
            **spread_info,
        }
        results.append(entry)

    if output_format == "json":
        print(json.dumps({"pending_deals": results}, indent=2))
        return

    print("=" * 85)
    print("  PENDING M&A DEALS — Merger Arbitrage")
    print("=" * 85)
    print("")
    hdr = "{:<22} {:<18} {:<6} {:>8} {:>8} {:>8} {:>8} {:<10}".format(
        "Acquirer", "Target", "Type", "Offer", "Current", "Spread%", "Annual%", "Exp Close")
    print(hdr)
    print("-" * 95)
    for d in results:
        offer = "{:.2f}".format(d["offer_price"]) if d["offer_price"] > 0 else "N/A"
        curr = "{:.2f}".format(d["current_price"]) if d["current_price"] else "N/A"
        spread = "{:.2f}".format(d["spread_pct"]) if d["spread_pct"] is not None else "N/A"
        annual = "{:.1f}".format(d["annualized_pct"]) if d["annualized_pct"] is not None else "N/A"
        print("{:<22} {:<18} {:<6} {:>8} {:>8} {:>8} {:>8} {:<10}".format(
            d["acquirer"][:21], d["target"][:17], d["deal_type"],
            offer, curr, spread, annual, d["expected_close"]))
    print("")


def show_recent(output_format: str) -> None:
    """Show recently completed M&A deals."""
    if output_format == "json":
        print(json.dumps({"recent_deals": RECENT_DEALS}, indent=2))
        return

    print("=" * 75)
    print("  RECENTLY COMPLETED M&A DEALS")
    print("=" * 75)
    print("")
    hdr = "{:<20} {:<20} {:<12} {:>10} {:<10}".format(
        "Acquirer", "Target", "Completed", "Value ($B)", "Type")
    print(hdr)
    print("-" * 75)
    for d in RECENT_DEALS:
        print("{:<20} {:<20} {:<12} {:>10.1f} {:<10}".format(
            d["acquirer"][:19], d["target"][:19], d["completed"],
            d["value_bn"], d["deal_type"]))
    print("")


def main() -> None:
    parser = argparse.ArgumentParser(description="M&A deal tracker and merger arbitrage")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--pending", action="store_true", help="Show pending deals")
    group.add_argument("--recent", action="store_true", help="Show recent deals")
    parser.add_argument("--format", choices=["text", "json"], default="text", help="Output format")
    args = parser.parse_args()

    if args.pending:
        show_pending(args.format)
    else:
        show_recent(args.format)


if __name__ == "__main__":
    main()
