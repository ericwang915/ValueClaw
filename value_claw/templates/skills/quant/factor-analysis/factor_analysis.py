#!/usr/bin/env python3
"""Fama-French 3-factor analysis — decompose returns via OLS (numpy only)."""

from __future__ import annotations

import argparse
import io
import json
import os
import sys
import zipfile

import numpy as np
import requests

DATA_DIR = os.path.expanduser("~/.value_claw/factor_analysis")
FF3_URL = (
    "https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/"
    "ftp/F-F_Research_Data_Factors_daily_CSV.zip"
)

PERIOD_MAP = {"1y": 252, "2y": 504, "3y": 756, "5y": 1260}


def _ensure_dir() -> None:
    os.makedirs(DATA_DIR, exist_ok=True)


def fetch_ff3_factors() -> dict[str, dict]:
    """Download and parse Fama-French 3-factor daily data. Returns {date: {Mkt-RF, SMB, HML, RF}}."""
    resp = requests.get(FF3_URL, timeout=30)
    resp.raise_for_status()

    zf = zipfile.ZipFile(io.BytesIO(resp.content))
    csv_name = [n for n in zf.namelist() if n.endswith(".CSV") or n.endswith(".csv")][0]
    raw = zf.read(csv_name).decode("utf-8")

    factors: dict[str, dict] = {}
    started = False
    for line in raw.splitlines():
        stripped = line.strip()
        if not stripped:
            if started:
                break
            continue
        parts = [p.strip() for p in stripped.split(",")]
        if len(parts) < 5 or not parts[0].isdigit() or len(parts[0]) != 8:
            continue
        started = True
        d = parts[0]
        key = "%s-%s-%s" % (d[:4], d[4:6], d[6:8])
        try:
            factors[key] = {"Mkt-RF": float(parts[1]) / 100, "SMB": float(parts[2]) / 100,
                            "HML": float(parts[3]) / 100, "RF": float(parts[4]) / 100}
        except (ValueError, IndexError):
            continue
    return factors


def fetch_stock_returns(ticker: str, days: int) -> dict[str, float]:
    """Fetch daily returns via yfinance. Returns {date: daily_return}."""
    try:
        import yfinance as yf
    except ImportError:
        print("yfinance not installed. Run: pip install yfinance", file=sys.stderr)
        sys.exit(1)

    period_str = "%dd" % (days + 30)
    df = yf.download(ticker, period=period_str, progress=False)
    if df.empty:
        print("No data for %s" % ticker, file=sys.stderr)
        sys.exit(1)

    closes = df["Close"].values.flatten().astype(float)
    dates = [d.strftime("%Y-%m-%d") for d in df.index]
    returns: dict[str, float] = {}
    for i in range(1, len(closes)):
        if closes[i - 1] != 0:
            returns[dates[i]] = (closes[i] - closes[i - 1]) / closes[i - 1]
    return returns


def run_ols(y: np.ndarray, x: np.ndarray) -> dict:
    """OLS regression via numpy least squares. x should include intercept column."""
    result = np.linalg.lstsq(x, y, rcond=None)
    coeffs = result[0]

    y_hat = x @ coeffs
    ss_res = float(np.sum((y - y_hat) ** 2))
    ss_tot = float(np.sum((y - np.mean(y)) ** 2))
    r_squared = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0

    return {"coefficients": coeffs.tolist(), "r_squared": r_squared}


