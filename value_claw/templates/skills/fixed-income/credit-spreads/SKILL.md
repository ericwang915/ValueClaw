---
name: credit-spreads
description: >
  Track investment-grade and high-yield credit spreads using FRED data.
  Use when: the user asks about credit spreads, IG/HY OAS, corporate bond risk,
  or credit market stress indicators.
dependencies: requests
metadata:
  emoji: "📉"
---
# Credit Spreads

## When to Use

- [ ] Check current IG or HY credit spreads
- [ ] Track credit spread trends and 52-week ranges
- [ ] Assess credit market stress levels via percentile rank
- [ ] Compare BBB vs IG vs HY spread dynamics

## When NOT to Use

- [ ] Individual corporate bond analysis
- [ ] CDS spreads or credit default swap pricing
- [ ] Emerging market sovereign spreads

## Usage/Commands

```bash
python {skill_path}/credit_spreads.py [options]
```

| Option | Description |
|--------|-------------|
| `--history N` | Show spread history for last N days (default: 30) |
| `--format text\|json` | Output format (default: text) |

## Examples

Current credit spread snapshot:
```bash
python credit_spreads.py
```

Extended history with JSON:
```bash
python credit_spreads.py --history 365 --format json
```

## Notes

- Data sourced from FRED (ICE BofA indices): BAMLC0A0CM (IG), BAMLH0A0HYM2 (HY), BAMLC0A4CBBB (BBB)
- OAS = Option-Adjusted Spread over Treasuries in basis points
- Percentile rank uses available history window for context
