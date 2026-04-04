---
name: lynch-garp
description: "Peter Lynch GARP (Growth At Reasonable Price) framework — PEG ratio screening, stock classification, ten-bagger potential. Use when: user asks for GARP analysis, PEG screening, Lynch-style stock classification, or ten-bagger candidates."
metadata:
  emoji: "🌱"
---
# Lynch GARP Analysis

Peter Lynch-inspired Growth At Reasonable Price framework: stock classification, PEG ratio screening, and ten-bagger potential identification.

## When to Use

- GARP stock screening and analysis
- Classify stocks into Lynch categories
- PEG ratio analysis
- Screen for ten-bagger potential (small/mid cap + high growth + low PEG)

## When NOT to Use

- Deep value / distressed investing
- Macro or top-down analysis
- Index/ETF analysis

## Usage

```bash
# Analyze tickers
python {skill_path}/lynch_analyze.py --tickers PLTR SHOP CRWD

# JSON output
python {skill_path}/lynch_analyze.py --tickers PLTR --format json
```

| Option | Description |
|--------|-------------|
| `--tickers SYM [SYM ...]` | Tickers to analyze (required) |
| `--format text\|json` | Output format (default: text) |

## Lynch Stock Categories

| Category | Description |
|----------|-------------|
| Slow Grower | Large, mature, low growth (<5%), often pays dividends |
| Stalwart | Large cap, moderate growth (5-15%), steady performers |
| Fast Grower | Small/mid cap, high growth (>15%), the ten-bagger source |
| Cyclical | Earnings tied to economic cycles |
| Turnaround | Depressed companies with recovery potential |
| Asset Play | Hidden asset value not reflected in price |

## Ten-Bagger Screen

Flags stocks with: small/mid cap + high growth + PEG < 1.5 + low institutional ownership.

## Dependencies

```bash
pip install yfinance
```
