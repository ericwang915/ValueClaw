---
name: deep-analysis
description: "Multi-perspective adversarial stock analysis inspired by TradingAgents. Runs a full pipeline: parallel data gathering → Bull/Bear debate → risk assessment (aggressive/conservative/neutral) → final 5-level rating (Buy/Overweight/Hold/Underweight/Sell). Produces institutional-grade reports with contrarian checks built in."
metadata:
  emoji: "🔬"
---

# Deep Analysis — Adversarial Investment Research Pipeline

A structured, multi-perspective analysis framework that forces adversarial thinking
to eliminate single-viewpoint bias. Inspired by real trading firm dynamics where
analysts, researchers, risk managers, and portfolio managers collaborate and debate.

## When to Use

Trigger this skill when the user asks for:
- "深度分析 AAPL" / "deep dive NVDA" / "全面分析一下特斯拉"
- "帮我做一个完整的投资分析" / "give me a full investment report"
- "should I buy TSLA?" (when a thorough answer is appropriate)
- Any request that warrants more than a quick take

## Pipeline (execute ALL steps sequentially)

### Step 1 — Parallel Data Collection

Run these tool calls **in parallel**:

1. `use_skill("stock_fundamentals")` → then run fundamentals report
2. `use_skill("technical_analysis")` → then run technical report
3. `multi_search` with queries:
   - `"{TICKER} latest news {today}"` 
   - `"{TICKER} analyst rating upgrade downgrade {this_month}"`
   - `"{TICKER} earnings outlook risks"`
4. `use_skill("market-sentiment")` → run sentiment dashboard (if relevant)

Collect all 4 reports before proceeding.

### Step 2 — Bull Case (看多论点)

Using ALL data from Step 1, write a **Bull Analyst** argument:

> You are a Bull Analyst. Build a compelling, evidence-based case FOR investing.
> Focus on: growth potential, competitive moats, positive catalysts, strong metrics.
> Cite specific numbers from the reports above. Be persuasive but honest.

Output this section with header `## 🐂 Bull Case`.

### Step 3 — Bear Case (看空论点)

Now write a **Bear Analyst** rebuttal:

> You are a Bear Analyst. Build a compelling case AGAINST investing.
> Focus on: valuation risks, competitive threats, macro headwinds, negative signals.
> Directly counter the Bull Case's strongest arguments with data.

Output this section with header `## 🐻 Bear Case`.

### Step 4 — Risk Assessment (三方风控)

Evaluate the trade from three risk perspectives in a single section:

> **Aggressive View**: Where is the upside being underestimated? What's the moonshot scenario?
> **Conservative View**: What's the worst realistic downside? What could go wrong?
> **Neutral View**: What's the balanced, risk-adjusted take? What position size makes sense?

Output with header `## ⚖️ Risk Assessment`.

Include concrete risk metrics:
- Suggested **position size** (% of portfolio) based on volatility
- **Stop-loss** level (based on ATR or key support)
- **Risk/Reward ratio**

### Step 5 — Final Verdict (最终裁决)

Synthesize everything into a definitive rating:

| Rating | Meaning |
|--------|---------|
| **Buy** | Strong conviction — enter or add to position |
| **Overweight** | Favorable — gradually increase exposure |
| **Hold** | Maintain current position, no action |
| **Underweight** | Reduce exposure, take partial profits |
| **Sell** | Exit position or avoid entry |

Output format:
```
## 🎯 Final Verdict

**Rating: [BUY/OVERWEIGHT/HOLD/UNDERWEIGHT/SELL]**
**Confidence: [HIGH/MEDIUM/LOW]**
**Time Horizon: [short-term / medium-term / long-term]**

**Executive Summary**: 2-3 sentences with the core thesis.

**Action Plan**:
- Entry: ...
- Position Size: ...% of portfolio
- Stop-Loss: $...
- Target: $...
- Key Catalyst to Watch: ...
```

### Step 6 — Memory

After completing the analysis, store the result:
```
remember("{TICKER}_deep_analysis_{date}", "Rating: X, Key thesis: ...")
```

## Rules

- **NEVER skip the Bear Case** — even for beloved stocks, always find real risks
- **Cite specific numbers** — not "strong growth" but "revenue grew 23% YoY to $94.9B"
- **Conflict of interest**: always end with disclaimer
- Use the user's language throughout
- Total output should be comprehensive but structured — aim for quality over length
