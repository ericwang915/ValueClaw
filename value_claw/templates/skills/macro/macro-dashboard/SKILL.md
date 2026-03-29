---
name: macro-dashboard
description: >
  Comprehensive macro dashboard — GDP, CPI, unemployment, PMI, Fed Funds, yield
  curve across major economies. Use when: the user asks about macro outlook,
  economic indicators, recession risk, or wants a macro snapshot.
metadata:
  emoji: "📊"
---
# Macro Dashboard

## When to Use

- [ ] User wants a snapshot of key economic indicators
- [ ] Checking GDP, inflation (CPI), unemployment, PMI trends
- [ ] Assessing recession risk via yield curve (10Y-2Y spread)
- [ ] Comparing current macro state to historical norms

## When NOT to Use

- [ ] Specific stock or company analysis — use other skills
- [ ] Real-time intraday market data
- [ ] Non-US macro without explicit support

## Setup

Install dependency: `pip install requests`

FRED data is fetched from the public CSV endpoint (no API key required).

## Usage/Commands

```bash
python {skill_path}/macro_dashboard.py [options]
```

| Option | Description |
|--------|-------------|
| `--country us` | Country to pull data for (default: `us`) |
| `--format text\|json` | Output format (default: `text`) |

## Data Sources

All data pulled from FRED public CSV endpoint:
- **GDP** — nominal GDP
- **GDPC1** — real GDP
- **CPIAUCSL** — Consumer Price Index (all urban)
- **UNRATE** — Unemployment Rate
- **MANEMP** — Manufacturing Employment (PMI proxy)
- **FEDFUNDS** — Federal Funds Rate
- **T10Y2Y** — 10-Year minus 2-Year Treasury spread

## Notes

- Year-over-year changes computed automatically
- Trend detection: rising / falling / stable (based on 3-month direction)
- Output cached to `~/.value_claw/macro_dashboard/`
