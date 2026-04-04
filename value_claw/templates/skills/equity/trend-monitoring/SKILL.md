---
name: trend-monitoring
description: "Full-pipeline stock trend analysis: generates professional candlestick charts (BB, SMA, RSI, MACD, pattern detection), TradingView indicator tables, news summaries, and LLM-powered trading signals — outputs combined PNG images. Use when: user wants trend analysis with charts, visual stock reports, technical analysis images, or market monitoring reports. To send images, use the existing channel (Telegram) or twitter-post skill."
metadata:
  emoji: "📊"
---

# Trend Monitoring Skill

Full-pipeline stock trend analysis with professional chart generation and LLM-powered analysis.

## When to Use

✅ **USE this skill when:**
- "Analyze TSLA trend and show me the chart"
- "Generate a technical analysis report for AAPL with images"
- "Run trend analysis on these stocks"
- "Show me a candlestick chart with RSI and MACD for NVDA"
- "Create a visual stock report"

## Features

1. **Candlestick Charts** — 6-month OHLCV with Bollinger Bands, SMA20/50, RSI, MACD, volume panels, buy/sell markers, pattern detection (Double Top/Bottom, Head & Shoulders)
2. **TradingView Indicator Table** — Oscillators + Moving Averages summary rendered as a styled table image
3. **News Aggregation** — Recent headlines + article summaries from Yahoo Finance
4. **LLM Analysis** — Uses the default configured LLM to generate signal (Strong Positive → Strong Negative), confidence score, and key drivers
5. **Combined Image** — Trend chart + indicator table stitched into one professional PNG

## Usage/Commands

```bash
# Analyze one or more tickers (generates charts + LLM analysis)
python {skill_path}/trend_monitor.py TSLA AAPL NVDA

# Charts only (skip LLM analysis — faster)
python {skill_path}/trend_monitor.py TSLA --no-llm

# Skip news fetching (even faster, charts + indicators only)
python {skill_path}/trend_monitor.py TSLA --no-news

# JSON output (for programmatic use — includes image paths)
python {skill_path}/trend_monitor.py TSLA --format json

# Specify config file path
python {skill_path}/trend_monitor.py TSLA --config /path/to/value_claw.json
```

## Output Files

All generated data is stored under `~/.value_claw/trend_monitoring/`:

| Directory | Content |
|-----------|---------|
| `images/trend/` | Candlestick chart PNGs |
| `images/indicators/` | Indicator table PNGs |
| `images/combined/` | Stitched trend + indicator PNGs |
| `news/` | News CSV files |
| `stats/` | Key stats text files |
| `prompt/` | LLM prompt text files |

## Sending Images

This skill generates images only. To deliver them:
- **Telegram**: Use the agent's built-in Telegram channel — just tell the agent "send this chart to Telegram"
- **Twitter**: Use the `twitter-post` skill — `python {twitter-post_skill_path}/twitter_post.py "TSLA Analysis" --image /path/to/combined.png`
- **Discord**: Use a Discord webhook skill or the agent's Discord channel

## Dependencies

```bash
pip install mplfinance matplotlib scipy tradingview-ta Pillow pandas yfinance
```

## Notes

- Uses the **default configured LLM** from `value_claw.json` (`llm.provider`) for analysis
- TradingView data is fetched via public API (no key needed, US stocks only: NASDAQ/NYSE/AMEX)
- yfinance provides free market data (no key needed)
- Chart images are 300 DPI, suitable for sharing on social media
- No additional tokens required — uses existing LLM configuration
