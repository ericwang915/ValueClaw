---
name: yield-curve
description: >
  Fetch US Treasury yield curve from FRED, detect inversions, and track spread history.
  Use when: the user asks about the yield curve, Treasury yields, 2s10s spread,
  3m10y spread, yield curve inversions, or recession indicators.
dependencies: requests
metadata:
  emoji: "📈"
---
# Yield Curve

## When to Use

- [ ] View the current US Treasury yield curve
- [ ] Check for yield curve inversions (2s10s, 3m10y)
- [ ] Track spread history over a date range
- [ ] Assess recession probability via curve shape

## When NOT to Use

- [ ] Non-US sovereign yield curves
- [ ] Corporate bond yield curves
- [ ] Real-time intraday yield movements

## Usage/Commands

```bash
python {skill_path}/yield_curve.py [options]
```

| Option | Description |
|--------|-------------|
| `--history N` | Show spread history for last N days (default: current snapshot only) |
| `--format text\|json` | Output format (default: text) |

## Examples

Current yield curve snapshot:
```bash
python yield_curve.py
```

Spread history over 90 days:
```bash
python yield_curve.py --history 90
```

## Notes

- Data sourced from FRED public CSV endpoint (no API key required)
- Treasury maturities: 1M, 3M, 6M, 1Y, 2Y, 3Y, 5Y, 7Y, 10Y, 20Y, 30Y
- Inversion is flagged when short-term yields exceed long-term yields
