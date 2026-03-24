#!/usr/bin/env python3
"""Search and read SEC EDGAR filings. No API key required."""

import argparse
import json
import sys
import urllib.error
import urllib.request

HEADERS = {"User-Agent": "value_claw invest-research@valueclaw.ai"}
TICKER_MAP_URL = "https://www.sec.gov/files/company_tickers.json"
SUBMISSIONS_URL = "https://data.sec.gov/submissions/CIK{cik}.json"
XBRL_FACTS_URL = "https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json"

# Key GAAP concepts to extract from XBRL data
GAAP_METRICS = [
    ("Revenues", "Revenue"),
    ("RevenueFromContractWithCustomerExcludingAssessedTax", "Revenue (ASC 606)"),
    ("GrossProfit", "Gross Profit"),
    ("OperatingIncomeLoss", "Operating Income"),
    ("NetIncomeLoss", "Net Income"),
    ("EarningsPerShareBasic", "EPS Basic"),
    ("EarningsPerShareDiluted", "EPS Diluted"),
    ("Assets", "Total Assets"),
    ("Liabilities", "Total Liabilities"),
    ("StockholdersEquity", "Shareholders Equity"),
    ("CashAndCashEquivalentsAtCarryingValue", "Cash & Equivalents"),
    ("LongTermDebt", "Long-Term Debt"),
    ("NetCashProvidedByUsedInOperatingActivities", "Operating Cash Flow"),
    ("PaymentsToAcquirePropertyPlantAndEquipment", "CapEx"),
    ("CommonStockSharesOutstanding", "Shares Outstanding"),
]


def _fetch(url: str) -> dict:
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=20) as resp:
        return json.loads(resp.read().decode())


def get_cik(ticker: str) -> tuple:
    """Return (cik_padded, company_name) for a ticker."""
    data = _fetch(TICKER_MAP_URL)
    up = ticker.upper()
    for item in data.values():
        if item.get("ticker", "").upper() == up:
            cik = str(item["cik_str"]).zfill(10)
            return cik, item.get("title", ticker)
    raise ValueError(f"'{ticker}' not found in SEC EDGAR. (Only US-listed companies are supported.)")


def list_filings(cik: str, form_type: str = "10-K", count: int = 5) -> list:
    data = _fetch(SUBMISSIONS_URL.format(cik=cik))
    recent = data.get("filings", {}).get("recent", {})
    forms = recent.get("form", [])
    dates = recent.get("filingDate", [])
    accessions = recent.get("accessionNumber", [])
    primary_docs = recent.get("primaryDocument", [])
    descriptions = recent.get("primaryDocDescription", [])

    results = []
    form_filter = form_type.upper()
    for form, date, acc, doc, desc in zip(forms, dates, accessions, primary_docs, descriptions):
        if form_filter and form_filter not in form.upper():
            continue
        acc_clean = acc.replace("-", "")
        cik_int = int(cik)
        results.append({
            "form": form,
            "date": date,
            "accession": acc,
            "primary_doc": doc,
            "description": desc,
            "filing_url": f"https://www.sec.gov/Archives/edgar/data/{cik_int}/{acc_clean}/{doc}",
            "index_url": f"https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK={cik}&type={form}&dateb=&owner=include&count=1",
        })
        if len(results) >= count:
            break
    return results


def get_xbrl_financials(cik: str, num_periods: int = 8) -> dict:
    """Extract key financial metrics from EDGAR XBRL company-facts."""
    data = _fetch(XBRL_FACTS_URL.format(cik=cik))
    us_gaap = data.get("facts", {}).get("us-gaap", {})
    results = {}

    for gaap_key, label in GAAP_METRICS:
        concept = us_gaap.get(gaap_key, {})
        units = concept.get("units", {})
        values = units.get("USD", []) or units.get("shares", [])
        if not values:
            continue

        # Prefer 10-K (annual) filings; fall back to 10-Q
        annual = [v for v in values if v.get("form") in ("10-K", "10-K/A") and v.get("end")]
        quarterly = [v for v in values if v.get("form") in ("10-Q", "10-Q/A") and v.get("end")]
        source = annual if annual else quarterly
        if not source:
            continue

        # Sort by period end descending, deduplicate by end date
        source = sorted(source, key=lambda x: x["end"], reverse=True)
        seen, deduped = set(), []
        for v in source:
            if v["end"] not in seen:
                seen.add(v["end"])
                deduped.append(v)

        results[label] = [
            {"period": v["end"], "value": v.get("val"), "form": v.get("form")}
            for v in deduped[:num_periods]
        ]

    return results


