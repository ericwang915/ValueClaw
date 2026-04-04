---
name: short-interest
description: "Short interest and short squeeze potential analysis. Use when: user asks about short interest, short squeeze candidates, days to cover, or bearish positioning on a stock."
metadata:
  emoji: "📉"
---
# Short Interest

Analyze short interest data and identify potential short squeeze candidates.

## When to Use

- User asks about short interest levels for stocks
- Screening for short squeeze candidates
- Checking days-to-cover or shares shorted
- Analyzing bearish positioning

## When NOT to Use

- Options flow analysis (different data source)
- General stock screening without short interest focus

## Usage

```bash
# Analyze short interest for tickers
python {skill_path}/short_interest.py --tickers GME AMC TSLA

# JSON output
python {skill_path}/short_interest.py --tickers BBBY GME --format json
```

| Option | Description |
|--------|-------------|
| `--tickers SYM [SYM ...]` | Tickers to analyze (required) |
| `--format text\|json` | Output format (default: text) |

## Flags

- **High Short Interest**: >15% of float shorted
- **High Days-to-Cover**: Short ratio >5 days
- **Squeeze Risk**: Both conditions met simultaneously

## Dependencies

```bash
pip install yfinance
```
