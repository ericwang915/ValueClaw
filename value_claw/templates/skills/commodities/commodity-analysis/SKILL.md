---
name: commodity-analysis
description: >
  In-depth commodity analysis with technicals, seasonal patterns, and supply-demand context.
  Use when: the user asks for commodity technical analysis, seasonal trends,
  volatility assessment, or wants an LLM-ready analysis prompt for a commodity.
dependencies: yfinance
metadata:
  emoji: "🔬"
---
# Commodity Analysis

## When to Use

- [ ] Deep-dive technical analysis on a specific commodity
- [ ] Assess seasonal patterns (average monthly returns over 5 years)
- [ ] Compute RSI, moving averages, and historical volatility
- [ ] Generate a data-rich prompt for LLM-assisted supply-demand analysis

## When NOT to Use

- [ ] Simple price checks (use commodity-tracker instead)
- [ ] Physical commodity trading or logistics
- [ ] Commodity options Greeks or spread trading

## Usage/Commands

```bash
python {skill_path}/commodity_analysis.py --commodity oil [options]
```

| Option | Description |
|--------|-------------|
| `--commodity NAME` | Commodity: oil, gold, silver, copper, natgas, corn, wheat, soybeans |
| `--format text\|json` | Output format (default: text) |

## Examples

Oil analysis:
```bash
python commodity_analysis.py --commodity oil
```

Gold analysis as JSON:
```bash
python commodity_analysis.py --commodity gold --format json
```

## Notes

- Seasonal patterns use 5 years of monthly data
- RSI and SMAs computed from daily closes
- Volatility is annualized from 20-day rolling window
