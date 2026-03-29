#!/usr/bin/env python3
"""Central bank rate watch — compare policy rates across major central banks."""

from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timedelta

import requests

DATA_DIR = os.path.expanduser("~/.value_claw/central_bank_watch")
FRED_CSV_URL = "https://fred.stlouisfed.org/graph/fredgraph.csv"

BANKS = {
    "fed": {"series": "FEDFUNDS", "name": "US Federal Reserve", "currency": "USD"},
    "ecb": {"series": "ECBDFR", "name": "European Central Bank", "currency": "EUR"},
    "boj": {"series": "IRSTCB01JPM156N", "name": "Bank of Japan", "currency": "JPY"},
    "boe": {"series": "BOERUKM", "name": "Bank of England", "currency": "GBP"},
    "pboc": {"series": None, "name": "People's Bank of China", "currency": "CNY"},
}

PBOC_LPR_FALLBACK = {"rate": 3.10, "date": "2024-10-21", "note": "1Y LPR (hardcoded fallback)"}


def _ensure_dir() -> None:
    os.makedirs(DATA_DIR, exist_ok=True)


def fetch_rate_history(series_id: str, months: int = 18) -> list[dict]:
    """Fetch monthly rate data from FRED."""
    start = (datetime.now() - timedelta(days=months * 31)).strftime("%Y-%m-%d")
    params = {"id": series_id, "cosd": start}
    resp = requests.get(FRED_CSV_URL, params=params, timeout=20)
    resp.raise_for_status()

    rows: list[dict] = []
    for line in resp.text.strip().splitlines()[1:]:
        parts = line.split(",")
        if len(parts) < 2 or parts[1].strip() == ".":
            continue
        try:
            rows.append({"date": parts[0].strip(), "rate": float(parts[1].strip())})
        except ValueError:
            continue
    return rows


def last_change_direction(history: list[dict]) -> dict:
    """Find the most recent rate change and its direction."""
    if len(history) < 2:
        return {"direction": "unknown", "date": None, "from": None, "to": None}
    for i in range(len(history) - 1, 0, -1):
        if history[i]["rate"] != history[i - 1]["rate"]:
            diff = history[i]["rate"] - history[i - 1]["rate"]
            direction = "hike" if diff > 0 else "cut"
            return {
                "direction": direction,
                "date": history[i]["date"],
                "from": history[i - 1]["rate"],
                "to": history[i]["rate"],
            }
    return {"direction": "unchanged", "date": None, "from": None, "to": None}


def build_bank_data(bank_key: str) -> dict:
    """Build rate data for a single central bank."""
    bank = BANKS[bank_key]
    result = {"bank": bank_key, "name": bank["name"], "currency": bank["currency"]}

    if bank["series"] is None:
        result.update({
            "current_rate": PBOC_LPR_FALLBACK["rate"],
            "latest_date": PBOC_LPR_FALLBACK["date"],
            "last_change": {"direction": "cut", "date": "2024-10-21", "from": 3.35, "to": 3.10},
            "history_12m": [],
            "note": PBOC_LPR_FALLBACK["note"],
        })
        return result

    history = fetch_rate_history(bank["series"])
    if not history:
        result.update({"current_rate": None, "latest_date": None,
                        "last_change": {}, "history_12m": []})
        return result

    result["current_rate"] = history[-1]["rate"]
    result["latest_date"] = history[-1]["date"]
    result["last_change"] = last_change_direction(history)
    result["history_12m"] = history[-12:]
    return result


def format_text(data: list[dict]) -> str:
    """Render central bank comparison as text."""
    lines = [
        "=" * 72,
        "  CENTRAL BANK RATE WATCH",
        "  Generated: %s" % datetime.now().strftime("%Y-%m-%d %H:%M"),
        "=" * 72,
        "",
    ]

    for bank in data:
        rate_str = ("%.2f%%" % bank["current_rate"]) if bank["current_rate"] is not None else "N/A"
        lines.append("%-30s  Rate: %8s  (%s)" % (bank["name"], rate_str, bank["currency"]))

        lc = bank.get("last_change", {})
        if lc.get("direction") and lc["direction"] not in ("unknown", "unchanged"):
            lines.append(
                "  Last change: %s on %s (%.2f -> %.2f)"
                % (lc["direction"].upper(), lc.get("date", "?"),
                   lc.get("from", 0), lc.get("to", 0))
            )
        elif lc.get("direction") == "unchanged":
            lines.append("  No rate change in observed period")

        if bank.get("note"):
            lines.append("  Note: %s" % bank["note"])
        lines.append("")

    lines.append("-" * 72)
    rates = [(b["name"], b["current_rate"]) for b in data if b["current_rate"] is not None]
    if rates:
        highest = max(rates, key=lambda x: x[1])
        lowest = min(rates, key=lambda x: x[1])
        lines.append("  Highest rate: %s (%.2f%%)" % (highest[0], highest[1]))
        lines.append("  Lowest rate:  %s (%.2f%%)" % (lowest[0], lowest[1]))
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Central Bank Rate Watch")
    parser.add_argument("--bank", default="all",
                        choices=["fed", "ecb", "boj", "boe", "pboc", "all"])
    parser.add_argument("--format", choices=["text", "json"], default="text")
    args = parser.parse_args()

    _ensure_dir()
    keys = list(BANKS.keys()) if args.bank == "all" else [args.bank]

    print("Fetching central bank rates...")
    data = []
    for key in keys:
        info = BANKS[key]
        if info["series"]:
            print("  %s (%s)..." % (info["name"], info["series"]))
        else:
            print("  %s (hardcoded fallback)..." % info["name"])
        data.append(build_bank_data(key))

    if args.format == "json":
        print(json.dumps(data, indent=2))
    else:
        print(format_text(data))

    cache_path = os.path.join(DATA_DIR, "last_rates.json")
    with open(cache_path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2)
    print("Cached to: %s" % cache_path)


if __name__ == "__main__":
    main()
