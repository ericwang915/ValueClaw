---
name: soros-macro
description: "George Soros reflexivity and macro trading framework — identify self-reinforcing boom/bust cycles. Use when: user asks about reflexivity, boom-bust cycles, macro regime analysis, Soros-style trading signals, or currency stress."
metadata:
  emoji: "🔄"
---
# Soros Macro / Reflexivity Analysis

George Soros-inspired reflexivity framework: identify self-reinforcing feedback loops, boom/bust dynamics, and macro inflection points.

## When to Use

- Analyze markets or assets for reflexivity (self-reinforcing trends)
- Detect boom/bust cycle positioning
- Macro regime and policy divergence analysis
- Currency stress and volatility regime assessment

## When NOT to Use

- Fundamental stock-picking
- Long-term buy-and-hold analysis
- Portfolio construction

## Usage

```bash
# Analyze a market index
python {skill_path}/soros_analyze.py --market SPY

# Analyze a specific stock
python {skill_path}/soros_analyze.py --ticker TSLA

# Analyze a currency pair proxy
python {skill_path}/soros_analyze.py --currency USDJPY

# JSON output
python {skill_path}/soros_analyze.py --market SPY --format json
```

| Option | Description |
|--------|-------------|
| `--market INDEX` | Market index ETF to analyze (e.g., SPY, QQQ) |
| `--ticker SYM` | Individual stock to analyze |
| `--currency PAIR` | Currency pair proxy (e.g., USDJPY, EURUSD) |
| `--format text\|json` | Output format (default: text) |

## Reflexivity Score (0-100)

| Factor | Weight | Method |
|--------|--------|--------|
| Trend Strength | 25 | Data (momentum, RSI) |
| Leverage / Credit Conditions | 25 | LLM evaluated |
| Narrative Strength | 25 | LLM evaluated |
| Policy Response Probability | 25 | LLM evaluated |

## Dependencies

```bash
pip install yfinance pandas requests
```
