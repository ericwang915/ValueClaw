#!/usr/bin/env python3
"""Comprehensive fundamental analysis for stocks via Yahoo Finance."""

import argparse
import json
import math
import sys

try:
    import yfinance as yf
except ImportError:
    print("Error: yfinance not installed. Run: pip install yfinance", file=sys.stderr)
    sys.exit(1)


def _is_nan(v):
    try:
        return v is None or math.isnan(float(v))
    except (TypeError, ValueError):
        return v is None


def fmt_pct(v):
    return "N/A" if _is_nan(v) else f"{v * 100:.1f}%"


def fmt_num(v):
    if _is_nan(v):
        return "N/A"
    v = float(v)
    if abs(v) >= 1e12:
        return f"{v / 1e12:.2f}T"
    if abs(v) >= 1e9:
        return f"{v / 1e9:.2f}B"
    if abs(v) >= 1e6:
        return f"{v / 1e6:.2f}M"
    return f"{v:,.0f}"


def fmt_f(v, d=2):
    return "N/A" if _is_nan(v) else f"{float(v):.{d}f}"


def get_fundamentals(symbol: str) -> dict:
    t = yf.Ticker(symbol)
    i = t.info
    return {
        "symbol": symbol.upper(),
        "name": i.get("shortName") or i.get("longName", symbol),
        "sector": i.get("sector", "N/A"),
        "industry": i.get("industry", "N/A"),
        "exchange": i.get("exchange", "N/A"),
        "currency": i.get("currency", "USD"),
        "description": (i.get("longBusinessSummary") or "")[:280],
        # Price
        "currentPrice": i.get("currentPrice") or i.get("regularMarketPrice"),
        "fiftyTwoWeekHigh": i.get("fiftyTwoWeekHigh"),
        "fiftyTwoWeekLow": i.get("fiftyTwoWeekLow"),
        # Valuation
        "marketCap": i.get("marketCap"),
        "enterpriseValue": i.get("enterpriseValue"),
        "trailingPE": i.get("trailingPE"),
        "forwardPE": i.get("forwardPE"),
        "pegRatio": i.get("pegRatio"),
        "priceToBook": i.get("priceToBook"),
        "priceToSales": i.get("priceToSalesTrailing12Months"),
        "evToEbitda": i.get("enterpriseToEbitda"),
        "evToRevenue": i.get("enterpriseToRevenue"),
        # Income TTM
        "totalRevenue": i.get("totalRevenue"),
        "grossProfits": i.get("grossProfits"),
        "ebitda": i.get("ebitda"),
        "trailingEps": i.get("trailingEps"),
        "forwardEps": i.get("forwardEps"),
        # Margins & Returns
        "grossMargins": i.get("grossMargins"),
        "operatingMargins": i.get("operatingMargins"),
        "profitMargins": i.get("profitMargins"),
        "ebitdaMargins": i.get("ebitdaMargins"),
        "returnOnEquity": i.get("returnOnEquity"),
        "returnOnAssets": i.get("returnOnAssets"),
        # Growth
        "revenueGrowth": i.get("revenueGrowth"),
        "earningsGrowth": i.get("earningsGrowth"),
        "earningsQuarterlyGrowth": i.get("earningsQuarterlyGrowth"),
        # Balance sheet
        "totalCash": i.get("totalCash"),
        "totalCashPerShare": i.get("totalCashPerShare"),
        "totalDebt": i.get("totalDebt"),
        "debtToEquity": i.get("debtToEquity"),
        "currentRatio": i.get("currentRatio"),
        "quickRatio": i.get("quickRatio"),
        "freeCashflow": i.get("freeCashflow"),
        "operatingCashflow": i.get("operatingCashflow"),
        # Dividends
        "dividendYield": i.get("dividendYield"),
        "dividendRate": i.get("dividendRate"),
        "payoutRatio": i.get("payoutRatio"),
        # Analyst
        "targetMeanPrice": i.get("targetMeanPrice"),
        "targetHighPrice": i.get("targetHighPrice"),
        "targetLowPrice": i.get("targetLowPrice"),
        "recommendationKey": i.get("recommendationKey"),
        "recommendationMean": i.get("recommendationMean"),
        "numberOfAnalystOpinions": i.get("numberOfAnalystOpinions"),
    }


