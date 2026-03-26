---
name: insider-tracker
description: "Track insider trading activity for stocks using SEC EDGAR API and OpenInsider data. Detects cluster buying patterns, filters by transaction size, and provides net insider sentiment analysis."
dependencies: requests,beautifulsoup4
metadata:
  emoji: "👔"
---

# Insider Trading Tracker

Track insider trading activity for stocks using free SEC EDGAR API and OpenInsider data. This skill helps identify potential investment signals by monitoring when company insiders are buying or selling shares.

## Usage

The skill provides a command-line interface to analyze insider trading patterns for any stock ticker.

```bash
# Basic insider analysis for a ticker
python3 insider_tracker.py AAPL

# Filter by transaction size (>$100K, >$1M)
python3 insider_tracker.py AAPL --min-value 100000

# Look for cluster buying in last 30 days
python3 insider_tracker.py AAPL --days 30 --cluster-only

# Get detailed analysis with specific date range
python3 insider_tracker.py TSLA --start-date 2024-01-01 --end-date 2024-03-01
```

## Commands

- **Basic Analysis**: `python3 insider_tracker.py TICKER` - Get recent insider trading summary
- **Value Filter**: `--min-value AMOUNT` - Only show transactions above specified dollar amount
- **Cluster Detection**: `--cluster-only` - Only show periods with multiple insider buys
- **Date Range**: `--start-date YYYY-MM-DD --end-date YYYY-MM-DD` - Custom date range
- **Time Window**: `--days N` - Look back N days from today
- **Detailed Output**: `--verbose` - Show individual transactions with details

The tool analyzes insider sentiment by calculating buy/sell ratios, identifying cluster buying patterns (multiple insiders buying within 30 days), and flagging unusual activity patterns.