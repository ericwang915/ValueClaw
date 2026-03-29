---
name: central-bank-watch
description: >
  Central bank rate decisions and policy stance for Fed, ECB, BOJ, BOE, PBOC.
  Use when: the user asks about interest rates, central bank policy, rate hikes
  or cuts, or wants to compare monetary policy across countries.
metadata:
  emoji: "🏦"
---
# Central Bank Watch

## When to Use

- [ ] Check current policy rates for major central banks
- [ ] Compare monetary policy stance across countries
- [ ] Track rate change history over the past 12 months
- [ ] Assess direction of global monetary policy

## When NOT to Use

- [ ] Detailed bond market analysis — use other tools
- [ ] Forward rate expectations / futures pricing
- [ ] Emerging market central banks not covered

## Setup

Install dependency: `pip install requests`

Uses FRED public CSV endpoint (no API key required).

## Usage/Commands

```bash
python {skill_path}/central_bank_watch.py [options]
```

| Option | Description |
|--------|-------------|
| `--bank fed\|ecb\|boj\|boe\|pboc\|all` | Which bank(s) to show (default: `all`) |
| `--format text\|json` | Output format (default: `text`) |

## Data Sources

- **Fed** — FEDFUNDS (FRED)
- **ECB** — ECBDFR (FRED)
- **BOJ** — IRSTCB01JPM156N (FRED, approximate)
- **BOE** — BOERUKM (FRED)
- **PBOC** — Hardcoded LPR fallback (updated manually)

## Notes

- Shows current rate, last change direction, and 12-month history
- Rate history is monthly resolution
- Output cached to `~/.value_claw/central_bank_watch/`
