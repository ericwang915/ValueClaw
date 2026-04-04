---
name: economic-calendar
description: "Track upcoming economic events and releases that can impact markets. Provides economic calendar with country filters, impact levels, and highlights key events like FOMC, CPI, NFP."
dependencies: requests,beautifulsoup4
metadata:
  emoji: "📅"
---

# Economic Calendar

Track upcoming economic events and data releases that can significantly impact financial markets. This skill helps investors prepare for market-moving events by monitoring economic calendars from multiple sources.

## Usage

The economic calendar provides a command-line interface to view upcoming economic events with filtering capabilities.

```bash
# View this week's economic events
python3 econ_calendar.py

# View next week's events
python3 econ_calendar.py --next-week

# Filter by country
python3 econ_calendar.py --country US --country China

# Filter by impact level
python3 econ_calendar.py --impact high --impact medium

# Custom date range
python3 econ_calendar.py --start-date 2024-03-01 --end-date 2024-03-07

# Show only major events (FOMC, CPI, NFP, etc.)
python3 econ_calendar.py --major-only
```

## Commands

- **This Week**: `python3 econ_calendar.py` - Show this week's economic events
- **Next Week**: `--next-week` - Show next week's events  
- **Country Filter**: `--country COUNTRY` - Filter by specific countries (US, China, EU, Japan, UK)
- **Impact Filter**: `--impact LEVEL` - Filter by impact level (high, medium, low)
- **Date Range**: `--start-date YYYY-MM-DD --end-date YYYY-MM-DD` - Custom date range
- **Major Events**: `--major-only` - Show only major market-moving events
- **Detailed View**: `--verbose` - Show additional event details and descriptions

The tool highlights critical events like FOMC meetings, CPI releases, Non-Farm Payrolls (NFP), PMI data, and GDP announcements that typically cause significant market volatility.