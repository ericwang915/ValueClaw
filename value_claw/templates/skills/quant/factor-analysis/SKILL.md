---
name: factor-analysis
description: >
  Fama-French factor exposure analysis — decompose stock returns into market,
  size (SMB), and value (HML) factors via OLS regression. Use when: the user
  asks about factor exposure, alpha, beta decomposition, or Fama-French analysis.
metadata:
  emoji: "🧮"
---
# Factor Analysis

## When to Use

- [ ] Decompose stock returns into market, size, and value factors
- [ ] Estimate alpha (excess return beyond factor exposure)
- [ ] Find a stock's factor loadings (beta, SMB, HML)
- [ ] Compare factor exposures across stocks

## When NOT to Use

- [ ] Full 5-factor or custom factor models
- [ ] Real-time intraday factor attribution
- [ ] Bond or options factor analysis

## Setup

Install dependencies: `pip install yfinance numpy requests`

No statsmodels required — uses numpy least-squares regression.

## Usage/Commands

```bash
python {skill_path}/factor_analysis.py --ticker TSLA --period 3y [options]
```

| Option | Description |
|--------|-------------|
| `--ticker SYM` | Stock ticker (required) |
| `--period Ny` | Lookback period: 1y, 2y, 3y, 5y (default: `3y`) |
| `--format text\|json` | Output format (default: `text`) |

## Data Sources

- **Stock returns** — yfinance daily prices
- **Fama-French factors** — Kenneth French's data library (CSV)

## Notes

- OLS regression: Ri - Rf = alpha + beta*(Rm-Rf) + s*SMB + h*HML + e
- R-squared indicates how much return is explained by factors
- Positive alpha suggests outperformance beyond factor exposure
- Output cached to `~/.value_claw/factor_analysis/`
