---
name: ipo-tracker
description: >
  Track upcoming and recent IPOs, SPAC mergers, and new listing performance.
  Use when: user asks about upcoming IPOs, recent listings, SPAC deals,
  or post-IPO stock performance.
metadata:
  emoji: "N"
---

# IPO Tracker

## When to Use

- Track upcoming IPO filings and expected listing dates
- Review recent IPO performance (first-day pop, current vs offer price)
- Monitor SPAC merger activity
- Screen new listings by sector or exchange

## When NOT to Use

- Detailed fundamental analysis of established companies (use stock-analysis)
- Historical IPO data older than 1 year

## Usage

```bash
# Show upcoming IPOs
python {skill_path}/ipo_tracker.py --upcoming

# Show recent IPOs from the last 30 days with performance
python {skill_path}/ipo_tracker.py --recent 30

# JSON output
python {skill_path}/ipo_tracker.py --upcoming --format json
```

| Option | Description |
|--------|-------------|
| `--upcoming` | Show upcoming/expected IPOs |
| `--recent N` | Show IPOs from the last N days with performance |
| `--format text\|json` | Output format (default: text) |

## Dependencies

```bash
pip install yfinance requests
```

## Notes

- Scrapes SEC EDGAR for S-1 filings to detect upcoming IPOs
- Uses yfinance for post-IPO price performance data
- Includes a curated list of notable recent/upcoming IPOs as fallback
