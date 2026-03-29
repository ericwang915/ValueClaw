---
name: dividend-tracker
description: >
  Dividend analysis — yield, growth rate, payout ratio, ex-dividend calendar,
  dividend aristocrats screening. Use when: user asks about dividend stocks,
  yield analysis, payout ratios, or dividend aristocrats.
metadata:
  emoji: "D"
---

# Dividend Tracker

## When to Use

- Analyze dividend yield, growth rate, and payout ratio for stocks
- Check ex-dividend dates and upcoming payments
- Screen for dividend aristocrats (25+ years of consecutive increases)
- Compare dividend metrics across multiple tickers

## When NOT to Use

- Growth stock analysis with no dividends
- Detailed fundamental/technical analysis (use stock-analysis or technical-analyst)

## Usage

```bash
# Analyze dividend metrics for specific tickers
python {skill_path}/dividend_tracker.py --tickers JNJ KO PG VZ T ABBV

# Filter for dividend aristocrats only
python {skill_path}/dividend_tracker.py --tickers JNJ KO PG --aristocrats

# JSON output
python {skill_path}/dividend_tracker.py --tickers JNJ KO --format json
```

| Option | Description |
|--------|-------------|
| `--tickers T1 T2 ...` | Tickers to analyze (required) |
| `--aristocrats` | Filter for 25+ years of consecutive dividend increases |
| `--format text\|json` | Output format (default: text) |

## Dependencies

```bash
pip install yfinance
```

## Notes

- Uses yfinance for dividend data (free, no API key)
- 5-year CAGR computed from historical dividend payments
- Aristocrats list is a curated set of ~30 well-known names
