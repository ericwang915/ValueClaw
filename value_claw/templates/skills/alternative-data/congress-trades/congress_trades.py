#!/usr/bin/env python3
"""Fetch and filter US congressional stock trades from STOCK Act disclosures."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timedelta, timezone

import requests

API_URL = (
    "https://house-stock-watcher-data.s3-us-west-2.amazonaws.com"
    "/data/all_transactions.json"
)


def fetch_transactions() -> list[dict]:
    """Download all House stock transactions."""
    resp = requests.get(API_URL, timeout=30)
    resp.raise_for_status()
    return resp.json()


def parse_date(raw: str) -> datetime | None:
    """Parse transaction date string into a datetime."""
    for fmt in ("%Y-%m-%d", "%m/%d/%Y"):
        try:
            return datetime.strptime(raw, fmt).replace(tzinfo=timezone.utc)
        except (ValueError, TypeError):
            continue
    return None


def filter_transactions(
    txns: list[dict],
    ticker: str | None = None,
    member: str | None = None,
    days: int | None = None,
) -> list[dict]:
    """Apply filters to the transaction list."""
    cutoff = None
    if days is not None:
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)

    results = []
    for txn in txns:
        if ticker:
            txn_ticker = (txn.get("ticker") or "").upper()
            if txn_ticker != ticker.upper():
                continue

        if member:
            txn_member = (txn.get("representative") or "").lower()
            if member.lower() not in txn_member:
                continue

        if cutoff:
            txn_date = parse_date(txn.get("transaction_date", ""))
            if txn_date is None or txn_date < cutoff:
                continue

        results.append(txn)

    return results


def normalize(txn: dict) -> dict:
    """Normalize a transaction into a clean record."""
    return {
        "member": txn.get("representative", "Unknown"),
        "ticker": (txn.get("ticker") or "N/A").upper(),
        "asset": txn.get("asset_description", ""),
        "type": txn.get("type", "Unknown"),
        "amount": txn.get("amount", "Unknown"),
        "date": txn.get("transaction_date", "Unknown"),
        "district": txn.get("district", ""),
        "disclosure_date": txn.get("disclosure_date", ""),
    }


def format_text(records: list[dict]) -> str:
    """Render records as a human-readable table."""
    if not records:
        return "No trades found matching the criteria."

    lines = []
    header = (
        "Date        | Member                    | Ticker | Type       "
        "| Amount              "
    )
    sep = "-" * len(header)
    lines.append(header)
    lines.append(sep)

    for r in records:
        date_str = r["date"][:10] if len(r["date"]) >= 10 else r["date"]
        member_str = r["member"][:25].ljust(25)
        ticker_str = r["ticker"][:6].ljust(6)
        type_str = r["type"][:10].ljust(10)
        amount_str = r["amount"][:20]
        lines.append(
            "%s | %s | %s | %s | %s"
            % (date_str, member_str, ticker_str, type_str, amount_str)
        )

    lines.append(sep)
    lines.append("Total: %d trade(s)" % len(records))
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Track US congressional stock trades (STOCK Act disclosures)"
    )
    parser.add_argument("--ticker", default=None, help="Filter by stock ticker")
    parser.add_argument(
        "--member", default=None, help="Filter by member name (partial match)"
    )
    parser.add_argument(
        "--days", type=int, default=None, help="Only trades within last N days"
    )
    parser.add_argument(
        "--limit", type=int, default=50, help="Max trades to display (default: 50)"
    )
    parser.add_argument(
        "--format",
        choices=["text", "json"],
        default="text",
        help="Output format (default: text)",
    )
    args = parser.parse_args()

    try:
        txns = fetch_transactions()
    except Exception as exc:
        print("Error fetching data: %s" % exc, file=sys.stderr)
        sys.exit(1)

    filtered = filter_transactions(
        txns, ticker=args.ticker, member=args.member, days=args.days
    )

    filtered.sort(
        key=lambda t: t.get("transaction_date", ""), reverse=True
    )
    filtered = filtered[: args.limit]
    records = [normalize(t) for t in filtered]

    if args.format == "json":
        print(json.dumps(records, indent=2))
    else:
        print(format_text(records))


if __name__ == "__main__":
    main()
