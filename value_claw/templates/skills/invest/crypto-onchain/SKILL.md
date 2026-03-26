---
name: crypto-onchain
description: "Comprehensive cryptocurrency analysis using free APIs. Tracks prices, market cap, Fear & Greed Index, trending coins, DeFi TVL, and historical performance across multiple timeframes."
dependencies: requests
metadata:
  emoji: "₿"
---

# Crypto On-Chain Analysis

Comprehensive cryptocurrency market analysis using free APIs from CoinGecko, DeFiLlama, and Alternative.me. This skill provides market data, sentiment indicators, and DeFi ecosystem insights.

## Usage

The crypto analyzer provides real-time and historical cryptocurrency data with market sentiment analysis.

```bash
# Get Bitcoin analysis
python3 crypto_data.py bitcoin

# Top cryptocurrencies by market cap
python3 crypto_data.py --top 20

# Crypto Fear & Greed Index
python3 crypto_data.py --fear-greed

# Trending cryptocurrencies
python3 crypto_data.py --trending

# Specific crypto with historical data
python3 crypto_data.py ethereum --history 30d

# DeFi ecosystem overview
python3 crypto_data.py --defi-tvl

# Portfolio tracking (multiple cryptos)
python3 crypto_data.py bitcoin,ethereum,solana --portfolio

# Market overview dashboard
python3 crypto_data.py --market-overview

# Price comparison across timeframes
python3 crypto_data.py bitcoin --timeframes 7d,30d,90d
```

## Commands

- **Individual Crypto**: `python3 crypto_data.py CRYPTO_ID` - Detailed analysis of specific cryptocurrency
- **Top Cryptos**: `--top N` - Show top N cryptocurrencies by market cap
- **Fear & Greed**: `--fear-greed` - Crypto market sentiment index
- **Trending**: `--trending` - Currently trending cryptocurrencies
- **Historical Data**: `--history PERIOD` - Price history (7d, 30d, 90d, 1y)
- **DeFi TVL**: `--defi-tvl` - Total Value Locked in DeFi protocols
- **Portfolio Mode**: `--portfolio` - Analyze multiple cryptos together
- **Market Overview**: `--market-overview` - Complete market dashboard
- **Timeframe Compare**: `--timeframes PERIODS` - Compare performance across periods
- **Price Alerts**: `--alerts` - Check for significant price movements
- **Volume Analysis**: `--volume` - Focus on trading volume metrics

## Data Sources

**CoinGecko API**: Price, market cap, volume, historical data
**Alternative.me**: Crypto Fear & Greed Index
**DeFiLlama API**: DeFi Total Value Locked (TVL) data
**Trending Data**: Real-time trending cryptocurrencies

All data sources are free and don't require API keys for basic usage.