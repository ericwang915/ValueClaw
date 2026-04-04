---
name: akshare_data
description: "Chinese market data via AKShare: A-share real-time quotes, historical K-line, company fundamentals, financial indicators, stock news, major indices (SSE/SZSE/CSI300/GEM), HK market data, macroeconomic indicators, and sector/industry analysis. Use when: user asks about A-share stocks, Chinese indices, China macro data, HK stocks, or any Chinese financial market information."
dependencies: akshare
metadata:
  emoji: "🇨🇳"
---

# AKShare Data Skill

Chinese market data powered by AKShare — the most comprehensive open-source Chinese financial data library.

## When to Use

✅ **USE this skill when:**
- "茅台现在股价多少？"  /  "What's Kweichow Moutai's price?"
- "沪深300最近走势"  /  "Show CSI 300 trend"
- "查一下比亚迪的财务指标"
- "A股市场今天涨跌情况"
- "港股腾讯的行情"
- "最新A股财经新闻"
- Any question about A-shares, HK stocks, Chinese macro, or domestic funds

## Usage/Commands

```bash
# Real-time quote (A-share: 6-digit code)
python {skill_path}/akshare_data.py --quote 600519     # Moutai
python {skill_path}/akshare_data.py --quote 000858     # Wuliangye
python {skill_path}/akshare_data.py --quote 300750     # CATL (GEM)

# Historical K-line data
python {skill_path}/akshare_data.py --hist 600519 --period daily --start 2024-01-01
python {skill_path}/akshare_data.py --hist 600519 --period weekly

# Company fundamentals + financial indicators
python {skill_path}/akshare_data.py --info 600519

# Recent news for a stock
python {skill_path}/akshare_data.py --news 600519

# Major indices overview
python {skill_path}/akshare_data.py --indices

# Top gainers / losers today
python {skill_path}/akshare_data.py --market

# HK stock quote
python {skill_path}/akshare_data.py --hk 00700      # Tencent

# Sector / industry performance
python {skill_path}/akshare_data.py --sectors
```

## A-Share Code Format

- **Shanghai (SSE)**: 6-digit starting with 6 (e.g., `600519`, `601318`)
- **Shenzhen (SZSE)**: 6-digit starting with 0 or 3 (e.g., `000858`, `300750`)
- **No suffix needed** — just the 6-digit code

## Data Available

| Command | Data |
|---------|------|
| `--quote` | Real-time price, change, volume, turnover |
| `--hist` | OHLCV daily/weekly/monthly K-line |
| `--info` | Company profile + key financial ratios |
| `--news` | Recent announcements and news |
| `--indices` | SSE Composite, SZSE Component, CSI 300, GEM, ChiNext |
| `--market` | Top 20 gainers and losers |
| `--hk` | HK market quotes (Tencent, Alibaba-HK, etc.) |
| `--sectors` | Sector rotation heatmap |

## Notes

- AKShare is free, no API key needed
- Data sourced from East Money (东方财富), Sina Finance, and official exchanges
- Install: `pip install akshare`
- For US stock data: use `finance` or `stock_fundamentals` skill
