---
name: fund-flows
description: "ETF fund flow tracking — monitor capital flows into/out of major ETFs. Use when: user asks about ETF fund flows, sector rotation, capital movement, risk-on/risk-off signals, or money flow trends."
metadata:
  emoji: "💹"
---
# Fund Flows

Track capital flows into and out of major ETFs using volume and price analysis as a flow proxy.

## When to Use

- Monitor capital flows across asset classes (equity, bonds, gold, EM)
- Detect risk-on vs risk-off shifts
- Sector rotation signals
- Identify unusual flow activity in specific ETFs

## When NOT to Use

- Exact dollar fund flow data (this uses volume-price proxy)
- Individual stock volume analysis
- Mutual fund flows

## Usage

```bash
# Default major ETFs
python {skill_path}/fund_flows.py --all

# Specific ETFs
python {skill_path}/fund_flows.py --etfs SPY QQQ GLD TLT

# JSON output
python {skill_path}/fund_flows.py --all --format json
```

| Option | Description |
|--------|-------------|
| `--etfs SYM [SYM ...]` | Specific ETFs to analyze |
| `--all` | Analyze all default ETFs (SPY, QQQ, IWM, GLD, TLT, HYG, EEM, XLF, XLE, ARKK) |
| `--format text\|json` | Output format (default: text) |

## Methodology

Relative volume (current vs 20-day average) combined with price direction as a flow proxy:
- High relative volume + price up = **inflow signal**
- High relative volume + price down = **outflow signal**
- Normal volume = **neutral**

## Dependencies

```bash
pip install yfinance
```