def _fmt_val(val) -> str:
    if val is None:
        return "N/A"
    v = float(val)
    if abs(v) >= 1e12:
        return f"{v / 1e12:.3f}T"
    if abs(v) >= 1e9:
        return f"{v / 1e9:.3f}B"
    if abs(v) >= 1e6:
        return f"{v / 1e6:.2f}M"
    if abs(v) < 1000:
        return f"{v:.2f}"
    return f"{v:,.0f}"


def format_filings(filings: list, company: str, symbol: str) -> str:
    lines = [
        f"{'═' * 60}",
        f"  SEC EDGAR Filings: {company} ({symbol.upper()})",
        f"{'═' * 60}",
    ]
    for f in filings:
        lines.append(f"\n  [{f['form']}]  {f['date']}")
        if f.get("description"):
            lines.append(f"  {f['description']}")
        lines.append(f"  URL: {f['filing_url']}")
    if not filings:
        lines.append("  (No matching filings found)")
    return "\n".join(lines)


def format_financials(data: dict, company: str, symbol: str) -> str:
    lines = [
        f"{'═' * 60}",
        f"  EDGAR XBRL Financials: {company} ({symbol.upper()})",
        f"{'─' * 60}",
        f"  (Source: SEC EDGAR structured data — official filings)",
        f"{'═' * 60}",
    ]
    for label, records in data.items():
        if not records:
            continue
        lines.append(f"\n── {label} ─────────────────────────────────")
        header = f"  {'Period':<14} {'Value':>14}  {'Form':<8}"
        lines.append(header)
        lines.append(f"  {'─' * 14} {'─' * 14}  {'─' * 8}")
        for r in records[:8]:
            val_str = _fmt_val(r["value"])
            form_str = r.get("form", "")
            lines.append(f"  {r['period']:<14} {val_str:>14}  {form_str:<8}")
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="SEC EDGAR filing search and financial data.")
    parser.add_argument("ticker", help="US stock ticker (e.g. AAPL, MSFT, TSLA)")
    parser.add_argument("--type", default="10-K",
                        help="Filing type: 10-K (annual), 10-Q (quarterly), 8-K (current events), all")
    parser.add_argument("--count", type=int, default=5, help="Max number of filings to list")
    parser.add_argument("--financials", action="store_true",
                        help="Fetch structured XBRL financial data instead of filing list")
    parser.add_argument("--periods", type=int, default=8,
                        help="Number of historical periods for --financials (default: 8)")
    parser.add_argument("--format", choices=["text", "json"], default="text")
    args = parser.parse_args()

    # Look up CIK
    try:
        cik, company = get_cik(args.ticker)
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)
    except Exception as exc:
        print(f"EDGAR lookup error: {exc}", file=sys.stderr)
        sys.exit(1)

    print(f"[EDGAR] {company}  |  CIK: {int(cik)}", file=sys.stderr)

    if args.financials:
        try:
            fin = get_xbrl_financials(cik, num_periods=args.periods)
        except urllib.error.HTTPError as exc:
            print(f"Error fetching XBRL data: HTTP {exc.code} — {exc.reason}", file=sys.stderr)
            sys.exit(1)
        except Exception as exc:
            print(f"Error fetching XBRL data: {exc}", file=sys.stderr)
            sys.exit(1)

        if args.format == "json":
            print(json.dumps({"ticker": args.ticker, "company": company, "cik": int(cik),
                               "financials": fin}, indent=2))
        else:
            print(format_financials(fin, company, args.ticker))
    else:
        form_filter = "" if args.type.lower() == "all" else args.type
        try:
            filings = list_filings(cik, form_type=form_filter, count=args.count)
        except Exception as exc:
            print(f"Error listing filings: {exc}", file=sys.stderr)
            sys.exit(1)

        if args.format == "json":
            print(json.dumps({"ticker": args.ticker, "company": company,
                               "cik": int(cik), "filings": filings}, indent=2))
        else:
            print(format_filings(filings, company, args.ticker))


if __name__ == "__main__":
    main()
