---
name: sector-rotation
description: >
  Sector rotation analysis — relative strength, momentum, and business cycle
  positioning for S&P 500 sectors. Use when: user asks about sector performance,
  momentum rankings, or business cycle positioning.
metadata:
  emoji: "S"
---

# Sector Rotation

## When to Use

- Rank S&P 500 sectors by momentum and relative strength
- Identify which sectors lead or lag vs the broad market
- Map current conditions to business cycle phases
- Decide sector allocation tilts

## When NOT to Use

- Individual stock analysis (use stock-analysis)
- International sector comparisons

## Usage

```bash
# Sector rotation analysis (default 3-month period)
python {skill_path}/sector_rotation.py

# Custom lookback period
python {skill_path}/sector_rotation.py --period 6m

# JSON output
python {skill_path}/sector_rotation.py --period 1y --format json
```

| Option | Description |
|--------|-------------|
| `--period 1m\|3m\|6m\|1y` | Lookback period (default: 3m) |
| `--format text\|json` | Output format (default: text) |

## Dependencies

```bash
pip install yfinance
```

## Notes

- Uses SPDR sector ETFs (XLK, XLF, XLE, etc.) as sector proxies
- Relative strength computed vs SPY
- RSI computed on 14-day window
- Business cycle mapping: Early (financials, discretionary), Mid (tech, industrials), Late (energy, materials, staples), Recession (utilities, healthcare)
