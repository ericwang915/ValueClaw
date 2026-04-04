#!/usr/bin/env python3
"""Fetch US Treasury yield curve from FRED and detect inversions."""

from __future__ import annotations

import argparse
import csv
import io
import json
import os
import sys
from datetime import datetime, timedelta

try:
    import requests
except ImportError:
    print("Error: requests not installed. Run: pip install requests", file=sys.stderr)
    sys.exit(1)


DATA_DIR = os.path.expanduser("~/.value_claw/yield-curve")
FRED_CSV = "https://fred.stlouisfed.org/graph/fredgraph.csv"

SERIES = {
    "1M": "DGS1MO", "3M": "DGS3MO", "6M": "DGS6MO",
    "1Y": "DGS1", "2Y": "DGS2", "3Y": "DGS3",
    "5Y": "DGS5", "7Y": "DGS7", "10Y": "DGS10",
    "20Y": "DGS20", "30Y": "DGS30",
}


def fetch_fred_series(series_id: str, days: int = 5) -> list[tuple[str, float]]:
    """Fetch a FRED series as (date, value) pairs."""
    start = (datetime.now() - timedelta(days=days + 10)).strftime("%Y-%m-%d")
    url = f"{FRED_CSV}?id={series_id}&cosd={start}"
    resp = requests.get(url, timeout=15)
    resp.raise_for_status()
    reader = csv.reader(io.StringIO(resp.text))
    next(reader, None)
    rows = []
    for row in reader:
        if len(row) >= 2 and row[1] not in (".", ""):
            try:
                rows.append((row[0], float(row[1])))
            except ValueError:
                continue
    return rows


def fetch_curve_snapshot() -> dict[str, float | None]:
    """Fetch the latest yield for each maturity."""
    curve: dict[str, float | None] = {}
    for label, sid in SERIES.items():
        try:
            rows = fetch_fred_series(sid, days=5)
            curve[label] = rows[-1][1] if rows else None
        except Exception:
            curve[label] = None
    return curve


def fetch_spread_history(days: int) -> list[dict]:
    """Fetch 2s10s and 3m10y spread history."""
    s2 = dict(fetch_fred_series("DGS2", days))
    s10 = dict(fetch_fred_series("DGS10", days))
    s3m = dict(fetch_fred_series("DGS3MO", days))
    all_dates = sorted(set(s2) & set(s10) & set(s3m))
    history = []
    for d in all_dates:
        spread_2s10s = round(s10[d] - s2[d], 3)
        spread_3m10y = round(s10[d] - s3m[d], 3)
        history.append({
            "date": d,
            "2y": s2[d], "10y": s10[d], "3m": s3m[d],
            "2s10s": spread_2s10s, "3m10y": spread_3m10y,
            "2s10s_inverted": spread_2s10s < 0,
            "3m10y_inverted": spread_3m10y < 0,
        })
    return history


def analyze(curve: dict, history: list[dict] | None = None) -> dict:
    y2 = curve.get("2Y")
    y10 = curve.get("10Y")
    y3m = curve.get("3M")
    spread_2s10s = round(y10 - y2, 3) if y10 is not None and y2 is not None else None
    spread_3m10y = round(y10 - y3m, 3) if y10 is not None and y3m is not None else None
    result = {
        "curve": curve,
        "spread_2s10s": spread_2s10s,
        "spread_3m10y": spread_3m10y,
        "inverted_2s10s": spread_2s10s < 0 if spread_2s10s is not None else None,
        "inverted_3m10y": spread_3m10y < 0 if spread_3m10y is not None else None,
    }
    if history:
        result["history"] = history
    return result


def format_text(data: dict) -> str:
    lines = ["US Treasury Yield Curve", "=" * 40]
    for label, value in data["curve"].items():
        bar = "*" * int(value * 4) if value else ""
        lines.append(f"  {label:>4s}: {value if value is not None else 'N/A':>6} {bar}")
    lines.append("")
    s1 = data.get("spread_2s10s")
    s2 = data.get("spread_3m10y")
    inv1 = " << INVERTED" if data.get("inverted_2s10s") else ""
    inv2 = " << INVERTED" if data.get("inverted_3m10y") else ""
    lines.append(f"  2s10s Spread: {s1}{inv1}" if s1 is not None else "  2s10s Spread: N/A")
    lines.append(f"  3m10y Spread: {s2}{inv2}" if s2 is not None else "  3m10y Spread: N/A")
    if data.get("history"):
        lines.append(f"\n  Spread History ({len(data['history'])} days):")
        lines.append(f"  {'Date':>12s}  {'2s10s':>7s}  {'3m10y':>7s}")
        for row in data["history"][-10:]:
            flag = " *" if row["2s10s_inverted"] or row["3m10y_inverted"] else ""
            lines.append(f"  {row['date']:>12s}  {row['2s10s']:>7.3f}  {row['3m10y']:>7.3f}{flag}")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="US Treasury yield curve and spread tracker.")
    parser.add_argument("--history", type=int, default=0, help="Show spread history for N days")
    parser.add_argument("--format", choices=["text", "json"], default="text")
    args = parser.parse_args()

    os.makedirs(DATA_DIR, exist_ok=True)
    curve = fetch_curve_snapshot()
    hist = fetch_spread_history(args.history) if args.history > 0 else None
    result = analyze(curve, hist)

    if args.format == "json":
        print(json.dumps(result, indent=2))
    else:
        print(format_text(result))


if __name__ == "__main__":
    main()
