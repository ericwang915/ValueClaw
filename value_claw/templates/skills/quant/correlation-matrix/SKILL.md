---
name: correlation-matrix
description: >
  Asset correlation matrix — compute and visualize return correlations between
  any set of tickers. Use when: the user asks about asset correlations, portfolio
  diversification, or wants a correlation heatmap.
metadata:
  emoji: "🔗"
---
# Correlation Matrix

## When to Use

- [ ] Compute pairwise correlations between assets
- [ ] Assess portfolio diversification
- [ ] Identify highly correlated or uncorrelated asset pairs
- [ ] Generate a correlation heatmap chart

## When NOT to Use

- [ ] Causal analysis (correlation is not causation)
- [ ] Intraday or tick-level correlation
- [ ] Cointegration or pairs-trading analysis

## Setup

Install dependencies: `pip install yfinance numpy`

For heatmap charts: `pip install matplotlib` (optional, only with `--chart`)

## Usage/Commands

```bash
python {skill_path}/correlation_matrix.py --tickers AAPL MSFT GOOGL SPY GLD TLT [options]
```

| Option | Description |
|--------|-------------|
| `--tickers SYM [SYM ...]` | Tickers to include (at least 2) |
| `--period 1y` | Lookback period (default: `1y`) |
| `--chart` | Generate a heatmap PNG (requires matplotlib) |
| `--format text\|json` | Output format (default: `text`) |

## Notes

- Uses daily return correlations (Pearson)
- Period options: 1mo, 3mo, 6mo, 1y, 2y, 5y
- Heatmap saved to `~/.value_claw/correlation_matrix/heatmap.png`
- Output cached to `~/.value_claw/correlation_matrix/`
