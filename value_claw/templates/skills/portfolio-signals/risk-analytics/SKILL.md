---
name: risk-analytics
description: "Comprehensive risk analysis for portfolios and individual stocks using statistical measures. Calculates VaR, correlations, Sharpe ratios, maximum drawdown, and stress test scenarios."
dependencies: yfinance,numpy
metadata:
  emoji: "⚖️"
---

# Risk Analytics

Comprehensive risk analysis toolkit for portfolios and individual securities using advanced statistical measures. This skill helps investors understand and quantify various types of investment risk.

## Usage

The risk analytics tool provides detailed risk assessments using historical data and statistical modeling.

```bash
# Single stock risk analysis
python3 risk_analytics.py AAPL

# Portfolio risk analysis (multiple tickers)
python3 risk_analytics.py AAPL,MSFT,GOOGL --portfolio

# Correlation matrix analysis
python3 risk_analytics.py AAPL,TSLA,NVDA --correlation-matrix

# Value at Risk calculation
python3 risk_analytics.py SPY --var --confidence 95

# Maximum drawdown analysis
python3 risk_analytics.py QQQ --drawdown

# Portfolio vs benchmark comparison
python3 risk_analytics.py AAPL,MSFT --benchmark SPY

# Stress testing with historical scenarios
python3 risk_analytics.py AAPL --stress-test --scenario covid

# Risk metrics summary
python3 risk_analytics.py TSLA --all-metrics
```

## Commands

- **Single Asset**: `python3 risk_analytics.py TICKER` - Comprehensive risk analysis for one stock
- **Portfolio Mode**: `--portfolio` - Analyze portfolio of multiple tickers
- **Correlation Matrix**: `--correlation-matrix` - Show correlation relationships
- **Value at Risk**: `--var --confidence PCT` - Calculate VaR at specified confidence level
- **Maximum Drawdown**: `--drawdown` - Detailed drawdown analysis with recovery periods
- **Benchmark Comparison**: `--benchmark TICKER` - Compare against benchmark (default: SPY)
- **Stress Testing**: `--stress-test --scenario NAME` - Test against historical scenarios
- **All Metrics**: `--all-metrics` - Complete risk dashboard
- **Time Period**: `--period PERIOD` - Historical data period (1y, 2y, 5y)
- **Output Format**: `--format FORMAT` - Choose output format (text, json)

## Risk Metrics

**VaR (Value at Risk)**: Potential loss at 95%/99% confidence over specified period
**Sharpe Ratio**: Risk-adjusted return vs risk-free rate
**Sortino Ratio**: Risk-adjusted return using downside deviation
**Maximum Drawdown**: Largest peak-to-trough decline with recovery time
**Beta**: Systematic risk vs benchmark
**Correlation Analysis**: Relationship matrix between assets
**Stress Testing**: Performance during major market events (2008, COVID, etc.)

## Position Sizing & Stop-Loss (NEW)

When presenting risk analysis, ALWAYS include actionable risk management advice:

### Position Sizing (Kelly / Volatility-based)
- **Volatility-Adjusted**: `Position % = Risk Budget / (ATR% × Leverage)`
- For a typical 2% risk budget and a stock with 3% daily ATR → ~0.67 position weight
- **Kelly Criterion** (simplified): `f = edge / odds` — for reference only, use half-Kelly in practice
- Present as: "建议仓位: X% of portfolio (based on Y% daily volatility)"

### Dynamic Stop-Loss
- **ATR Stop**: Entry price - (2 × ATR14) for long positions
- **Support-Based**: Nearest key support level from technical analysis
- **Trailing Stop**: Use 2×ATR or 20-day low as trailing stop after +10% gain
- Present both mechanical and structural stop levels

### Risk/Reward Assessment
Always calculate and display:
```
Risk/Reward Ratio: (Target - Entry) / (Entry - Stop)
Expected Value: Win% × Avg_Win - Loss% × Avg_Loss
```
A minimum 2:1 risk/reward ratio is required for a BUY recommendation.