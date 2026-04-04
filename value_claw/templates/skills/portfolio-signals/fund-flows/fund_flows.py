#!/usr/bin/env python3
"""ETF fund flow tracking via volume-price proxy analysis."""

from __future__ import annotations

import argparse
import json
import sys

DEFAULT_ETFS = ["SPY", "QQQ", "IWM", "GLD", "TLT", "HYG", "EEM", "XLF", "XLE", "ARKK"]

ETF_LABELS = {
    "SPY": "S&P 500",
    "QQQ": "Nasdaq 100",
    "IWM": "Russell 2000",
    "GLD": "Gold",
    "TLT": "20+ Year Treasury",
    "HYG": "High Yield Corporate",
    "EEM": "Emerging Markets",
    "XLF": "Financials",
    "XLE": "Energy",
    "ARKK": "ARK Innovation",
}


def analyze_etf(ticker: str, period: str = "1mo") -> dict:
    """Compute relative volume and flow signal for an ETF."""
    try:
        import yfinance as yf
    except ImportError:
        return {"ticker": ticker, "error": "yfinance not installed"}

    try:
        etf = yf.Ticker(ticker)
        hist = etf.history(period=period)
    except Exception as exc:
        return {"ticker": ticker, "error": str(exc)}

    if hist.empty or len(hist) < 5:
        return {"ticker": ticker, "error": "Insufficient data"}

    latest = hist.iloc[-1]
    current_volume = int(latest["Volume"])
    current_close = float(latest["Close"])
    prev_close = float(hist.iloc[-2]["Close"])
    price_change_pct = ((current_close - prev_close) / prev_close) * 100

    lookback = min(20, len(hist) - 1)
    avg_volume = int(hist["Volume"].iloc[-lookback - 1 : -1].mean())
    rel_volume = (current_volume / avg_volume) if avg_volume > 0 else 0

    if rel_volume > 1.3 and price_change_pct > 0:
        flow_signal = "INFLOW"
    elif rel_volume > 1.3 and price_change_pct < 0:
        flow_signal = "OUTFLOW"
    elif rel_volume < 0.7:
        flow_signal = "LOW ACTIVITY"
    else:
        flow_signal = "NEUTRAL"

    period_return = (
        (current_close - float(hist.iloc[0]["Close"]))
        / float(hist.iloc[0]["Close"])
    ) * 100

    return {
        "ticker": ticker.upper(),
        "name": ETF_LABELS.get(ticker.upper(), ticker),
        "price": round(current_close, 2),
        "priceChangePct": round(price_change_pct, 2),
        "currentVolume": current_volume,
        "avgVolume20d": avg_volume,
        "relativeVolume": round(rel_volume, 2),
        "flowSignal": flow_signal,
        "periodReturn": round(period_return, 2),
    }


def format_text(results: list[dict]) -> str:
    """Render results as a readable table."""
    lines = []
    lines.append("ETF Fund Flow Analysis")
    lines.append("=" * 80)

    header = (
        "%-6s %-20s %8s %7s %8s %8s  %-12s"
        % ("Ticker", "Name", "Price", "Chg%", "RelVol", "20dAvg", "Signal")
    )
    lines.append(header)
    lines.append("-" * 80)

    inflows = []
    outflows = []

    for r in results:
        if "error" in r:
            lines.append("%-6s ERROR: %s" % (r["ticker"], r["error"]))
            continue

        signal = r["flowSignal"]
        if signal == "INFLOW":
            inflows.append(r["ticker"])
        elif signal == "OUTFLOW":
            outflows.append(r["ticker"])

        lines.append(
            "%-6s %-20s %8.2f %+6.2f%% %7.2fx %8s  %-12s"
            % (
                r["ticker"],
                r["name"][:20],
                r["price"],
                r["priceChangePct"],
                r["relativeVolume"],
                _fmt_vol(r["avgVolume20d"]),
                signal,
            )
        )

    lines.append("-" * 80)

    if inflows:
        lines.append("Inflow signals:  %s" % ", ".join(inflows))
    if outflows:
        lines.append("Outflow signals: %s" % ", ".join(outflows))
    if not inflows and not outflows:
        lines.append("No strong flow signals detected.")

    return "\n".join(lines)


def _fmt_vol(n: int) -> str:
    if n >= 1e9:
        return "%.1fB" % (n / 1e9)
    if n >= 1e6:
        return "%.1fM" % (n / 1e6)
    if n >= 1e3:
        return "%.0fK" % (n / 1e3)
    return str(n)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="ETF fund flow tracking via volume-price proxy"
    )
    parser.add_argument("--etfs", nargs="+", help="Specific ETFs to analyze")
    parser.add_argument(
        "--all",
        action="store_true",
        help="Analyze all default ETFs",
    )
    parser.add_argument(
        "--format",
        choices=["text", "json"],
        default="text",
        help="Output format (default: text)",
    )
    args = parser.parse_args()

    if not args.etfs and not args.all:
        parser.print_help()
        print("\nSpecify --etfs or --all", file=sys.stderr)
        sys.exit(1)

    tickers = [t.upper() for t in args.etfs] if args.etfs else DEFAULT_ETFS

    results = []
    for ticker in tickers:
        results.append(analyze_etf(ticker))

    if args.format == "json":
        print(json.dumps(results, indent=2, default=str))
    else:
        print(format_text(results))


if __name__ == "__main__":
    main()