def analyze(ticker: str, period: str) -> dict:
    """Run full Fama-French 3-factor analysis."""
    days = PERIOD_MAP.get(period, 756)
    print("Fetching Fama-French factor data...")
    ff_data = fetch_ff3_factors()
    print("  %d factor observations loaded." % len(ff_data))

    print("Fetching returns for %s..." % ticker)
    stock_ret = fetch_stock_returns(ticker, days)
    print("  %d daily returns loaded." % len(stock_ret))

    common_dates = sorted(set(stock_ret.keys()) & set(ff_data.keys()))
    common_dates = common_dates[-days:] if len(common_dates) > days else common_dates

    if len(common_dates) < 30:
        return {"error": "Too few overlapping dates (%d). Need at least 30." % len(common_dates)}

    y_vals = []
    x_vals = []
    for d in common_dates:
        ri = stock_ret[d]
        ff = ff_data[d]
        y_vals.append(ri - ff["RF"])
        x_vals.append([1.0, ff["Mkt-RF"], ff["SMB"], ff["HML"]])

    y = np.array(y_vals)
    x = np.array(x_vals)
    ols = run_ols(y, x)

    c = ols["coefficients"]
    alpha_annual = ((1 + c[0]) ** 252 - 1) * 100
    return {
        "ticker": ticker.upper(), "period": period, "observations": len(common_dates),
        "date_range": {"start": common_dates[0], "end": common_dates[-1]},
        "alpha_daily": round(c[0], 6), "alpha_annual_pct": round(alpha_annual, 2),
        "beta_market": round(c[1], 4), "smb_loading": round(c[2], 4),
        "hml_loading": round(c[3], 4), "r_squared": round(ols["r_squared"], 4),
    }


def format_text(result: dict) -> str:
    """Render factor analysis as text."""
    if "error" in result:
        return "ERROR: %s" % result["error"]
    lines = [
        "=" * 56,
        "  FAMA-FRENCH 3-FACTOR ANALYSIS: %s" % result["ticker"],
        "  Period: %s (%s to %s)" % (
            result["period"], result["date_range"]["start"], result["date_range"]["end"]),
        "  Observations: %d" % result["observations"],
        "=" * 56,
        "",
        "  Ri - Rf = alpha + beta*(Rm-Rf) + s*SMB + h*HML",
        "",
        "  %-20s %10s" % ("Factor", "Loading"),
        "  " + "-" * 32,
        "  %-20s %+10.6f  (%.2f%% annualized)" % (
            "Alpha (intercept)", result["alpha_daily"], result["alpha_annual_pct"]),
        "  %-20s %+10.4f" % ("Beta (Market)", result["beta_market"]),
        "  %-20s %+10.4f" % ("SMB (Size)", result["smb_loading"]),
        "  %-20s %+10.4f" % ("HML (Value)", result["hml_loading"]),
        "",
        "  R-squared:  %.4f  (%.1f%% of variance explained)" % (
            result["r_squared"], result["r_squared"] * 100),
        "",
    ]

    for label, val, pos_msg, neg_msg, thresh in [
        ("Beta", result["beta_market"], "more volatile than market", "less volatile than market", (1.2, 0.8)),
        ("SMB", result["smb_loading"], "small-cap characteristics", "large-cap characteristics", (0.3, -0.3)),
        ("HML", result["hml_loading"], "value-stock characteristics", "growth-stock characteristics", (0.3, -0.3)),
    ]:
        if val > thresh[0]:
            lines.append("  -> %s=%+.2f: %s." % (label, val, pos_msg))
        elif val < thresh[1]:
            lines.append("  -> %s=%+.2f: %s." % (label, val, neg_msg))
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Fama-French 3-Factor Analysis")
    parser.add_argument("--ticker", required=True, help="Stock ticker")
    parser.add_argument("--period", default="3y", choices=["1y", "2y", "3y", "5y"])
    parser.add_argument("--format", choices=["text", "json"], default="text")
    args = parser.parse_args()

    _ensure_dir()
    result = analyze(args.ticker, args.period)

    if args.format == "json":
        print(json.dumps(result, indent=2))
    else:
        print(format_text(result))

    cache_path = os.path.join(DATA_DIR, "last_analysis.json")
    with open(cache_path, "w", encoding="utf-8") as fh:
        json.dump(result, fh, indent=2)
    print("Cached to: %s" % cache_path)


if __name__ == "__main__":
    main()
