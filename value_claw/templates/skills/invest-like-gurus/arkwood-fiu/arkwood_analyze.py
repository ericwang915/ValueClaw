#!/usr/bin/env python3
"""
ARKWOOD Financial Intelligence Unit — data collection, scoring, and report generation.

Fetches real-time market data, computes the Technology-Valuation Score (0-125),
and outputs structured analysis data for each ticker.

Usage:
    python arkwood_analyze.py TSLA PLTR NVDA
    python arkwood_analyze.py TSLA --format json
    python arkwood_analyze.py TSLA --quick
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import os
import sys
from datetime import datetime, timezone

import requests

DATA_DIR = os.path.expanduser("~/.value_claw/arkwood")

ARK_ETFS = {
    "ARKK": "ARK Innovation ETF",
    "ARKW": "ARK Next Generation Internet ETF",
    "ARKQ": "ARK Autonomous Tech & Robotics ETF",
    "ARKG": "ARK Genomic Revolution ETF",
    "ARKF": "ARK Fintech Innovation ETF",
    "ARKX": "ARK Space Exploration & Innovation ETF",
}

ARK_HOLDINGS_URL = (
    "https://ark-funds.com/wp-content/uploads/funds-etf-csv/ARK_INNOVATION_ETF_{etf}_HOLDINGS.csv"
)

DISRUPTIVE_SECTORS = {
    "Artificial Intelligence", "Robotics & Automation", "Energy Storage",
    "Genomics / MedTech", "Blockchain / Fintech", "Electric Vehicles",
    "Space Technology", "3D Printing", "Cloud / SaaS", "Cybersecurity",
    "Semiconductors", "Quantum Computing",
}


def _ensure_dir():
    for sub in ("cache", "reports"):
        os.makedirs(os.path.join(DATA_DIR, sub), exist_ok=True)


def fetch_stock_data(ticker: str) -> dict:
    """Fetch fundamentals and price data via yfinance."""
    try:
        import yfinance as yf
    except ImportError:
        return {"error": "yfinance not installed — run: pip install yfinance"}

    try:
        stock = yf.Ticker(ticker)
        info = stock.info or {}
    except Exception as e:
        return {"error": f"Failed to fetch data for {ticker}: {e}"}

    price = info.get("currentPrice") or info.get("regularMarketPrice") or info.get("previousClose", 0)
    market_cap = info.get("marketCap", 0)

    trailing_eps = info.get("trailingEps")
    forward_eps = info.get("forwardEps")
    trailing_pe = info.get("trailingPE") or (price / trailing_eps if trailing_eps and trailing_eps > 0 else None)
    forward_pe = info.get("forwardPE") or (price / forward_eps if forward_eps and forward_eps > 0 else None)

    rev_growth = info.get("revenueGrowth")
    gross_margin = info.get("grossMargins")
    op_margin = info.get("operatingMargins")
    fcf = info.get("freeCashflow")
    total_cash = info.get("totalCash", 0)
    total_debt = info.get("totalDebt", 0)

    target_mean = info.get("targetMeanPrice")
    target_high = info.get("targetHighPrice")
    target_low = info.get("targetLowPrice")
    num_analysts = info.get("numberOfAnalystOpinions", 0)
    recommendation = info.get("recommendationKey", "")

    upside_pct = ((target_mean / price) - 1) * 100 if target_mean and price else None

    eps_growth = None
    if trailing_eps and forward_eps and trailing_eps > 0:
        eps_growth = ((forward_eps / trailing_eps) - 1) * 100

    peg = None
    if forward_pe and eps_growth and eps_growth > 0:
        peg = forward_pe / eps_growth

    gross_margin_expanding = None
    try:
        financials = stock.quarterly_financials
        if financials is not None and not financials.empty:
            gp_row = financials.loc["Gross Profit"] if "Gross Profit" in financials.index else None
            rev_row = financials.loc["Total Revenue"] if "Total Revenue" in financials.index else None
            if gp_row is not None and rev_row is not None and len(gp_row) >= 4:
                recent_gm = float(gp_row.iloc[0]) / float(rev_row.iloc[0]) if float(rev_row.iloc[0]) else 0
                older_gm = float(gp_row.iloc[3]) / float(rev_row.iloc[3]) if float(rev_row.iloc[3]) else 0
                gross_margin_expanding = recent_gm > older_gm
    except Exception:
        pass

    profitable = (fcf and fcf > 0) or (op_margin and op_margin > 0)
    burn_rate = info.get("operatingCashflow")
    cash_runway_months = None
    if total_cash and burn_rate and burn_rate < 0:
        cash_runway_months = abs(total_cash / (burn_rate / 12))

    return {
        "ticker": ticker.upper(),
        "name": info.get("shortName", ticker),
        "sector": info.get("sector", ""),
        "industry": info.get("industry", ""),
        "price": round(price, 2) if price else None,
        "marketCap": market_cap,
        "marketCapB": round(market_cap / 1e9, 2) if market_cap else None,
        "trailingPE": round(trailing_pe, 2) if trailing_pe else None,
        "forwardPE": round(forward_pe, 2) if forward_pe else None,
        "trailingEPS": round(trailing_eps, 2) if trailing_eps else None,
        "forwardEPS": round(forward_eps, 2) if forward_eps else None,
        "revenueGrowthPct": round(rev_growth * 100, 1) if rev_growth else None,
        "grossMarginPct": round(gross_margin * 100, 1) if gross_margin else None,
        "opMarginPct": round(op_margin * 100, 1) if op_margin else None,
        "grossMarginExpanding": gross_margin_expanding,
        "fcf": fcf,
        "totalCash": total_cash,
        "totalDebt": total_debt,
        "cashRunwayMonths": round(cash_runway_months, 0) if cash_runway_months else None,
        "profitable": profitable,
        "peg": round(peg, 2) if peg else None,
        "epsGrowthPct": round(eps_growth, 1) if eps_growth else None,
        "targetMean": target_mean,
        "targetHigh": target_high,
        "targetLow": target_low,
        "upsidePct": round(upside_pct, 1) if upside_pct else None,
        "numAnalysts": num_analysts,
        "recommendation": recommendation,
        "rdExpenseRatio": None,
        "beta": info.get("beta"),
        "52wHigh": info.get("fiftyTwoWeekHigh"),
        "52wLow": info.get("fiftyTwoWeekLow"),
        "dividendYield": info.get("dividendYield"),
    }


def fetch_ark_holdings() -> dict[str, list[dict]]:
    """Fetch current ARK ETF holdings. Returns {ticker: [{etf, weight, shares}]}."""
    holdings: dict[str, list[dict]] = {}

    for etf in ARK_ETFS:
        url = f"https://ark-funds.com/wp-content/uploads/funds-etf-csv/ARK_{_etf_full_name(etf)}_HOLDINGS.csv"
        try:
            resp = requests.get(url, timeout=15, headers={"User-Agent": "ValueClaw/1.0"})
            if resp.status_code != 200:
                continue
            reader = csv.DictReader(io.StringIO(resp.text))
            for row in reader:
                ticker = (row.get("ticker") or row.get("Ticker") or "").strip()
                weight = row.get("weight(%)") or row.get("Weight(%)") or row.get("weight") or "0"
                if not ticker or ticker == "N/A":
                    continue
                try:
                    w = float(weight.replace("%", ""))
                except (ValueError, AttributeError):
                    w = 0
                entry = {"etf": etf, "weight": w, "shares": row.get("shares", "")}
                holdings.setdefault(ticker.upper(), []).append(entry)
        except Exception:
            continue

    return holdings


def _etf_full_name(etf_code: str) -> str:
    mapping = {
        "ARKK": "INNOVATION_ETF_ARKK",
        "ARKW": "NEXT_GENERATION_INTERNET_ETF_ARKW",
        "ARKQ": "AUTONOMOUS_TECH_ROBOTICS_ETF_ARKQ",
        "ARKG": "GENOMIC_REVOLUTION_ETF_ARKG",
        "ARKF": "FINTECH_INNOVATION_ETF_ARKF",
        "ARKX": "SPACE_EXPLORATION_INNOVATION_ETF_ARKX",
    }
    return mapping.get(etf_code, etf_code)


def compute_score(data: dict, ark_holdings: dict) -> dict:
    """Compute the Technology-Valuation Score (0-125).

    Returns {section_a, section_b, section_c, total, rating, breakdown}.
    Data-driven factors are scored automatically; LLM-evaluated factors
    default to 0 and should be filled in by the LLM.
    """
    ticker = data.get("ticker", "")
    breakdown = {}

    # --- A. Growth & Innovation (max 70) ---
    a_score = 0

    rev_growth = data.get("revenueGrowthPct") or 0
    if rev_growth > 20:
        a_score += 10
        breakdown["revenue_growth_20pct"] = 10
    else:
        breakdown["revenue_growth_20pct"] = 0

    if data.get("grossMarginExpanding"):
        a_score += 10
        breakdown["expanding_gross_margins"] = 10
    else:
        breakdown["expanding_gross_margins"] = 0

    # LLM-evaluated (placeholder = 0)
    for llm_factor in ["tech_moat", "steep_s_curve", "wrights_law", "convergence", "disruption_driver"]:
        breakdown[llm_factor] = 0  # LLM fills these

    # --- B. Valuation & Fundamentals (max 40) ---
    b_score = 0

    peg = data.get("peg")
    if peg is not None:
        if peg < 1.0:
            b_score += 10
            breakdown["peg_score"] = 10
        elif peg <= 2.0:
            breakdown["peg_score"] = 0
        elif peg <= 2.5:
            b_score -= 10
            breakdown["peg_score"] = -10
        else:
            b_score -= 20
            breakdown["peg_score"] = -20
    else:
        breakdown["peg_score"] = 0

    profitable = data.get("profitable")
    cash_runway = data.get("cashRunwayMonths")
    if profitable or (cash_runway and cash_runway > 24):
        b_score += 10
        breakdown["cash_runway_or_profitable"] = 10
    else:
        breakdown["cash_runway_or_profitable"] = 0

    upside = data.get("upsidePct") or 0
    if upside > 15:
        b_score += 10
        breakdown["upside_gt_15pct"] = 10
    else:
        breakdown["upside_gt_15pct"] = 0

    breakdown["below_avg_multiples"] = 0  # LLM fills this

    # --- C. Momentum & ARK Conviction (max 15) ---
    c_score = 0

    ark_held = ticker in ark_holdings
    if ark_held:
        total_weight = sum(h["weight"] for h in ark_holdings.get(ticker, []))
        if total_weight >= 1.0:
            c_score += 5
            breakdown["ark_high_weight"] = 5
        else:
            c_score += 2
            breakdown["ark_high_weight"] = 2
    else:
        breakdown["ark_high_weight"] = 0

    breakdown["positive_news_catalyst"] = 0  # LLM fills this

    total = a_score + b_score + c_score

    if total >= 100:
        rating = "STRONG BUY"
    elif total >= 80:
        rating = "BUY"
    elif total >= 60:
        rating = "HOLD"
    else:
        rating = "SELL"

    return {
        "section_a": a_score,
        "section_b": b_score,
        "section_c": c_score,
        "total_data_only": total,
        "total": total,
        "rating_data_only": rating,
        "breakdown": breakdown,
        "ark_held": ark_held,
        "ark_etfs": [h["etf"] for h in ark_holdings.get(ticker, [])],
        "note": "LLM-evaluated factors (tech_moat, steep_s_curve, wrights_law, convergence, "
                "disruption_driver, below_avg_multiples, positive_news_catalyst) are set to 0. "
                "Add your assessment (0-10 each) to get the full score.",
    }


def format_report(data: dict, score: dict) -> str:
    """Format a human-readable report for one ticker."""
    t = data
    s = score
    lines = []

    lines.append(f"{'=' * 60}")
    lines.append(f"  {t['ticker']} — {t.get('name', '')}  |  Score: {s['total_data_only']}/125 (data-only)")
    lines.append(f"  Rating (data-only): {s['rating_data_only']}")
    lines.append(f"{'=' * 60}")

    lines.append("\n--- Financials ---")
    lines.append(f"  Price:           ${t.get('price', 'N/A')}")
    lines.append(f"  Market Cap:      ${t.get('marketCapB', 'N/A')}B")
    lines.append(f"  Sector:          {t.get('sector', 'N/A')} / {t.get('industry', 'N/A')}")
    lines.append(f"  Trailing P/E:    {t.get('trailingPE', 'N/A')}")
    lines.append(f"  Forward P/E:     {t.get('forwardPE', 'N/A')}")
    lines.append(f"  PEG:             {t.get('peg', 'N/A')}")
    lines.append(f"  Rev Growth:      {t.get('revenueGrowthPct', 'N/A')}%")
    lines.append(f"  Gross Margin:    {t.get('grossMarginPct', 'N/A')}%")
    lines.append(f"  Op Margin:       {t.get('opMarginPct', 'N/A')}%")
    lines.append(f"  Profitable:      {t.get('profitable', 'N/A')}")
    lines.append(f"  Cash:            ${_fmt_num(t.get('totalCash'))}")
    lines.append(f"  Debt:            ${_fmt_num(t.get('totalDebt'))}")
    lines.append(f"  Cash Runway:     {t.get('cashRunwayMonths', 'N/A')} months")
    lines.append(f"  Beta:            {t.get('beta', 'N/A')}")
    lines.append(f"  52w Range:       ${t.get('52wLow', '?')} — ${t.get('52wHigh', '?')}")

    lines.append("\n--- Analyst Consensus ---")
    lines.append(f"  Target (mean):   ${t.get('targetMean', 'N/A')}")
    lines.append(f"  Target Range:    ${t.get('targetLow', '?')} — ${t.get('targetHigh', '?')}")
    lines.append(f"  Upside:          {t.get('upsidePct', 'N/A')}%")
    lines.append(f"  # Analysts:      {t.get('numAnalysts', 'N/A')}")
    lines.append(f"  Recommendation:  {t.get('recommendation', 'N/A')}")

    lines.append("\n--- Score Breakdown (data-driven factors) ---")
    lines.append(f"  A. Growth & Innovation:     {s['section_a']}/70")
    for k, v in s["breakdown"].items():
        if k in ("revenue_growth_20pct", "expanding_gross_margins"):
            lines.append(f"     {k}: {v:+d}")
    lines.append(f"  B. Valuation & Fundamentals: {s['section_b']}/40")
    for k, v in s["breakdown"].items():
        if k in ("peg_score", "cash_runway_or_profitable", "upside_gt_15pct"):
            lines.append(f"     {k}: {v:+d}")
    lines.append(f"  C. Momentum & ARK:           {s['section_c']}/15")
    lines.append(f"     ark_high_weight: {s['breakdown'].get('ark_high_weight', 0):+d}")
    lines.append(f"  TOTAL (data-only):           {s['total_data_only']}/125")

    lines.append("\n--- ARK Holdings ---")
    if s["ark_held"]:
        for etf in s["ark_etfs"]:
            lines.append(f"  Held in: {etf} ({ARK_ETFS.get(etf, '')})")
    else:
        lines.append("  Not currently held in any ARK ETF")

    lines.append("\n--- LLM-Evaluated Factors (fill in 0-10 each) ---")
    for k in ("tech_moat", "steep_s_curve", "wrights_law", "convergence", "disruption_driver",
              "below_avg_multiples", "positive_news_catalyst"):
        lines.append(f"  {k}: [0-10] → currently {s['breakdown'].get(k, 0)}")

    lines.append("")
    return "\n".join(lines)


def _fmt_num(n) -> str:
    if n is None:
        return "N/A"
    if abs(n) >= 1e9:
        return f"{n / 1e9:.2f}B"
    if abs(n) >= 1e6:
        return f"{n / 1e6:.1f}M"
    return f"{n:,.0f}"


def generate_llm_prompt(tickers_data: list[dict], scores: list[dict]) -> str:
    """Generate an LLM analysis prompt with all collected data."""
    prompt_parts = []
    prompt_parts.append(
        "You are the ARKWOOD Financial Intelligence Unit. Below is real-time data for "
        f"{len(tickers_data)} stock(s). For EACH stock:\n"
        "\n"
        "1. Evaluate the LLM-scored factors (0-10 each): tech_moat, steep_s_curve, "
        "wrights_law, convergence, disruption_driver, below_avg_multiples, positive_news_catalyst\n"
        "2. Add them to the data-only score to get the FINAL Technology-Valuation Score (0-125)\n"
        "3. Provide the full 10-section analysis as specified in the ARKWOOD framework\n"
        "4. Start with the summary comparison table if multiple stocks\n"
        "\n"
    )

    for data, score in zip(tickers_data, scores):
        prompt_parts.append(format_report(data, score))

    prompt_parts.append(
        "\n--- INSTRUCTIONS ---\n"
        "For each stock, provide:\n"
        "1. Your LLM-evaluated factor scores (with 1-sentence justification each)\n"
        "2. Final combined score = data-only + LLM factors\n"
        "3. Final rating: STRONG BUY (100-125) / BUY (80-99) / HOLD (60-79) / SELL (<60)\n"
        "4. Full 10-section writeup (Company Overview → Ark-Fit Summary)\n"
        "5. 1-Year Bull/Base/Bear scenarios with price targets\n"
        "\nAlways present both bull and bear cases. Be data-driven, concise, information-dense."
    )

    return "\n".join(prompt_parts)


def main():
    parser = argparse.ArgumentParser(description="ARKWOOD FIU — Technology Investment Analyzer")
    parser.add_argument("tickers", nargs="*", help="Stock tickers to analyze")
    parser.add_argument("--format", choices=["text", "json", "prompt"], default="text",
                        help="Output format: text (human-readable), json (structured), prompt (LLM prompt)")
    parser.add_argument("--quick", action="store_true", help="Quick mode: data + score only, skip narrative")
    parser.add_argument("--config", default=None, help="Path to value_claw.json")
    parser.add_argument("--no-ark", action="store_true", help="Skip ARK holdings fetch")

    args = parser.parse_args()

    if not args.tickers:
        parser.print_help()
        sys.exit(1)

    _ensure_dir()

    tickers = [t.upper() for t in args.tickers]
    print(f"ARKWOOD FIU — Analyzing {len(tickers)} ticker(s): {', '.join(tickers)}")
    print(f"Timestamp: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    print()

    ark_holdings: dict = {}
    if not args.no_ark:
        print("Fetching ARK ETF holdings...")
        ark_holdings = fetch_ark_holdings()
        print(f"  Found {len(ark_holdings)} tickers across ARK ETFs")
    print()

    all_data = []
    all_scores = []

    for ticker in tickers:
        print(f"Fetching data for {ticker}...")
        data = fetch_stock_data(ticker)
        if "error" in data:
            print(f"  ERROR: {data['error']}")
            continue

        score = compute_score(data, ark_holdings)
        all_data.append(data)
        all_scores.append(score)

        if args.format == "text":
            print(format_report(data, score))

    if not all_data:
        print("No valid data fetched.")
        sys.exit(1)

    if args.format == "json":
        output = []
        for data, score in zip(all_data, all_scores):
            output.append({"data": data, "score": score})
        print(json.dumps(output, indent=2, default=str))

    elif args.format == "prompt":
        prompt = generate_llm_prompt(all_data, all_scores)
        print(prompt)

        prompt_path = os.path.join(DATA_DIR, "cache", "last_prompt.txt")
        with open(prompt_path, "w", encoding="utf-8") as f:
            f.write(prompt)
        print(f"\nPrompt saved to: {prompt_path}")

    cache_path = os.path.join(DATA_DIR, "cache", "last_analysis.json")
    with open(cache_path, "w", encoding="utf-8") as f:
        json.dump(
            {"timestamp": datetime.now(timezone.utc).isoformat(), "tickers": tickers,
             "data": all_data, "scores": all_scores},
            f, indent=2, default=str,
        )
    print(f"\nData cached to: {cache_path}")


if __name__ == "__main__":
    main()
