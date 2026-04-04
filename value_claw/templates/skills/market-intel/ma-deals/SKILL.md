---
name: ma-deals
description: >
  M&A deal tracker and merger arbitrage analysis. Use when: user asks about
  pending mergers, acquisition spreads, merger arbitrage opportunities,
  or recent M&A activity.
metadata:
  emoji: "M"
---

# M&A Deals

## When to Use

- Track pending M&A deals and their completion status
- Compute merger arbitrage spreads and annualized returns
- Review recent M&A activity
- Evaluate deal risk (cash vs stock, regulatory hurdles)

## When NOT to Use

- Historical M&A analysis from years ago
- Detailed antitrust/regulatory legal analysis

## Usage

```bash
# Show pending deals with live spreads
python {skill_path}/ma_deals.py --pending

# Show recently completed deals
python {skill_path}/ma_deals.py --recent

# JSON output
python {skill_path}/ma_deals.py --pending --format json
```

| Option | Description |
|--------|-------------|
| `--pending` | Show pending deals with arbitrage spreads |
| `--recent` | Show recently completed/announced deals |
| `--format text\|json` | Output format (default: text) |

## Dependencies

```bash
pip install yfinance
```

## Notes

- Uses a curated list of well-known pending deals
- Live prices from yfinance to compute current spread
- Annualized return assumes deal closes on expected date
