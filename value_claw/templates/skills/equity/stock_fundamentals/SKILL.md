---
name: stock_fundamentals
description: "Deep fundamental analysis + earnings tracker for stocks: valuation (P/E, P/B, EV/EBITDA, PEG), profitability (margins, ROE, ROA), growth (revenue/earnings YoY), balance sheet (debt, cash, FCF), analyst price targets, EPS history (beat/miss rate), next earnings date, quarterly revenue & net income. Use when: user asks about a company's financials, valuation ratios, profitability, debt, financial health, analyst consensus, earnings results, EPS surprise, or upcoming earnings date. Works for US stocks, HK stocks (0700.HK), and A-shares (600519.SS)."
dependencies: yfinance
metadata:
  emoji: "📊"
---

# Stock Fundamentals Skill

Comprehensive fundamental analysis + earnings tracker powered by Yahoo Finance (yfinance).

## When to Use

✅ **USE this skill when:**
- "Is AAPL overvalued?"  /  "茅台的市盈率是多少？"
- "What's Tesla's P/E / P/B / EV/EBITDA?"
- "Show Apple's profit margins / ROE / ROA"
- "How much debt does Amazon have?"
- "What's the analyst price target for NVDA?"
- "Compare FAANG valuations"
- "When does AAPL report earnings next?"
- "Did NVDA beat earnings last quarter?"
- "Show me TSLA's EPS history and beat rate"

## Usage/Commands

```bash
# Full fundamental report
python {skill_path}/fundamentals.py SYMBOL

# Fundamentals + earnings history + next earnings date
python {skill_path}/fundamentals.py AAPL --earnings

# Multiple stocks (comparison)
python {skill_path}/fundamentals.py AAPL MSFT GOOGL

# JSON output for programmatic use
python {skill_path}/fundamentals.py AAPL --format json
python {skill_path}/fundamentals.py AAPL --earnings --format json
```

## Ticker Format

| Market | Example |
|--------|---------|
| US stocks | `AAPL`, `TSLA`, `NVDA` |
| HK stocks | `0700.HK`, `9988.HK` |
| A-shares (Shanghai) | `600519.SS` |
| A-shares (Shenzhen) | `000858.SZ` |
| Crypto | `BTC-USD` |

## Output Sections

**Fundamentals (default):**
- **Valuation**: Market Cap, EV, P/E (trailing & forward), PEG, P/B, P/S, EV/EBITDA
- **Income (TTM)**: Revenue, Gross Profit, EBITDA, EPS
- **Profitability**: Gross/Operating/Net margins, ROE, ROA
- **Growth**: Revenue growth YoY, Earnings growth YoY/QoQ
- **Balance Sheet**: Cash, Debt, D/E ratio, Current ratio, FCF
- **Analyst Consensus**: Rating, price targets (mean/high/low), upside %
- **Dividends**: Yield, rate, payout ratio (if applicable)

**Earnings (--earnings flag):**
- **Next Earnings Date**: Upcoming report date + EPS/revenue estimate
- **EPS History**: Last 8 quarters — estimate vs actual, surprise %, beat/miss indicator
- **Beat Rate**: % of quarters where EPS beat estimates
- **Quarterly Revenue & Net Income**: Last 6 quarters trend

## Balance Sheet & Cash Flow Deep Dive (Enhanced)

When performing in-depth fundamental analysis, go beyond ratios — analyze the **trajectory**:

### Balance Sheet Health Check
Compare last 4 quarters to spot trends:
- **Cash vs Debt trajectory**: Is net cash position improving or deteriorating?
- **Current Ratio trend**: >1.5 healthy, <1.0 warning
- **Goodwill / Total Assets**: >30% = acquisition-driven growth risk
- **Share count change**: Dilution (bad) vs buybacks (positive signal)

### Cash Flow Quality Assessment
- **FCF Margin**: FCF / Revenue — sustainable >15% for tech, >8% for industrial
- **OCF vs Net Income**: OCF should be ≥ Net Income; gap = earnings quality concern
- **CapEx Intensity**: CapEx / Revenue — high = heavy reinvestment needs
- **FCF Yield**: FCF / Market Cap — compare vs treasury yield for value signal

### Financial Strength Score
Synthesize into a single score:
```
Financial Strength: 8/10
✅ Growing FCF (+18% YoY)
✅ Net cash position ($24B cash vs $12B debt)
✅ Share buyback ($15B trailing 12M)
⚠️ Goodwill at 22% of assets (manageable)
❌ Current ratio declining (1.8 → 1.4 over 4Q)
```

## Notes

- Data from Yahoo Finance — typical 15-min delay for US markets
- A-share data may be incomplete via yfinance; use `akshare_data` skill for richer A-share fundamentals
- Not financial advice — always verify with official sources
