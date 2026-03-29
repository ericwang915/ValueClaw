---
name: commodity-tracker
description: >
  Track prices for major commodities including oil, gold, silver, copper, nat gas, and agriculture.
  Use when: the user asks about commodity prices, oil/gold/silver quotes,
  agricultural futures, or wants a commodities dashboard.
dependencies: yfinance
metadata:
  emoji: "📦"
---
# Commodity Tracker

## When to Use

- [ ] Check current commodity prices (oil, gold, silver, etc.)
- [ ] View daily/weekly/monthly/YTD performance
- [ ] Compare 52-week ranges across commodities
- [ ] Get a quick commodities dashboard

## When NOT to Use

- [ ] Commodity options or derivatives analytics
- [ ] Physical commodity logistics or supply chain
- [ ] Niche commodities not covered by CME/NYMEX futures

## Usage/Commands

```bash
python {skill_path}/commodity_tracker.py [options]
```

| Option | Description |
|--------|-------------|
| `--commodities NAME [NAME ...]` | Specific commodities: oil, gold, silver, copper, natgas, corn, wheat, soybeans |
| `--all` | Track all supported commodities |
| `--format text\|json` | Output format (default: text) |

## Examples

Quick gold and oil check:
```bash
python commodity_tracker.py --commodities oil gold
```

Full dashboard:
```bash
python commodity_tracker.py --all
```

## Notes

- Uses yfinance futures symbols (CL=F, GC=F, SI=F, etc.)
- Prices reflect front-month futures contracts
- YTD change computed from first trading day of the year
