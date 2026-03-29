#!/usr/bin/env python3
"""Global liquidity dashboard — M2, Fed balance sheet, TGA, reverse repo."""

from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timedelta

import requests

DATA_DIR = os.path.expanduser("~/.value_claw/global_liquidity")
FRED_CSV_URL = "https://fred.stlouisfed.org/graph/fredgraph.csv"

SERIES = {
    "M2SL": {"label": "M2 Money Stock", "unit": "$B", "divisor": 1},
    "WALCL": {"label": "Fed Balance Sheet", "unit": "$M", "divisor": 1},
    "WTREGEN": {"label": "Treasury General Account", "unit": "$M", "divisor": 1},
    "RRPONTSYD": {"label": "Overnight Reverse Repo", "unit": "$M", "divisor": 1},
}


def _ensure_dir() -> None:
    os.makedirs(DATA_DIR, exist_ok=True)


def fetch_series(series_id: str, years: int = 2) -> list[dict]:
    """Fetch a FRED series as list of {date, value}."""
    start = (datetime.now() - timedelta(days=years * 365)).strftime("%Y-%m-%d")
    params = {"id": series_id, "cosd": start}
    resp = requests.get(FRED_CSV_URL, params=params, timeout=20)
    resp.raise_for_status()

    rows: list[dict] = []
    for line in resp.text.strip().splitlines()[1:]:
        parts = line.split(",")
        if len(parts) < 2 or parts[1].strip() == ".":
            continue
        try:
            rows.append({"date": parts[0].strip(), "value": float(parts[1].strip())})
        except ValueError:
            continue
    return rows


def week52_change(rows: list[dict]) -> float | None:
    """Compute approximate 52-week change in percent."""
    if len(rows) < 52:
        if len(rows) < 2:
            return None
        old = rows[0]["value"]
    else:
        old = rows[-52]["value"]
    current = rows[-1]["value"]
    if old == 0:
        return None
    return round(((current / old) - 1) * 100, 2)


def detect_trend(rows: list[dict], window: int = 4) -> str:
    """Simple trend detection over last `window` observations."""
    if len(rows) < window:
        return "insufficient data"
    recent = [r["value"] for r in rows[-window:]]
    diffs = [recent[i] - recent[i - 1] for i in range(1, len(recent))]
    avg_diff = sum(diffs) / len(diffs)
    threshold = abs(recent[-1]) * 0.001
    if avg_diff > threshold:
        return "rising"
    if avg_diff < -threshold:
        return "falling"
    return "stable"


def build_dashboard() -> dict:
    """Fetch all series and compute net liquidity."""
    results: dict[str, dict] = {}
    raw_latest: dict[str, float] = {}

    for series_id, meta in SERIES.items():
        rows = fetch_series(series_id)
        if not rows:
            results[series_id] = {
                "label": meta["label"], "latest": None, "date": None,
                "trend": "no data", "week52_change_pct": None,
            }
            continue

        latest = rows[-1]["value"]
        raw_latest[series_id] = latest
        results[series_id] = {
            "label": meta["label"],
            "latest": latest,
            "unit": meta["unit"],
            "date": rows[-1]["date"],
            "trend": detect_trend(rows),
            "week52_change_pct": week52_change(rows),
        }

    walcl = raw_latest.get("WALCL", 0)
    tga = raw_latest.get("WTREGEN", 0)
    rrp = raw_latest.get("RRPONTSYD", 0)
    net_liquidity = walcl - tga - rrp

    return {
        "series": results,
        "net_liquidity": {
            "value": net_liquidity,
            "formula": "WALCL - WTREGEN - RRPONTSYD",
            "components": {"WALCL": walcl, "WTREGEN": tga, "RRPONTSYD": rrp},
        },
    }


def format_text(data: dict) -> str:
    """Render liquidity dashboard as text."""
    lines = [
        "=" * 72,
        "  GLOBAL LIQUIDITY DASHBOARD",
        "  Generated: %s" % datetime.now().strftime("%Y-%m-%d %H:%M"),
        "=" * 72,
        "",
        "%-12s %-28s %14s %10s %10s" % ("Series", "Indicator", "Latest", "Trend", "52w Chg"),
        "-" * 72,
    ]

    for sid, row in data["series"].items():
        val = row["latest"]
        val_str = "{:,.0f}".format(val) if val is not None else "N/A"
        chg = row.get("week52_change_pct")
        chg_str = ("%+.2f%%" % chg) if chg is not None else "N/A"
        lines.append(
            "%-12s %-28s %14s %10s %10s"
            % (sid, row["label"], val_str, row.get("trend", "?"), chg_str)
        )

    lines.append("-" * 72)
    nl = data["net_liquidity"]
    lines.append("")
    lines.append("  NET LIQUIDITY = %s" % nl["formula"])
    lines.append("  = {:,.0f} - {:,.0f} - {:,.0f}".format(
        nl["components"]["WALCL"], nl["components"]["WTREGEN"], nl["components"]["RRPONTSYD"],
    ))
    lines.append("  = {:,.0f} ($M)".format(nl["value"]))
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Global Liquidity Dashboard")
    parser.add_argument("--format", choices=["text", "json"], default="text")
    args = parser.parse_args()

    _ensure_dir()
    print("Fetching liquidity indicators from FRED...")
    data = build_dashboard()

    if args.format == "json":
        print(json.dumps(data, indent=2))
    else:
        print(format_text(data))

    cache_path = os.path.join(DATA_DIR, "last_liquidity.json")
    with open(cache_path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2, default=str)
    print("Cached to: %s" % cache_path)


if __name__ == "__main__":
    main()