def format_report(d: dict) -> str:
    price = d.get("currentPrice")
    hi52 = d.get("fiftyTwoWeekHigh")
    lo52 = d.get("fiftyTwoWeekLow")
    price_range = ""
    if not _is_nan(price) and not _is_nan(hi52) and not _is_nan(lo52):
        pct_from_hi = (price / hi52 - 1) * 100
        price_range = f"  52W Range: {fmt_f(lo52)} — {fmt_f(hi52)}  ({pct_from_hi:+.1f}% from 52W high)"

    lines = [
        f"{'═' * 54}",
        f"  {d['name']} ({d['symbol']})  [{d['exchange']}]",
        f"  {d['sector']}  ›  {d['industry']}",
        f"{'═' * 54}",
    ]
    if not _is_nan(price):
        lines.append(f"  Current Price: {fmt_f(price)} {d.get('currency', '')}")
    if price_range:
        lines.append(price_range)

    lines += [
        "",
        "── Valuation ─────────────────────────────────────",
        f"  Market Cap:       {fmt_num(d.get('marketCap'))}",
        f"  Enterprise Value: {fmt_num(d.get('enterpriseValue'))}",
        f"  P/E  (Trailing):  {fmt_f(d.get('trailingPE'))}",
        f"  P/E  (Forward):   {fmt_f(d.get('forwardPE'))}",
        f"  PEG Ratio:        {fmt_f(d.get('pegRatio'))}",
        f"  P/B:              {fmt_f(d.get('priceToBook'))}",
        f"  P/S (TTM):        {fmt_f(d.get('priceToSales'))}",
        f"  EV/EBITDA:        {fmt_f(d.get('evToEbitda'))}",
        f"  EV/Revenue:       {fmt_f(d.get('evToRevenue'))}",
        "",
        "── Income Statement (TTM) ────────────────────────",
        f"  Revenue:          {fmt_num(d.get('totalRevenue'))}",
        f"  Gross Profit:     {fmt_num(d.get('grossProfits'))}",
        f"  EBITDA:           {fmt_num(d.get('ebitda'))}",
        f"  EPS (Trailing):   {fmt_f(d.get('trailingEps'))}",
        f"  EPS (Forward):    {fmt_f(d.get('forwardEps'))}",
        "",
        "── Profitability & Returns ───────────────────────",
        f"  Gross Margin:     {fmt_pct(d.get('grossMargins'))}",
        f"  Operating Margin: {fmt_pct(d.get('operatingMargins'))}",
        f"  Net Margin:       {fmt_pct(d.get('profitMargins'))}",
        f"  EBITDA Margin:    {fmt_pct(d.get('ebitdaMargins'))}",
        f"  ROE:              {fmt_pct(d.get('returnOnEquity'))}",
        f"  ROA:              {fmt_pct(d.get('returnOnAssets'))}",
        "",
        "── Growth (YoY) ──────────────────────────────────",
        f"  Revenue Growth:          {fmt_pct(d.get('revenueGrowth'))}",
        f"  Earnings Growth:         {fmt_pct(d.get('earningsGrowth'))}",
        f"  Earnings Growth (QoQ):   {fmt_pct(d.get('earningsQuarterlyGrowth'))}",
        "",
        "── Balance Sheet ─────────────────────────────────",
        f"  Cash:             {fmt_num(d.get('totalCash'))}  ({fmt_f(d.get('totalCashPerShare'))}/share)",
        f"  Total Debt:       {fmt_num(d.get('totalDebt'))}",
        f"  Debt / Equity:    {fmt_f(d.get('debtToEquity'))}",
        f"  Current Ratio:    {fmt_f(d.get('currentRatio'))}",
        f"  Quick Ratio:      {fmt_f(d.get('quickRatio'))}",
        f"  Free Cash Flow:   {fmt_num(d.get('freeCashflow'))}",
        f"  Operating CF:     {fmt_num(d.get('operatingCashflow'))}",
    ]

    # Dividends (only if paying)
    if not _is_nan(d.get("dividendYield")):
        lines += [
            "",
            "── Dividends ─────────────────────────────────────",
            f"  Yield:          {fmt_pct(d.get('dividendYield'))}",
            f"  Rate:           {fmt_f(d.get('dividendRate'))}",
            f"  Payout Ratio:   {fmt_pct(d.get('payoutRatio'))}",
        ]

    # Analyst consensus
    rec = (d.get("recommendationKey") or "N/A").upper()
    mean_target = d.get("targetMeanPrice")
    upside_str = ""
    if not _is_nan(mean_target) and not _is_nan(price) and float(price) > 0:
        upside = (float(mean_target) / float(price) - 1) * 100
        upside_str = f"  Upside to Mean: {upside:+.1f}%"

    lines += [
        "",
        "── Analyst Consensus ─────────────────────────────",
        f"  Rating:    {rec}  (score: {fmt_f(d.get('recommendationMean'))}/5,"
        f"  {d.get('numberOfAnalystOpinions') or 0} analysts)",
        f"  Target:    Mean={fmt_f(mean_target)}  "
        f"High={fmt_f(d.get('targetHighPrice'))}  "
        f"Low={fmt_f(d.get('targetLowPrice'))}",
    ]
    if upside_str:
        lines.append(upside_str)

    if d.get("description"):
        lines += [
            "",
            "── Business ──────────────────────────────────────",
            f"  {d['description']}{'...' if len(d['description']) >= 280 else ''}",
        ]

    return "\n".join(lines)


