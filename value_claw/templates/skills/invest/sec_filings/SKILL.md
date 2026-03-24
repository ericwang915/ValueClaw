---
name: sec_filings
description: "Search and read SEC EDGAR filings for US public companies: list 10-K/10-Q/8-K filings with direct links, and fetch structured XBRL financial data (income statement, balance sheet, cash flow) from EDGAR's official API. Use when: user wants to read annual/quarterly reports, check historical financials from official filings, find 8-K announcements, or do deep fundamental research on US-listed companies. NOT for: non-US companies (use akshare_data or web_search instead)."
metadata:
  emoji: "📋"
---

# SEC Filings Skill

Access SEC EDGAR for official filings and structured financial data. No API key required.

## When to Use

✅ **USE this skill when:**
- "Show me Apple's 10-K filings"
- "What did Tesla report in their last 10-Q?"
- "Find recent 8-K announcements for NVDA"
- "Get historical revenue and net income from SEC filings"
- "I want to read the annual report for Microsoft"

## Usage/Commands

```bash
# List recent 10-K filings (default)
python {skill_path}/sec_filings.py AAPL

# Specify filing type
python {skill_path}/sec_filings.py AAPL --type 10-Q    # Quarterly reports
python {skill_path}/sec_filings.py AAPL --type 8-K     # Current reports / announcements
python {skill_path}/sec_filings.py AAPL --type DEF\ 14A  # Proxy statements

# More results
python {skill_path}/sec_filings.py AAPL --type 10-K --count 10

# Fetch structured XBRL financials (income, balance sheet, cash flow history)
python {skill_path}/sec_filings.py AAPL --financials

# JSON output
python {skill_path}/sec_filings.py AAPL --financials --format json
```

## --financials Mode

Fetches key metrics from EDGAR's XBRL structured data API with multi-year history:

| Metric | GAAP Concept |
|--------|-------------|
| Revenue | Revenues / RevenueFromContract... |
| Gross Profit | GrossProfit |
| Operating Income | OperatingIncomeLoss |
| Net Income | NetIncomeLoss |
| EPS Basic/Diluted | EarningsPerShare... |
| Total Assets | Assets |
| Total Liabilities | Liabilities |
| Shareholders' Equity | StockholdersEquity |
| Cash & Equivalents | CashAndCashEquivalents... |
| Long-Term Debt | LongTermDebt |
| Operating Cash Flow | NetCashProvided... |
| CapEx | PaymentsToAcquire... |

## Filing Links

After listing filings, the agent can use `web/summarize` skill or `web_search` to read the content of a specific filing URL.

## Notes

- Data from SEC EDGAR — official, authoritative, free
- Only covers SEC-registered (US-listed) companies
- XBRL data is most complete for companies filing since ~2010
- For Chinese company data: use `akshare_data` skill
