#!/usr/bin/env python3
"""Analyze short interest and short squeeze potential for given tickers."""

from __future__ import annotations

import argparse
import json


def fetch_short_data(ticker: str) -> dict:
    """Fetch short interest metrics via yfinance."""
    try:
        import yfinance as yf
    except ImportError:
        return {"ticker": ticker, "error": "yfinance not installed"}

    try:
        stock = yf.Ticker(ticker)
        info = stock.info or {}
    except Exception as exc:
        return {"ticker": ticker, "error": str(exc)}

    shares_short = info.get("sharesShort")
    shares_float = info.get("floatShares")
    short_pct = info.get("shortPercentOfFloat")
    short_ratio = info.get("shortRatio")
    prev_shares_short = info.get("sharesShortPriorMonth")
    price = (
        info.get("currentPrice")
        or info.get("regularMarketPrice")
        or info.get("previousClose")
    )
    avg_volume = info.get("averageDailyVolume10Day") or info.get("averageVolume")

    if short_pct is not None:
        short_pct_display = round(short_pct * 100, 2)
    elif shares_short and shares_float and shares_float > 0:
        short_pct_display = round((shares_short / shares_float) * 100, 2)
    else:
        short_pct_display = None

    short_change = None
    if shares_short is not None and prev_shares_short is not None:
        if prev_shares_short > 0:
            short_change = round(
                ((shares_short - prev_shares_short) / prev_shares_short) * 100, 2
            )

    high_si = short_pct_display is not None and short_pct_display > 15
    high_dtc = short_ratio is not None and short_ratio > 5
    squeeze_risk = high_si and high_dtc

    return {
        "ticker": ticker.upper(),
        "name": info.get("shortName", ticker),
        "price": round(price, 2) if price else None,
        "sharesShort": shares_short,
        "sharesFloat": shares_float,
        "shortPercentOfFloat": short_pct_display,
        "shortRatio": round(short_ratio, 2) if short_ratio else None,
        "prevSharesShort": prev_shares_short,
        "shortChangeFromPriorMonth": short_change,
        "avgVolume": avg_volume,
        "flags": {
            "highShortInterest": high_si,
            "highDaysToCover": high_dtc,
            "squeezeRisk": squeeze_risk,
        },
    }


def format_text(results: list[dict]) -> str:
    """Render results as a human-readable report."""
    lines = []
    for r in results:
        if "error" in r:
            lines.append("%s: ERROR - %s" % (r["ticker"], r["error"]))
            lines.append("")
            continue

        lines.append("=" * 55)
        lines.append("  %s -- %s" % (r["ticker"], r.get("name", "")))
        lines.append("=" * 55)
        lines.append("  Price:                   $%s" % (r.get("price") or "N/A"))
        lines.append(
            "  Shares Short:            %s" % _fmt_num(r.get("sharesShort"))
        )
        lines.append(
            "  Float:                   %s" % _fmt_num(r.get("sharesFloat"))
        )

        si_str = "%s%%" % r["shortPercentOfFloat"] if r.get("shortPercentOfFloat") is not None else "N/A"
        lines.append("  Short %% of Float:        %s" % si_str)

        sr_str = "%s days" % r["shortRatio"] if r.get("shortRatio") is not None else "N/A"
        lines.append("  Days to Cover:           %s" % sr_str)

        chg = r.get("shortChangeFromPriorMonth")
        chg_str = "%+.1f%%" % chg if chg is not None else "N/A"
        lines.append("  Short Change (MoM):      %s" % chg_str)

        flags = r.get("flags", {})
        alerts = []
        if flags.get("highShortInterest"):
            alerts.append("HIGH SHORT INTEREST (>15%%)")
        if flags.get("highDaysToCover"):
            alerts.append("HIGH DAYS-TO-COVER (>5)")
        if flags.get("squeezeRisk"):
            alerts.append("** SQUEEZE RISK **")

        if alerts:
            lines.append("  Alerts:                  %s" % " | ".join(alerts))
        lines.append("")

    return "\n".join(lines)


def _fmt_num(n) -> str:
    if n is None:
        return "N/A"
    if abs(n) >= 1e9:
        return "%.2fB" % (n / 1e9)
    if abs(n) >= 1e6:
        return "%.1fM" % (n / 1e6)
    return "{:,}".format(int(n))


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Short interest and squeeze potential analysis"
    )
    parser.add_argument(
        "--tickers", nargs="+", required=True, help="Tickers to analyze"
    )
    parser.add_argument(
        "--format",
        choices=["text", "json"],
        default="text",
        help="Output format (default: text)",
    )
    args = parser.parse_args()

    results = []
    for ticker in args.tickers:
        results.append(fetch_short_data(ticker.upper()))

    if args.format == "json":
        print(json.dumps(results, indent=2, default=str))
    else:
        print(format_text(results))


if __name__ == "__main__":
    main()
