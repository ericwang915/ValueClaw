---
name: buffett-value
description: "Warren Buffett value investing framework — moat analysis, owner earnings, margin of safety. Use when: user asks for Buffett-style analysis, value investing screen, moat assessment, or owner earnings calculation."
metadata:
  emoji: "🏦"
---
# Buffett Value Analysis

Warren Buffett-inspired value investing framework: durable competitive advantages, owner earnings, and margin of safety.

## When to Use

- Buffett-style fundamental analysis of a stock
- Moat and competitive advantage assessment
- Owner earnings and intrinsic value estimation
- Screening for Buffett-style quality-value stocks

## When NOT to Use

- Growth/momentum investing
- Technical analysis
- Macro or top-down allocation

## Usage

```bash
# Analyze tickers
python {skill_path}/buffett_analyze.py --tickers BRK-B KO AAPL

# JSON output
python {skill_path}/buffett_analyze.py --tickers AAPL --format json
```

| Option | Description |
|--------|-------------|
| `--tickers SYM [SYM ...]` | Tickers to analyze (required) |
| `--format text\|json` | Output format (default: text) |

## Scoring (0-100)

| Criterion | Max | Method |
|-----------|-----|--------|
| Durable Moat | 20 | LLM evaluated |
| Consistent Earnings | 15 | Data (revenue consistency 5yr) |
| Low Debt | 15 | Data (debt-to-equity) |
| High ROE | 15 | Data (5yr average) |
| Reasonable Valuation | 20 | Data (P/E vs growth) |
| Management Quality | 15 | LLM evaluated |

## Dependencies

```bash
pip install yfinance
```
