---
name: backtester
description: >
  Simple strategy backtester — test SMA crossover, momentum, or buy-and-hold
  strategies with performance metrics. Use when: the user wants to backtest a
  trading strategy, compare returns, or evaluate drawdowns and Sharpe ratios.
metadata:
  emoji: "🔁"
---
# Backtester

## When to Use

- [ ] Backtest SMA crossover strategies with custom fast/slow windows
- [ ] Test momentum strategies with a lookback period
- [ ] Compare any strategy to buy-and-hold benchmark
- [ ] Get total return, annual return, max drawdown, Sharpe ratio

## When NOT to Use

- [ ] Live trading or paper trading execution
- [ ] Options or fixed-income strategy backtesting
- [ ] Strategies requiring intraday data

## Setup

Install dependency: `pip install yfinance numpy`

## Usage/Commands

```bash
python {skill_path}/backtester.py --ticker AAPL --start 2020-01-01 --end 2025-01-01 --strategy sma_cross [options]
```

| Option | Description |
|--------|-------------|
| `--ticker SYM` | Stock ticker (required) |
| `--start DATE` | Start date YYYY-MM-DD (default: 2020-01-01) |
| `--end DATE` | End date YYYY-MM-DD (default: 2025-01-01) |
| `--strategy sma_cross\|momentum\|buy_hold` | Strategy type (default: `sma_cross`) |
| `--fast N` | Fast SMA period for sma_cross (default: 20) |
| `--slow N` | Slow SMA period for sma_cross (default: 50) |
| `--lookback N` | Lookback days for momentum (default: 60) |
| `--format text\|json` | Output format (default: `text`) |

## Notes

- Uses daily close prices from yfinance
- Sharpe ratio computed assuming 252 trading days and 0% risk-free rate
- Max drawdown is peak-to-trough percentage decline
- Output cached to `~/.value_claw/backtester/`