def get_earnings_data(symbol: str) -> dict:
    t = yf.Ticker(symbol)
    info = t.info
    result = {
        "symbol": symbol.upper(),
        "name": info.get("shortName") or info.get("longName", symbol),
        "currency": info.get("currency", "USD"),
        "currentPrice": info.get("currentPrice") or info.get("regularMarketPrice"),
    }

    try:
        cal = t.calendar
        if cal is not None:
            if isinstance(cal, dict):
                dates = cal.get("Earnings Date")
                result["next_earnings_date"] = str(dates) if dates else "N/A"
                result["eps_estimate"] = cal.get("EPS Estimate")
                result["revenue_estimate"] = cal.get("Revenue Estimate")
            elif hasattr(cal, "iloc"):
                d = cal.to_dict()
                result["next_earnings_date"] = str(d)
    except Exception:
        result["next_earnings_date"] = "N/A"

    try:
        hist = t.earnings_history
        if hist is not None and not hist.empty:
            records = []
            for idx, row in hist.tail(8).iterrows():
                est = row.get("epsEstimate")
                act = row.get("epsActual")
                diff = row.get("epsDifference")
                pct = row.get("surprisePercent")
                beat = None
                if not _is_nan(diff):
                    beat = float(diff) >= 0
                records.append({
                    "date": str(idx)[:10],
                    "eps_estimate": None if _is_nan(est) else float(est),
                    "eps_actual": None if _is_nan(act) else float(act),
                    "eps_surprise": None if _is_nan(diff) else float(diff),
                    "surprise_pct": None if _is_nan(pct) else float(pct),
                    "beat": beat,
                })
            result["earnings_history"] = records
    except Exception:
        result["earnings_history"] = []

    try:
        qf = t.quarterly_financials
        if qf is not None and not qf.empty:
            q_data = {}
            for metric in ["Total Revenue", "Net Income", "Gross Profit"]:
                if metric in qf.index:
                    q_data[metric] = {
                        str(col)[:10]: (None if _is_nan(val) else float(val))
                        for col, val in qf.loc[metric].items()
                    }
            result["quarterly_financials"] = q_data
    except Exception:
        result["quarterly_financials"] = {}

    result["analyst"] = {
        "recommendation": info.get("recommendationKey"),
        "recommendation_mean": info.get("recommendationMean"),
        "num_analysts": info.get("numberOfAnalystOpinions"),
        "target_mean": info.get("targetMeanPrice"),
        "target_high": info.get("targetHighPrice"),
        "target_low": info.get("targetLowPrice"),
    }
    return result


