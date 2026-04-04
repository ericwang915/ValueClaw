---
name: marks-cycles
description: "Howard Marks cycle analysis — market temperature gauge, pendulum positioning, risk assessment. Use when: user asks about market cycles, market sentiment gauge, risk temperature, contrarian signals, or Howard Marks-style analysis."
metadata:
  emoji: "🌡️"
---
# Marks Cycle Analysis

Howard Marks-inspired cycle analysis: market temperature gauge, pendulum positioning, and contrarian risk assessment.

## When to Use

- Assess where we are in the market cycle
- Market sentiment and temperature gauging
- Contrarian signal generation
- Risk environment assessment

## When NOT to Use

- Individual stock picking
- Portfolio construction
- Short-term trading signals

## Usage

```bash
# Analyze market temperature
python {skill_path}/marks_analyze.py --index SPY

# JSON output
python {skill_path}/marks_analyze.py --index SPY --format json
```

| Option | Description |
|--------|-------------|
| `--index SYM` | Market index ETF to analyze (default: SPY) |
| `--format text\|json` | Output format (default: text) |

## Market Temperature (0-100)

| Range | Zone | Marks Pendulum |
|-------|------|----------------|
| 0-20 | Fear | Extreme pessimism — time to be aggressive |
| 20-40 | Caution | Below-average sentiment — lean bullish |
| 40-60 | Neutral | Fair pricing — stay disciplined |
| 60-80 | Optimism | Above-average enthusiasm — reduce risk |
| 80-100 | Euphoria | Extreme greed — time to be defensive |

## Inputs

VIX level + percentile, S&P P/E vs historical, credit spreads, put/call ratio, margin debt proxy, IPO activity proxy.

## Dependencies

```bash
pip install yfinance pandas requests
```
