---
name: investment-memory
description: "Trading decision reflection and learning system. Records analysis outcomes, compares predictions vs actual results, generates lessons learned. Builds long-term memory to improve future analysis accuracy."
metadata:
  emoji: "🧠"
---

# Investment Memory — Decision Reflection & Learning

A systematic framework for recording, reviewing, and learning from investment decisions.
Builds institutional memory so the agent improves over time, avoiding repeated mistakes
and reinforcing successful patterns.

## When to Use

Trigger automatically when:
- User asks "回顾之前的分析" / "review my past calls"
- User asks about a stock that was previously analyzed
- User asks "上次分析 AAPL 结果怎么样" / "how did my TSLA call do"
- Periodically for self-reflection

## 1. Recording a Decision

After any stock analysis (especially `deep-analysis`), store the decision:

```
remember("{TICKER}_call_{YYYY-MM-DD}", "Rating: BUY | Price: $185 | Thesis: Strong AI revenue growth | Risks: Valuation stretched | Target: $210 | Stop: $170")
```

Key fields to record:
- **Ticker + Date**: unique identifier
- **Rating**: Buy/Overweight/Hold/Underweight/Sell
- **Price at analysis**: the price when recommendation was made
- **Core thesis**: 1-sentence reason
- **Key risk identified**: the main concern
- **Target & Stop**: expected range

## 2. Reviewing Past Decisions

When the user asks to review, or when re-analyzing a previously covered stock:

1. `recall("{TICKER}")` to find past analyses
2. Use `use_skill("yahoo-finance")` or `multi_search` to get current price
3. Compare:
   - Was the direction correct?
   - Did price reach target or stop-loss?
   - Did the identified risk materialize?
   - Were there surprises we missed?

Output format:
```
## 📋 Decision Review: {TICKER}

| Field | Then | Now |
|-------|------|-----|
| Date | 2026-01-15 | 2026-03-14 |
| Price | $185 | $198 |
| Rating | BUY | — |
| P&L | — | +7.0% |
| Target ($210) | — | Not yet reached |
| Stop ($170) | — | Never triggered |

**Verdict**: ✅ Correct direction. Thesis (AI growth) validated by Q4 earnings beat.
**Lesson**: Entry timing was good; could have set tighter stop at $175.
```

## 3. Generating Reflections

After reviewing, store the lesson:

```
remember("{TICKER}_lesson_{YYYY-MM-DD}", "Called BUY at $185, now $198 (+7%). Thesis validated. Lesson: trust fundamental momentum when backed by earnings beats.")
```

For wrong calls:
```
remember("{TICKER}_lesson_{YYYY-MM-DD}", "Called BUY at $185, dropped to $160 (-13.5%). Missed: rising rates impact on growth valuations. Lesson: weight macro headwinds more heavily for high-PE stocks.")
```

## 4. Applying Lessons to New Analysis

When analyzing any stock, ALWAYS:

1. `recall("{TICKER}")` — check if we analyzed it before
2. `recall("lesson")` — retrieve general lessons learned
3. Incorporate relevant lessons into the current analysis
4. Explicitly reference past mistakes when they apply

Example integration:
> "Note: In a previous analysis of a similar high-PE growth stock (TSLA, Jan 2026),
> I underweighted macro rate risk. Applying that lesson here: current 10Y yield
> at 4.8% creates headwinds for {TICKER}'s 45x forward P/E."

## 5. Periodic Self-Review

When asked to do a full portfolio review or "反思":

1. `recall("call")` — retrieve all past calls
2. Categorize into: ✅ Correct, ❌ Wrong, ⏳ Pending
3. Calculate overall accuracy rate
4. Identify patterns:
   - Which sectors do we analyze best?
   - What type of risk do we most often miss?
   - Do we have a bullish or bearish bias?
5. Store meta-reflection:
```
remember("meta_reflection_{YYYY-MM}", "Win rate: 65% (13/20). Bias: slightly bullish. Blind spots: macro rate sensitivity, China regulatory risk. Strength: tech earnings calls.")
```

## Rules

- Be **brutally honest** in reviews — don't rationalize wrong calls
- Always store **both** the decision AND the lesson
- Lessons should be **specific and actionable**, not generic platitudes
- When a past lesson applies, **explicitly cite it** in the new analysis
