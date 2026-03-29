#!/usr/bin/env python3
"""Macro dashboard — fetch key US economic indicators from FRED public CSV."""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timedelta

import requests

DATA_DIR = os.path.expanduser("~/.value_claw/macro_dashboard")

FRED_CSV_URL = "https://fred.stlouisfed.org/graph/fredgraph.csv"

SERIES = {
    "GDP": "Nominal GDP ($B)",
    "GDPC1": "Real GDP ($B)",
    "CPIAUCSL": "CPI (All Urban)",
    "UNRATE": "Unemployment Rate (%)",
    "MANEMP": "Manufacturing Employment (K)",
    "FEDFUNDS": "Federal Funds Rate (%)",
    "T10Y2Y": "10Y-2Y Spread (%)",
}


def _ensure_dir() -> None:
    os.makedirs(DATA_DIR, exist_ok=True)


def fetch_series(series_id: str, years: int = 5) -> list[dict]:
    """Fetch a single FRED series as CSV, return list of {date, value}."""
    start = (datetime.now() - timedelta(days=years * 365)).strftime("%Y-%m-%d")
    params = {"id": series_id, "cosd": start}
    resp = requests.get(FRED_CSV_URL, params=params, timeout=20)
    resp.raise_for_status()

    rows: list[dict] = []
    lines = resp.text.strip().splitlines()
    for line in lines[1:]:
        parts = line.split(",")
        if len(parts) < 2 or parts[1].strip() == ".":
            continue
        try:
            rows.append({"date": parts[0].strip(), "value": float(parts[1].strip())})
        except ValueError:
            continue
    return rows


def detect_trend(values: list[float], window: int = 3) -> str:
    """Detect rising/falling/stable from the last `window` observations."""
    if len(values) < window:
        return "insufficient data"
    recent = values[-window:]
    diffs = [recent[i] - recent[i - 1] for i in range(1, len(recent))]
    avg_diff = sum(diffs) / len(diffs)
    if avg_diff > 0.01:
        return "rising"
    if avg_diff < -0.01:
        return "falling"
    return "stable"


def yoy_change(rows: list[dict]) -> float | None:
    """Compute year-over-year percentage change from last two comparable points."""
    if len(rows) < 12:
        return None
    current = rows[-1]["value"]
    year_ago = rows[-12]["value"] if len(rows) >= 12 else rows[0]["value"]
    if year_ago == 0:
        return None
    return round(((current / year_ago) - 1) * 100, 2)


def build_dashboard() -> list[dict]:
    """Fetch all series and build dashboard rows."""
    dashboard: list[dict] = []
    for series_id, label in SERIES.items():
        rows = fetch_series(series_id)
        if not rows:
            dashboard.append({
                "series": series_id,
                "label": label,
                "latest_value": None,
                "latest_date": None,
                "trend": "no data",
                "yoy_change_pct": None,
            })
            continue

        values = [r["value"] for r in rows]
        dashboard.append({
            "series": series_id,
            "label": label,
            "latest_value": rows[-1]["value"],
            "latest_date": rows[-1]["date"],
            "trend": detect_trend(values),
            "yoy_change_pct": yoy_change(rows),
        })
    return dashboard


def format_text(dashboard: list[dict]) -> str:
    """Render dashboard as a human-readable table."""
    lines = [
        "=" * 78,
        "  US MACRO DASHBOARD",
        "  Generated: %s" % datetime.now().strftime("%Y-%m-%d %H:%M"),
        "=" * 78,
        "",
        "%-14s %-30s %12s %10s %8s" % ("Series", "Indicator", "Latest", "Trend", "YoY %"),
        "-" * 78,
    ]
    for row in dashboard:
        val = row["latest_value"]
        val_str = ("%.2f" % val) if val is not None else "N/A"
        yoy = row["yoy_change_pct"]
        yoy_str = ("%+.2f%%" % yoy) if yoy is not None else "N/A"
        lines.append(
            "%-14s %-30s %12s %10s %8s"
            % (row["series"], row["label"], val_str, row["trend"], yoy_str)
        )
    lines.append("-" * 78)

    spread = next((r for r in dashboard if r["series"] == "T10Y2Y"), None)
    if spread and spread["latest_value"] is not None:
        if spread["latest_value"] < 0:
            lines.append("  ** YIELD CURVE INVERTED — historically a recession signal **")
        else:
            lines.append("  Yield curve is positive (%.2f%%)." % spread["latest_value"])

    lines.append("")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="US Macro Dashboard via FRED")
    parser.add_argument("--country", default="us", help="Country (default: us)")
    parser.add_argument("--format", choices=["text", "json"], default="text")
    args = parser.parse_args()

    if args.country.lower() != "us":
        print("Only --country us is currently supported.", file=sys.stderr)
        sys.exit(1)

    _ensure_dir()
    print("Fetching macro indicators from FRED...")
    dashboard = build_dashboard()

    if args.format == "json":
        print(json.dumps(dashboard, indent=2))
    else:
        print(format_text(dashboard))

    cache_path = os.path.join(DATA_DIR, "last_dashboard.json")
    with open(cache_path, "w", encoding="utf-8") as fh:
        json.dump(dashboard, fh, indent=2)
    print("Cached to: %s" % cache_path)


if __name__ == "__main__":
    main()
