#!/usr/bin/env python3
"""ESG (Environmental, Social, Governance) analysis using yfinance data."""

from __future__ import annotations

import argparse
import json
import sys

try:
    import yfinance as yf
except ImportError:
    print("Error: yfinance not installed.  Run: pip install yfinance", file=sys.stderr)
    sys.exit(1)

SECTOR_DEFAULTS = {
    "Technology": {"total": 18.0, "env": 3.0, "social": 8.0, "gov": 7.0},
    "Financial Services": {"total": 20.0, "env": 2.5, "social": 9.0, "gov": 8.5},
    "Healthcare": {"total": 22.0, "env": 5.0, "social": 10.0, "gov": 7.0},
    "Energy": {"total": 32.0, "env": 15.0, "social": 10.0, "gov": 7.0},
    "Consumer Cyclical": {"total": 21.0, "env": 5.0, "social": 9.0, "gov": 7.0},
    "Industrials": {"total": 24.0, "env": 8.0, "social": 9.0, "gov": 7.0},
    "Communication Services": {"total": 19.0, "env": 3.0, "social": 9.0, "gov": 7.0},
    "Consumer Defensive": {"total": 23.0, "env": 7.0, "social": 9.0, "gov": 7.0},
    "Utilities": {"total": 27.0, "env": 12.0, "social": 8.0, "gov": 7.0},
    "Real Estate": {"total": 20.0, "env": 5.0, "social": 8.0, "gov": 7.0},
    "Basic Materials": {"total": 28.0, "env": 11.0, "social": 9.0, "gov": 8.0},
}
DEFAULT_ESG = {"total": 22.0, "env": 6.0, "social": 9.0, "gov": 7.0}


def analyze_esg(symbol: str) -> dict:
    """Fetch ESG data for a single ticker."""
    t = yf.Ticker(symbol)
    info = t.info
    sector = info.get("sector", "Unknown")
    name = info.get("shortName", symbol)

    esg_data = None
    try:
        sus = t.sustainability
        if sus is not None and not sus.empty:
            esg_data = sus.to_dict().get(sus.columns[0], {}) if len(sus.columns) else {}
    except Exception:
        pass

    if esg_data and esg_data.get("totalEsg") is not None:
        result = {
            "symbol": symbol.upper(),
            "name": name,
            "sector": sector,
            "data_source": "yfinance",
            "total_esg": _safe_round(esg_data.get("totalEsg")),
            "environmental": _safe_round(esg_data.get("environmentScore")),
            "social": _safe_round(esg_data.get("socialScore")),
            "governance": _safe_round(esg_data.get("governanceScore")),
            "controversy_level": esg_data.get("highestControversy", "N/A"),
            "esg_performance": esg_data.get("esgPerformance", "N/A"),
            "peer_group": esg_data.get("peerGroup", sector),
        }
    else:
        defaults = SECTOR_DEFAULTS.get(sector, DEFAULT_ESG)
        result = {
            "symbol": symbol.upper(),
            "name": name,
            "sector": sector,
            "data_source": "sector_estimate",
            "total_esg": defaults["total"],
            "environmental": defaults["env"],
            "social": defaults["social"],
            "governance": defaults["gov"],
            "controversy_level": "N/A",
            "esg_performance": "N/A",
            "peer_group": sector,
        }

    result["rating"] = _esg_rating(result["total_esg"])
    return result


def _safe_round(val) -> float | None:
    if val is None:
        return None
    try:
        return round(float(val), 1)
    except (TypeError, ValueError):
        return None


def _esg_rating(total: float | None) -> str:
    if total is None:
        return "N/A"
    if total <= 10:
        return "Negligible Risk"
    if total <= 20:
        return "Low Risk"
    if total <= 30:
        return "Medium Risk"
    if total <= 40:
        return "High Risk"
    return "Severe Risk"


def format_text(results: list[dict]) -> str:
    lines = ["=" * 70, "  ESG ANALYSIS (lower score = better)", "=" * 70, ""]
    hdr = "{:<7} {:<18} {:>8} {:>6} {:>6} {:>6} {:>8} {:<16}".format(
        "Ticker", "Name", "Total", "Env", "Soc", "Gov", "Controv", "Rating")
    lines.append(hdr)
    lines.append("-" * 80)
    for r in results:
        if "error" in r:
            lines.append("{}: Error - {}".format(r["symbol"], r["error"]))
            continue
        total = "{:.1f}".format(r["total_esg"]) if r["total_esg"] else "N/A"
        env = "{:.1f}".format(r["environmental"]) if r["environmental"] else "N/A"
        soc = "{:.1f}".format(r["social"]) if r["social"] else "N/A"
        gov = "{:.1f}".format(r["governance"]) if r["governance"] else "N/A"
        ctr = str(r["controversy_level"])
        src = " *" if r["data_source"] == "sector_estimate" else ""
        lines.append("{:<7} {:<18} {:>8} {:>6} {:>6} {:>6} {:>8} {:<16}{}".format(
            r["symbol"], r["name"][:17], total, env, soc, gov, ctr, r["rating"], src))
    lines.append("")
    lines.append("  * = sector-average estimate (live ESG data unavailable)")
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="ESG analysis using yfinance")
    parser.add_argument("--tickers", nargs="+", required=True, help="Tickers to analyze")
    parser.add_argument("--format", choices=["text", "json"], default="text", help="Output format")
    args = parser.parse_args()

    results = []
    for sym in args.tickers:
        try:
            results.append(analyze_esg(sym.strip()))
        except Exception as exc:
            results.append({"symbol": sym.upper(), "error": str(exc)})

    if args.format == "json":
        print(json.dumps(results, indent=2))
    else:
        print(format_text(results))


if __name__ == "__main__":
    main()
