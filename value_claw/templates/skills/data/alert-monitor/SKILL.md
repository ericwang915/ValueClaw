---
name: alert-monitor
description: >
  Set price and indicator alerts that trigger notifications. Use when: user
  wants to set price alerts, RSI alerts, volume alerts, or check triggered
  conditions on stocks.
metadata:
  emoji: "A"
---

# Alert Monitor

## When to Use

- Set price alerts (above/below thresholds) for stocks
- Set indicator alerts (RSI, volume conditions)
- List all configured alerts
- Check which alerts are currently triggered

## When NOT to Use

- Real-time streaming alerts (this is a poll-based checker)
- Complex multi-condition strategies (use trading-coach)

## Usage

```bash
# Add a price alert
python {skill_path}/alert_monitor.py --add --ticker AAPL --condition "price > 200"

# Add an RSI alert
python {skill_path}/alert_monitor.py --add --ticker NVDA --condition "rsi < 30"

# Add a volume alert
python {skill_path}/alert_monitor.py --add --ticker TSLA --condition "volume > 100000000"

# List all alerts
python {skill_path}/alert_monitor.py --list

# Check all alerts against current data
python {skill_path}/alert_monitor.py --check

# JSON output
python {skill_path}/alert_monitor.py --check --format json
```

| Option | Description |
|--------|-------------|
| `--add` | Add a new alert |
| `--ticker SYM` | Ticker for the alert |
| `--condition COND` | Condition string: `price > N`, `rsi < N`, `volume > N` |
| `--list` | List all configured alerts |
| `--check` | Evaluate all alerts against live data |
| `--format text\|json` | Output format (default: text) |

## Dependencies

```bash
pip install yfinance
```

## Notes

- Alerts stored in `~/.value_claw/alerts/alerts.json`
- Conditions: `price >/<` N, `rsi >/<` N, `volume >/<` N
- `--check` fetches live data and reports triggered alerts