def format_earnings_report(d: dict) -> str:
    lines = [
        f"{'─' * 56}",
        f"  Earnings: {d['name']} ({d['symbol']})",
        f"{'─' * 56}",
        f"  Next Earnings:  {d.get('next_earnings_date', 'N/A')}",
    ]
    if not _is_nan(d.get("eps_estimate")):
        lines.append(f"  EPS Estimate:   {fmt_f(d.get('eps_estimate'))}")
    if not _is_nan(d.get("revenue_estimate")):
        lines.append(f"  Revenue Est:    {fmt_num(d.get('revenue_estimate'))}")

    hist = d.get("earnings_history", [])
    if hist:
        lines += ["", "── EPS History (Last 8 Quarters) ─────────────────────"]
        lines.append(f"  {'Date':<13} {'Est':>7} {'Actual':>8} {'Surprise':>9} {'%':>7}  Result")
        lines.append(f"  {'─' * 13} {'─' * 7} {'─' * 8} {'─' * 9} {'─' * 7}  {'─' * 6}")
        for r in reversed(hist):
            beat_str = "✅ BEAT" if r.get("beat") is True else ("❌ MISS" if r.get("beat") is False else "")
            pct = r.get("surprise_pct")
            pct_str = f"{pct:+.1f}%" if pct is not None else "N/A"
            lines.append(
                f"  {r['date']:<13} "
                f"{fmt_f(r.get('eps_estimate')):>7} "
                f"{fmt_f(r.get('eps_actual')):>8} "
                f"{fmt_f(r.get('eps_surprise')):>9} "
                f"{pct_str:>7}  {beat_str}"
            )
        beats = [r for r in hist if r.get("beat") is True]
        misses = [r for r in hist if r.get("beat") is False]
        if beats or misses:
            total = len(beats) + len(misses)
            rate = len(beats) / total * 100
            lines.append(f"\n  Beat Rate: {len(beats)}/{total} ({rate:.0f}%)")

    qf = d.get("quarterly_financials", {})
    rev = qf.get("Total Revenue", {})
    ni = qf.get("Net Income", {})
    if rev or ni:
        all_quarters = sorted(set(list(rev.keys()) + list(ni.keys())), reverse=True)[:6]
        lines += ["", "── Quarterly Revenue & Net Income ─────────────────────"]
        lines.append(f"  {'Quarter':<13} {'Revenue':>12} {'Net Income':>12}")
        lines.append(f"  {'─' * 13} {'─' * 12} {'─' * 12}")
        for q in all_quarters:
            lines.append(
                f"  {q:<13} "
                f"{fmt_num(rev.get(q)):>12} "
                f"{fmt_num(ni.get(q)):>12}"
            )

    a = d.get("analyst", {})
    if a:
        rec = (a.get("recommendation") or "N/A").upper()
        cur_price = d.get("currentPrice")
        mean_tgt = a.get("target_mean")
        upside_str = ""
        if not _is_nan(cur_price) and not _is_nan(mean_tgt) and float(cur_price) > 0:
            upside = (float(mean_tgt) / float(cur_price) - 1) * 100
            upside_str = f"  ({upside:+.1f}% upside)"
        lines += [
            "",
            "── Analyst Consensus ──────────────────────────────────",
            f"  Rating:   {rec}  (score: {fmt_f(a.get('recommendation_mean'))}/5,"
            f"  {a.get('num_analysts') or 0} analysts)",
            f"  Target:   Mean={fmt_f(mean_tgt)}  "
            f"High={fmt_f(a.get('target_high'))}  "
            f"Low={fmt_f(a.get('target_low'))}",
        ]
        if upside_str:
            lines.append(upside_str)

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Stock fundamental analysis.")
    parser.add_argument("symbols", nargs="+", help="Ticker symbols")
    parser.add_argument("--format", choices=["text", "json"], default="text")
    parser.add_argument("--earnings", action="store_true", help="Include earnings history and next earnings date")
    args = parser.parse_args()

    results = []
    for sym in args.symbols:
        try:
            data = get_fundamentals(sym.strip())
            if args.earnings:
                data["_earnings"] = get_earnings_data(sym.strip())
            results.append(data)
        except Exception as exc:
            results.append({"symbol": sym, "error": str(exc)})

    if args.format == "json":
        print(json.dumps(results, indent=2, default=str))
        return

    for data in results:
        if "error" in data:
            print(f"{data['symbol']}: Error — {data['error']}")
        else:
            print(format_report(data))
            if args.earnings and "_earnings" in data:
                print()
                print(format_earnings_report(data["_earnings"]))
        print()


if __name__ == "__main__":
    main()
