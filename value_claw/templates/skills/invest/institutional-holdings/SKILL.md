---
name: institutional-holdings
description: "Analyze institutional ownership patterns and holdings changes using SEC 13F data and yfinance. Track smart money moves, concentration analysis, and quarterly changes."
dependencies: yfinance,requests,beautifulsoup4
metadata:
  emoji: "🏛️"
---

# Institutional Holdings Analyzer

Analyze institutional ownership patterns and track smart money movements using SEC 13F filings and Yahoo Finance data. This skill helps identify institutional sentiment and potential catalysts through ownership changes.

## Usage

The institutional holdings analyzer provides insights into institutional investor behavior and ownership concentration.

```bash
# Analyze institutional holdings for a stock
python3 inst_holdings.py AAPL

# Track specific fund's holdings (e.g., Berkshire Hathaway)
python3 inst_holdings.py --fund "BERKSHIRE HATHAWAY"

# Show top institutional holders with changes
python3 inst_holdings.py TSLA --changes

# Analyze ownership concentration
python3 inst_holdings.py NVDA --concentration

# Track ARK Invest holdings
python3 inst_holdings.py --fund "ARK INVESTMENT"

# Show institutional flow summary
python3 inst_holdings.py SPY --flow-summary

# Get smart money alerts (significant changes)
python3 inst_holdings.py --alerts --min-change 5
```

## Commands

- **Stock Analysis**: `python3 inst_holdings.py TICKER` - Show institutional ownership breakdown
- **Fund Tracking**: `--fund "FUND_NAME"` - Track specific institutional fund's holdings
- **Ownership Changes**: `--changes` - Show quarter-over-quarter institutional changes
- **Concentration**: `--concentration` - Analyze ownership concentration metrics
- **Flow Summary**: `--flow-summary` - Show net institutional buying/selling
- **Smart Money Alerts**: `--alerts` - Detect significant institutional moves
- **Change Threshold**: `--min-change PCT` - Filter by minimum percentage change
- **Top Holdings**: `--top-holdings N` - Show top N institutional positions

## Analysis Features

**Top Holders**: Largest institutional positions with ownership percentages
**Quarterly Changes**: Track increases/decreases in institutional positions  
**Concentration Metrics**: Analyze how concentrated ownership is among top holders
**Fund Tracking**: Monitor specific funds like ARK, Berkshire, Tiger Global
**Smart Money Signals**: Identify when multiple institutions move in same direction