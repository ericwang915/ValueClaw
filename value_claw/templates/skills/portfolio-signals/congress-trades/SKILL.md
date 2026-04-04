---
name: congress-trades
description: "Track US congressional stock trades from STOCK Act disclosures. Use when: user asks about politician stock trades, congressional trading activity, insider government trades, or STOCK Act filings."
metadata:
  emoji: "🏛️"
---
# Congress Trades

Track stock transactions disclosed by US members of Congress under the STOCK Act.

## When to Use

- User asks about congressional stock trading activity
- Filter trades by specific ticker or congress member
- Monitor recent congressional trades for signals

## When NOT to Use

- Senate-only trades (this covers House disclosures)
- Historical analysis beyond what the API provides

## Usage

```bash
# Recent trades (last 30 days)
python {skill_path}/congress_trades.py --days 30

# Filter by ticker
python {skill_path}/congress_trades.py --ticker AAPL

# Filter by member
python {skill_path}/congress_trades.py --member "Pelosi"

# Combine filters
python {skill_path}/congress_trades.py --ticker NVDA --days 60

# JSON output
python {skill_path}/congress_trades.py --ticker MSFT --format json
```

| Option | Description |
|--------|-------------|
| `--ticker SYMBOL` | Filter by stock ticker |
| `--member NAME` | Filter by congress member name (partial match) |
| `--days N` | Only show trades from the last N days (default: all) |
| `--limit N` | Max number of trades to display (default: 50) |
| `--format text\|json` | Output format (default: text) |

## Data Source

House Stock Watcher API — aggregates STOCK Act disclosures from the US House of Representatives.

## Dependencies

```bash
pip install requests
```
