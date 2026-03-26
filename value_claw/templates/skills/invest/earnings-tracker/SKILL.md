---
name: earnings-tracker
description: "Track earnings releases and analyze historical earnings performance. Shows weekly earnings calendar, EPS estimates, beat/miss rates, and post-earnings price drift patterns."
dependencies: yfinance
metadata:
  emoji: "📊"
---

# Earnings Tracker

Track upcoming earnings releases and analyze historical earnings performance patterns. This skill helps investors prepare for earnings season by monitoring release schedules and analyzing historical price reactions.

## Usage

The earnings tracker provides earnings calendars and detailed analysis of individual companies' earnings patterns.

```bash
# View this week's earnings calendar
python3 earnings_tracker.py --calendar

# Analyze specific company earnings history
python3 earnings_tracker.py AAPL

# Get next week's earnings releases
python3 earnings_tracker.py --calendar --next-week

# Show only major companies (market cap > $10B)
python3 earnings_tracker.py --calendar --major-only

# Analyze earnings surprise history
python3 earnings_tracker.py TSLA --surprise-history

# Show post-earnings drift analysis
python3 earnings_tracker.py NVDA --drift-analysis

# Get EPS estimates and guidance
python3 earnings_tracker.py MSFT --estimates
```

## Commands

- **Earnings Calendar**: `--calendar` - Show upcoming earnings releases for the week
- **Individual Analysis**: `python3 earnings_tracker.py TICKER` - Comprehensive earnings analysis for specific stock
- **Next Week**: `--next-week` - Show next week's earnings (with --calendar)
- **Major Only**: `--major-only` - Filter calendar to large-cap companies only
- **Surprise History**: `--surprise-history` - Show last 8 quarters of earnings surprises
- **Drift Analysis**: `--drift-analysis` - Analyze 1/5/20 day post-earnings price movements
- **EPS Estimates**: `--estimates` - Show consensus estimates and guidance
- **Beat Rate**: `--beat-rate` - Calculate historical beat/miss percentage

## Analysis Features

**Earnings Calendar**: Weekly view of upcoming releases with timing (pre/post market)
**Historical Surprises**: Track EPS beats/misses vs consensus estimates
**Price Drift**: Analyze stock performance 1, 5, and 20 days post-earnings
**Beat Rates**: Calculate percentage of quarters with positive surprises
**Revenue Growth**: Track quarterly revenue growth patterns