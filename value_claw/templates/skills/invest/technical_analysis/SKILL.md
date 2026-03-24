---
name: technical_analysis
description: "Calculate and interpret daily K-line technical indicators: moving averages (MA5/10/20/60/120/250), MACD, RSI, Bollinger Bands, KDJ, ATR, OBV, volume analysis, and golden/death cross detection. Outputs a complete signal summary. Use when: user asks about K-line chart, technical signals, trend analysis, support/resistance, overbought/oversold conditions, or chart patterns. Works for any market (US, A-shares, HK, crypto, forex)."
dependencies: yfinance
metadata:
  emoji: "📈"
---

# Technical Analysis Skill

Daily K-line technical indicator analysis using pure pandas (no extra dependencies beyond yfinance).

## When to Use

✅ **USE this skill when:**
- "What's the MACD/RSI for TSLA?"  /  "茅台的KDJ指标怎么样？"
- "Is AAPL overbought?"
- "Show me the technical analysis for BTC"
- "Has there been a golden cross on NVDA?"
- "What's the trend for 600519.SS?"

## Usage/Commands

```bash
# Full technical analysis (default)
python {skill_path}/technicals.py SYMBOL

# Custom lookback period
python {skill_path}/technicals.py SYMBOL --period 6mo   # 3mo, 6mo, 1y, 2y (default: 1y)

# Show specific indicators only
python {skill_path}/technicals.py SYMBOL --show ma       # Moving averages only
python {skill_path}/technicals.py SYMBOL --show macd
python {skill_path}/technicals.py SYMBOL --show rsi
python {skill_path}/technicals.py SYMBOL --show bb       # Bollinger Bands
python {skill_path}/technicals.py SYMBOL --show kdj
python {skill_path}/technicals.py SYMBOL --show all      # All (default)

# JSON output
python {skill_path}/technicals.py SYMBOL --format json
```

## Indicators Computed

| Indicator | Parameters | Signal |
|-----------|-----------|--------|
| SMA | 5, 10, 20, 60, 120, 250 | Trend direction, MA alignment |
| EMA | 12, 26 | Used in MACD |
| MACD | (12, 26, 9) | Bullish/bearish crossover, histogram |
| RSI | 14 | Overbought >70, Oversold <30 |
| Bollinger Bands | (20, 2σ) | Band width, price position |
| KDJ | (9, 3, 3) | K/D crossover, J overbought/oversold |
| ATR | 14 | Volatility measure |
| OBV | — | Volume trend confirmation |
| Volume Ratio | 20-day avg | Unusual volume detection |

## Signal Summary

Each analysis ends with a **Signal Summary** covering:
- MA trend: 多头排列 (bullish) / 空头排列 (bearish)
- RSI signal
- MACD momentum direction
- KDJ K vs D crossover
- Golden Cross / Death Cross alerts

## Notes

- Uses pure pandas — no `ta-lib` or `pandas-ta` needed
- All calculations done on daily close/OHLCV from Yahoo Finance
- Works for US stocks, A-shares (600519.SS), HK (0700.HK), crypto (BTC-USD), forex (EURUSD=X)
