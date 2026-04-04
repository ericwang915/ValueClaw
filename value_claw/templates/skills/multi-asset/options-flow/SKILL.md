---
name: options-flow
description: "Analyze options flow and unusual activity for stocks using yfinance. Tracks options chains, detects unusual volume, calculates Greeks exposure, IV rank, and max pain levels."
dependencies: yfinance,numpy
metadata:
  emoji: "🎲"
---

# Options Flow Analyzer

Analyze options trading activity and detect unusual flow patterns using free Yahoo Finance data. This skill helps identify potential directional moves by monitoring options volume, Greeks exposure, and volatility patterns.

## Usage

The options flow analyzer provides comprehensive options chain analysis with unusual activity detection and Greeks calculations.

```bash
# Basic options analysis for a ticker
python3 options_flow.py AAPL

# Analyze specific expiration date
python3 options_flow.py AAPL --expiry 2024-03-15

# Detect unusual activity only
python3 options_flow.py TSLA --unusual-only

# Focus on specific option type
python3 options_flow.py SPY --type calls
python3 options_flow.py SPY --type puts

# Calculate max pain for expiry
python3 options_flow.py QQQ --max-pain

# Get IV rank analysis
python3 options_flow.py NVDA --iv-analysis
```

## Commands

- **Basic Analysis**: `python3 options_flow.py TICKER` - Complete options overview for all expirations
- **Specific Expiry**: `--expiry YYYY-MM-DD` - Analyze specific expiration date
- **Option Type**: `--type TYPE` - Focus on calls or puts only
- **Unusual Activity**: `--unusual-only` - Show only contracts with volume > 5x open interest
- **Max Pain**: `--max-pain` - Calculate maximum pain point for expiration
- **IV Analysis**: `--iv-analysis` - Show implied volatility rank and percentile
- **Greeks Summary**: `--greeks` - Show aggregate delta, gamma, theta exposure
- **Volume Threshold**: `--min-volume N` - Filter by minimum volume
- **Moneyness Filter**: `--moneyness RANGE` - Filter by strike relative to stock price

The tool identifies potential directional bias through unusual volume patterns, aggregate Greeks exposure, and volatility skew analysis.