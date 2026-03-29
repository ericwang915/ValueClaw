---
name: stock-screener
description: >
  Multi-criteria stock screener — filter by P/E, revenue growth, margins, market
  cap, and more from a curated universe. Use when: the user wants to screen
  stocks, find undervalued companies, or filter by fundamental criteria.
metadata:
  emoji: "🔍"
---
# Stock Screener

## When to Use

- [ ] Filter stocks by P/E ratio, growth rate, or margins
- [ ] Find stocks matching multiple fundamental criteria
- [ ] Screen a universe of large-cap stocks by custom thresholds
- [ ] Rank stocks by a composite score

## When NOT to Use

- [ ] Screening thousands of small-cap or micro-cap stocks (universe is top ~50)
- [ ] Technical analysis or chart-based screening
- [ ] Real-time intraday screening

## Setup

Install dependency: `pip install yfinance`

## Usage/Commands

```bash
python {skill_path}/stock_screener.py [options]
```

| Option | Description |
|--------|-------------|
| `--max-pe N` | Maximum trailing P/E (default: no limit) |
| `--min-growth N` | Minimum revenue growth % (default: 0) |
| `--min-margin N` | Minimum operating margin % (default: 0) |
| `--min-cap XB` | Minimum market cap, e.g. `10B` (default: none) |
| `--max-cap XB` | Maximum market cap, e.g. `500B` (default: none) |
| `--sort-by score\|pe\|growth\|margin` | Sort order (default: `score`) |
| `--format text\|json` | Output format (default: `text`) |

## Notes

- Default universe: ~50 large-cap S&P 500 stocks (hardcoded to avoid rate limits)
- Score = normalized composite of growth, margin, and inverse P/E
- Results fetched sequentially; may take 30-60 seconds for full universe
- Output cached to `~/.value_claw/stock_screener/`
