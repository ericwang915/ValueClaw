---
name: global-liquidity
description: >
  Global liquidity indicators — M2 money supply, Fed balance sheet, TGA, reverse
  repo, and net liquidity computation. Use when: the user asks about liquidity
  conditions, money supply, the Fed balance sheet, or financial plumbing.
metadata:
  emoji: "💧"
---
# Global Liquidity

## When to Use

- [ ] Check M2 money supply trends
- [ ] Monitor Fed balance sheet size (WALCL)
- [ ] Track Treasury General Account (TGA) and Reverse Repo (RRP)
- [ ] Compute net liquidity = Fed BS - TGA - RRP
- [ ] Assess overall liquidity conditions driving risk assets

## When NOT to Use

- [ ] Detailed fixed-income or bond analysis
- [ ] Individual stock or company research
- [ ] Non-US liquidity data

## Setup

Install dependency: `pip install requests`

Uses FRED public CSV endpoint (no API key required).

## Usage/Commands

```bash
python {skill_path}/global_liquidity.py [options]
```

| Option | Description |
|--------|-------------|
| `--format text\|json` | Output format (default: `text`) |

## Data Sources

All from FRED public CSV:
- **M2SL** — M2 Money Stock
- **WALCL** — Fed Total Assets (balance sheet)
- **WTREGEN** — Treasury General Account
- **RRPONTSYD** — Overnight Reverse Repo

## Notes

- Net liquidity = WALCL - WTREGEN - RRPONTSYD
- 52-week change computed for each series
- Rising net liquidity historically bullish for risk assets
- Output cached to `~/.value_claw/global_liquidity/`
