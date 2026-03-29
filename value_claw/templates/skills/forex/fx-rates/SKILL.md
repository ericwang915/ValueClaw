---
name: fx-rates
description: >
  Real-time and historical FX rates for major currency pairs via yfinance.
  Use when: the user asks about exchange rates, currency prices, FX pair history,
  or wants to compare multiple currency pairs.
dependencies: yfinance
metadata:
  emoji: "💹"
---
# FX Rates

## When to Use

- [ ] Check current exchange rates for major pairs
- [ ] View historical FX rate data over a period
- [ ] Compare multiple currency pairs side by side
- [ ] Track daily changes and 52-week ranges

## When NOT to Use

- [ ] Crypto exchange rates (use a crypto-specific tool)
- [ ] Real-time tick-level data for trading
- [ ] Forward rates or FX options pricing

## Usage/Commands

```bash
python {skill_path}/fx_rates.py --pairs EURUSD GBPUSD USDJPY [options]
```

| Option | Description |
|--------|-------------|
| `--pairs PAIR [PAIR ...]` | Currency pairs (e.g. EURUSD GBPUSD USDJPY) |
| `--history PERIOD` | Historical data period (1d, 5d, 1mo, 3mo, 6mo, 1y) |
| `--format text\|json` | Output format (default: text) |

## Examples

Major pairs snapshot:
```bash
python fx_rates.py --pairs EURUSD GBPUSD USDJPY USDCNH
```

EUR/USD with 30-day history:
```bash
python fx_rates.py --pairs EURUSD --history 1mo --format json
```

## Notes

- Uses yfinance tickers (e.g. EURUSD=X, GBPUSD=X)
- Rates are delayed ~15 minutes
- 52-week range from available history
