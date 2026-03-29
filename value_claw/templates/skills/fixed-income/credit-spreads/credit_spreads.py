#!/usr/bin/env python3
"""Track investment-grade and high-yield credit spreads using FRED data."""

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


DATA_DIR = os.path.expanduser("~/.value_claw/credit-spreads")
FRED_CSV = "https://fred.stlouisfed.org/graph/fredgraph.csv"

INDICES = {
    "IG_OAS": {"series": "BAMLC0A0CM", "label": "US IG Corporate OAS"},
    "HY_OAS": {"series": "BAMLH0A0HYM2", "label": "US HY Corporate OAS"},
    "BBB_OAS": {"series": "BAMLC0A4CBBB", "label": "US BBB Corporate OAS"},
}


def fetch_series(series_id: str, days: int) -> list[tuple[str, float]]:
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


def compute_stats(values: list[float]) -> dict:
    if not values:
        return {}
    current = values[-1]
    lo = min(values)
    hi = max(values)
    sorted_vals = sorted(values)
    rank = sum(1 for v in sorted_vals if v <= current) / len(sorted_vals) * 100
    avg = sum(values) / len(values)
    trend = "widening" if len(values) >= 5 and current > avg else "tightening"
    return {
        "current": round(current, 2),
        "52w_low": round(lo, 2),
        "52w_high": round(hi, 2),
        "percentile": round(rank, 1),
        "average": round(avg, 2),
        "trend": trend,
    }


def fetch_all(history_days: int) -> dict:
    lookback = max(history_days, 365)
    result = {}
    for key, meta in INDICES.items():
        try:
            rows = fetch_series(meta["series"], lookback)
            values = [v for _, v in rows]
            stats = compute_stats(values)
            stats["label"] = meta["label"]
            stats["series"] = meta["series"]
            if history_days > 0:
                cutoff = (datetime.now() - timedelta(days=history_days)).strftime("%Y-%m-%d")
                stats["history"] = [
                    {"date": d, "value": v} for d, v in rows if d >= cutoff
                ]
            result[key] = stats
        except Exception as exc:
            result[key] = {"label": meta["label"], "error": str(exc)}
    return result


def format_text(data: dict) -> str:
    lines = ["Credit Spreads (OAS, bps)", "=" * 50]
    for key, info in data.items():
        if "error" in info:
            lines.append(f"\n  {info.get('label', key)}: ERROR - {info['error']}")
            continue
        lines.append(f"\n  {info['label']}")
        lines.append(f"    Current:     {info.get('current', 'N/A')} bps")
        lines.append(f"    52w Range:   {info.get('52w_low', '?')} - {info.get('52w_high', '?')} bps")
        lines.append(f"    Percentile:  {info.get('percentile', 'N/A')}%")
        lines.append(f"    Average:     {info.get('average', 'N/A')} bps")
        lines.append(f"    Trend:       {info.get('trend', 'N/A')}")
        if info.get("history"):
            lines.append(f"    History ({len(info['history'])} points):")
            for row in info["history"][-5:]:
                lines.append(f"      {row['date']}: {row['value']} bps")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Credit spread tracker (IG, HY, BBB).")
    parser.add_argument("--history", type=int, default=30, help="History window in days")
    parser.add_argument("--format", choices=["text", "json"], default="text")
    args = parser.parse_args()

    os.makedirs(DATA_DIR, exist_ok=True)
    data = fetch_all(args.history)

    if args.format == "json":
        print(json.dumps(data, indent=2))
    else:
        print(format_text(data))


if __name__ == "__main__":
    main()
