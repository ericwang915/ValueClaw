---
name: chart-generator
description: >
  Generate publication-quality charts — line, bar, pie, heatmap from data.
  Use when: user asks to create a chart, plot data, visualize trends,
  or generate a graph from tickers or JSON data.
metadata:
  emoji: "C"
---

# Chart Generator

## When to Use

- Generate line, bar, pie, or heatmap charts from data
- Visualize stock price trends for given tickers
- Create charts from JSON input files
- Save publication-quality PNG charts

## When NOT to Use

- Interactive/real-time dashboards
- Complex candlestick charts with overlays (use trend-monitoring)

## Usage

```bash
# Line chart from tickers
python {skill_path}/chart_generator.py --tickers AAPL MSFT GOOGL --type line --period 1y

# Bar chart from JSON data
python {skill_path}/chart_generator.py --input data.json --type bar --title "Revenue by Quarter"

# Pie chart with labels
python {skill_path}/chart_generator.py --input data.json --type pie --title "Portfolio Allocation"

# Custom axis labels
python {skill_path}/chart_generator.py --tickers AAPL --type line --xlabel "Date" --ylabel "Price ($)"
```

| Option | Description |
|--------|-------------|
| `--type line\|bar\|pie\|heatmap` | Chart type (default: line) |
| `--tickers T1 T2 ...` | Fetch data from yfinance |
| `--input FILE` | JSON input file |
| `--period 1m\|3m\|6m\|1y\|5y` | Data period for tickers (default: 1y) |
| `--title TEXT` | Chart title |
| `--xlabel TEXT` | X-axis label |
| `--ylabel TEXT` | Y-axis label |
| `--format text\|json` | Output format (default: text) |

## Dependencies

```bash
pip install matplotlib yfinance
```

## Notes

- Charts saved to `~/.value_claw/charts/`
- Supports multiple tickers overlaid on one chart
- JSON input should have "labels" and "values" keys, or array of objects
