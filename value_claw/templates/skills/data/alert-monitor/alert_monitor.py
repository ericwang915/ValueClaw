#!/usr/bin/env python3
"""Price and indicator alert monitor with persistent storage."""

from __future__ import annotations

import argparse
import datetime
import json
import os
import re
import sys
import uuid

try:
    import yfinance as yf
except ImportError:
    print("Error: yfinance not installed.  Run: pip install yfinance", file=sys.stderr)
    sys.exit(1)

ALERTS_DIR = os.path.expanduser("~/.value_claw/alerts")
ALERTS_FILE = os.path.join(ALERTS_DIR, "alerts.json")
CONDITION_RE = re.compile(r"(price|rsi|volume)\s*([><])\s*([\d.]+)", re.IGNORECASE)


def load_alerts() -> list[dict]:
    if not os.path.exists(ALERTS_FILE):
        return []
    with open(ALERTS_FILE) as f:
        return json.load(f)


def save_alerts(alerts: list[dict]) -> None:
    os.makedirs(ALERTS_DIR, exist_ok=True)
    with open(ALERTS_FILE, "w") as f:
        json.dump(alerts, f, indent=2)


def parse_condition(cond_str: str) -> dict | None:
    m = CONDITION_RE.match(cond_str.strip())
    if not m:
        return None
    return {"metric": m.group(1).lower(), "operator": m.group(2), "threshold": float(m.group(3))}


def compute_rsi(closes: list[float], window: int = 14) -> float | None:
    if len(closes) < window + 1:
        return None
    deltas = [closes[i] - closes[i - 1] for i in range(1, len(closes))]
    gains = [max(d, 0.0) for d in deltas[-window:]]
    losses = [max(-d, 0.0) for d in deltas[-window:]]
    avg_gain, avg_loss = sum(gains) / window, sum(losses) / window
    if avg_loss == 0:
        return 100.0
    return round(100 - (100 / (1 + avg_gain / avg_loss)), 1)


def get_metrics(ticker: str) -> dict:
    t = yf.Ticker(ticker)
    info = t.info
    price = info.get("currentPrice") or info.get("regularMarketPrice")
    rsi = None
    try:
        hist = t.history(period="1mo")
        if not hist.empty:
            rsi = compute_rsi(hist["Close"].tolist())
    except Exception:
        pass
    return {"price": price, "volume": info.get("volume"), "rsi": rsi}


def evaluate(cond: dict, metrics: dict) -> bool:
    val = metrics.get(cond["metric"])
    if val is None:
        return False
    return val > cond["threshold"] if cond["operator"] == ">" else val < cond["threshold"]


def add_alert(ticker: str, cond_str: str) -> None:
    parsed = parse_condition(cond_str)
    if not parsed:
        print("Invalid condition: {}".format(cond_str), file=sys.stderr)
        sys.exit(1)
    alerts = load_alerts()
    alert = {
        "id": str(uuid.uuid4())[:8], "ticker": ticker.upper(),
        "condition": cond_str.strip(), "parsed": parsed,
        "created": datetime.datetime.now().isoformat(),
    }
    alerts.append(alert)
    save_alerts(alerts)
    print("Alert added: {} {} (id: {})".format(alert["ticker"], alert["condition"], alert["id"]))


def list_alerts(fmt: str) -> None:
    alerts = load_alerts()
    if fmt == "json":
        print(json.dumps(alerts, indent=2))
        return
    if not alerts:
        print("No alerts configured.")
        return
    print("=" * 55)
    print("  CONFIGURED ALERTS")
    print("=" * 55)
    print("\n{:<10} {:<8} {:<25} {}".format("ID", "Ticker", "Condition", "Created"))
    print("-" * 60)
    for a in alerts:
        print("{:<10} {:<8} {:<25} {}".format(a["id"], a["ticker"], a["condition"], a["created"][:10]))
    print()


def check_alerts(fmt: str) -> None:
    alerts = load_alerts()
    if not alerts:
        print("No alerts configured.")
        return
    cache = {}
    for sym in {a["ticker"] for a in alerts}:
        try:
            cache[sym] = get_metrics(sym)
        except Exception as exc:
            cache[sym] = {"error": str(exc)}
    results = []
    for a in alerts:
        m = cache.get(a["ticker"], {})
        parsed = a.get("parsed") or parse_condition(a["condition"])
        if not parsed:
            continue
        triggered = evaluate(parsed, m) if "error" not in m else False
        results.append({"id": a["id"], "ticker": a["ticker"], "condition": a["condition"],
                        "triggered": triggered, "current_value": m.get(parsed["metric"])})
    if fmt == "json":
        print(json.dumps(results, indent=2))
        return
    print("=" * 60)
    print("  ALERT CHECK RESULTS")
    print("=" * 60)
    fired = [r for r in results if r["triggered"]]
    quiet = [r for r in results if not r["triggered"]]
    if fired:
        print("\n  TRIGGERED:")
        for r in fired:
            v = r["current_value"]
            print("    [!] {} {} (current: {})".format(r["ticker"], r["condition"],
                  "{:.2f}".format(v) if isinstance(v, float) else v))
    else:
        print("\n  No alerts triggered.")
    if quiet:
        print("\n  Not triggered:")
        for r in quiet:
            v = r["current_value"]
            print("    [ ] {} {} (current: {})".format(r["ticker"], r["condition"],
                  "{:.2f}".format(v) if isinstance(v, float) else v))
    print()


def main() -> None:
    parser = argparse.ArgumentParser(description="Price and indicator alert monitor")
    grp = parser.add_mutually_exclusive_group(required=True)
    grp.add_argument("--add", action="store_true", help="Add a new alert")
    grp.add_argument("--list", action="store_true", help="List all alerts")
    grp.add_argument("--check", action="store_true", help="Check alerts against live data")
    parser.add_argument("--ticker", help="Ticker (with --add)")
    parser.add_argument("--condition", help="e.g. 'price > 200'")
    parser.add_argument("--format", choices=["text", "json"], default="text")
    args = parser.parse_args()
    if args.add:
        if not args.ticker or not args.condition:
            print("--add requires --ticker and --condition", file=sys.stderr)
            sys.exit(1)
        add_alert(args.ticker, args.condition)
    elif args.list:
        list_alerts(args.format)
    else:
        check_alerts(args.format)


if __name__ == "__main__":
    main()
