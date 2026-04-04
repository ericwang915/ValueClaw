---
name: fx-analysis
description: >
  Technical and fundamental FX pair analysis with carry trade signals.
  Use when: the user asks for FX technical analysis, RSI, moving averages,
  Bollinger Bands, carry trade opportunities, or interest rate differentials.
dependencies: yfinance
metadata:
  emoji: "🔍"
---
# FX Analysis

## When to Use

- [ ] Technical analysis of a currency pair (RSI, SMA, Bollinger)
- [ ] Assess interest rate differentials for carry trades
- [ ] Evaluate historical volatility of a pair
- [ ] Generate a data-rich analysis prompt for LLM review

## When NOT to Use

- [ ] Real-time trade execution or signals
- [ ] Options or derivatives on FX pairs
- [ ] Fundamental macro forecasting models

## Usage/Commands

```bash
python {skill_path}/fx_analysis.py --pair EURUSD [options]
```

| Option | Description |
|--------|-------------|
| `--pair PAIR` | Currency pair to analyze (e.g. EURUSD, USDJPY) |
| `--period PERIOD` | Data lookback (default: 6mo) |
| `--format text\|json` | Output format (default: text) |

## Examples

Full EUR/USD analysis:
```bash
python fx_analysis.py --pair EURUSD
```

JSON output for JPY carry trade assessment:
```bash
python fx_analysis.py --pair USDJPY --format json
```

## Notes

- RSI uses 14-period default
- SMAs: 20, 50, 200 day
- Bollinger Bands: 20-day SMA with 2 standard deviations
- Central bank rates are approximations updated periodically
