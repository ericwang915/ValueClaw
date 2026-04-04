---
name: dalio-allweather
description: "Ray Dalio All-Weather portfolio framework — risk parity allocation and economic regime analysis. Use when: user asks about All-Weather portfolio, risk parity, economic regime detection, or Dalio-style macro allocation."
metadata:
  emoji: "🌦️"
---
# Dalio All-Weather Analysis

Ray Dalio-inspired All-Weather portfolio framework: four economic environments, risk parity allocation, and regime detection.

## When to Use

- All-Weather or risk parity portfolio construction
- Economic regime analysis (growth/inflation)
- Asset class allocation across environments
- Comparing current portfolio to All-Weather target

## When NOT to Use

- Single stock analysis
- Short-term trading signals
- Sector rotation (use fund-flows instead)

## Usage

```bash
# Default All-Weather assets
python {skill_path}/dalio_analyze.py --assets SPY TLT TIP GLD

# JSON output
python {skill_path}/dalio_analyze.py --assets SPY TLT TIP GLD --format json
```

| Option | Description |
|--------|-------------|
| `--assets SYM [SYM ...]` | Asset ETFs to analyze (default: SPY TLT TIP GLD) |
| `--format text\|json` | Output format (default: text) |

## Economic Environments

| Environment | Favored Assets |
|-------------|---------------|
| Rising Growth | Stocks, Corporate Bonds, Commodities |
| Falling Growth | Long Bonds, TIPS |
| Rising Inflation | TIPS, Commodities, Gold |
| Falling Inflation | Stocks, Long Bonds |

## Dependencies

```bash
pip install yfinance pandas requests
```
