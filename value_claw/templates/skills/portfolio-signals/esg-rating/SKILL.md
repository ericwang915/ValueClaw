---
name: esg-rating
description: >
  ESG (Environmental, Social, Governance) analysis using yfinance data.
  Use when: user asks about ESG scores, sustainability ratings, controversy
  levels, or responsible investing metrics.
metadata:
  emoji: "E"
---

# ESG Rating

## When to Use

- Evaluate ESG scores for stocks (environmental, social, governance pillars)
- Compare controversy levels across companies
- Screen stocks for responsible/sustainable investing criteria
- Peer-compare ESG performance within a sector

## When NOT to Use

- Detailed carbon footprint or supply chain audits
- Regulatory compliance checks

## Usage

```bash
# ESG analysis for specific tickers
python {skill_path}/esg_rating.py --tickers MSFT AAPL TSLA XOM

# JSON output
python {skill_path}/esg_rating.py --tickers MSFT AAPL --format json
```

| Option | Description |
|--------|-------------|
| `--tickers T1 T2 ...` | Tickers to analyze (required) |
| `--format text\|json` | Output format (default: text) |

## Dependencies

```bash
pip install yfinance
```

## Notes

- Uses yfinance `.sustainability` property for ESG data
- Falls back to sector-average estimates when data is unavailable
- Controversy level: 0 (none) to 5 (severe)
