---
name: bond-analysis
description: >
  Calculate YTM, duration, convexity, and current yield for bonds with comparison support.
  Use when: the user asks about bond valuation, yield to maturity, duration risk,
  convexity, or wants to compare multiple bonds.
dependencies: null
metadata:
  emoji: "📊"
---
# Bond Analysis

## When to Use

- [ ] Calculate yield to maturity (YTM) for a bond
- [ ] Compute Macaulay duration, modified duration, or convexity
- [ ] Compare two or more bonds on risk/return metrics
- [ ] Assess current yield vs. YTM

## When NOT to Use

- [ ] Real-time bond price feeds (use a data terminal)
- [ ] Municipal or convertible bond-specific analytics
- [ ] Credit risk modeling beyond basic metrics

## Usage/Commands

```bash
python {skill_path}/bond_analysis.py --face 1000 --coupon 5.0 --maturity 10 --price 950 [options]
```

| Option | Description |
|--------|-------------|
| `--face VALUE` | Face/par value of the bond (default: 1000) |
| `--coupon RATE` | Annual coupon rate as percentage (e.g. 5.0) |
| `--maturity YEARS` | Years to maturity |
| `--price PRICE` | Current market price |
| `--frequency N` | Coupon payments per year (default: 2 = semiannual) |
| `--compare` | Compare multiple bonds (repeat --face/--coupon/--maturity/--price sets) |
| `--format text\|json` | Output format (default: text) |

## Examples

Single bond:
```bash
python bond_analysis.py --face 1000 --coupon 5.0 --maturity 10 --price 950
```

JSON output:
```bash
python bond_analysis.py --face 1000 --coupon 3.5 --maturity 5 --price 1020 --format json
```

## Notes

- YTM is solved iteratively via Newton's method
- Duration and convexity assume parallel yield curve shifts
- All rates are annualized
