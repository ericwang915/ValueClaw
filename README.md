<p align="center">
  <img src="assets/logo.png" alt="ValueClaw" width="160">
</p>

<h1 align="center">ValueClaw</h1>

<p align="center">
  <strong>Autonomous AI Strategy Orchestrator — Built entirely in Python.</strong><br>
  Strategy Management · Deep Research · Trend Monitoring · Multi-Channel · 97 Skills
</p>

<p align="center">
  <a href="https://github.com/ericwang915/ValueClaw/actions/workflows/ci.yml">
    <img src="https://github.com/ericwang915/ValueClaw/actions/workflows/ci.yml/badge.svg" alt="CI">
  </a>
  <img src="https://img.shields.io/badge/python-3.10%2B-blue" alt="Python 3.10+">
  <a href="LICENSE">
    <img src="https://img.shields.io/github/license/ericwang915/ValueClaw" alt="MIT License">
  </a>
  <a href="https://github.com/ericwang915/ValueClaw/stargazers">
    <img src="https://img.shields.io/github/stars/ericwang915/ValueClaw?style=social" alt="Stars">
  </a>
</p>

<p align="center">
  <em>A world-class AI strategy orchestrator for deep financial research, autonomous market monitoring, and multi-channel communication. Modeled after the investment discipline of Buffett, Dalio, Soros, and Lynch.</em>
</p>

> **ValueClaw is a research & strategy management tool — it does NOT execute real trades or connect to brokerages. See [full disclaimer](#%EF%B8%8F-disclaimer).**

---

## Why ValueClaw?

While other frameworks offer generic conversational AI, **ValueClaw** is engineered from the ground up as a **Strategy Orchestrator** — managing autonomous trading strategies, monitoring market conditions, and coordinating **97 specialized skills across 17 categories** through a token-efficient progressive discovery system.

- **Strategy Orchestrator:** Start, stop, switch, and monitor autonomous trading strategies — not individual trades.
- **Provider-Agnostic Engine:** Swap between Claude (API + OAuth), DeepSeek, Grok, Gemini, Kimi, and GLM — with automatic failover.
- **Configurable LLM Fallback:** Define a primary + fallback provider in config — seamless switch when the primary hits rate limits or quota.
- **Deep Analysis Pipeline:** Adversarial Bull vs Bear research with 5-level conviction ratings, position sizing, and stop-loss strategies.
- **Investment Memory:** Records decisions, reviews accuracy, and learns from past calls to reduce bias over time.
- **Persistent Memory:** Remembers risk tolerance, strategy decisions, and market context across sessions.
- **Hybrid RAG Architecture:** Fuses BM25 sparse retrieval with dense embeddings for pinpoint accuracy on SEC documents.
- **Token-Efficient Skill Discovery:** Two-stage category→skill loading with hot-skill tracking — reduces catalog overhead by ~82%.
- **Multi-Channel:** Telegram (DM + group @mention), Discord, Web Chat — always online as a background daemon.

---

## Skill Categories

ValueClaw ships with **97 specialized skills** across **17 categories**, loaded on-demand through a progressive two-stage discovery system.

| Category | Skills | Key Capabilities |
|----------|--------|-----------------|
| **Equity Analysis** | 9 | `deep-analysis`, `stock_fundamentals`, `technical_analysis`, `trend-monitoring`, `yahoo-finance`, `trading-coach` |
| **Market Intelligence** | 8 | `earnings-tracker`, `sec_filings`, `market-sentiment`, `finance-news`, `twitter-news`, `ipo-tracker`, `ma-deals` |
| **Portfolio Signals** | 9 | `risk-analytics`, `insider-tracker`, `institutional-holdings`, `congress-trades`, `dividend-tracker`, `sector-rotation`, `short-interest` |
| **Multi-Asset** | 9 | `bond-analysis`, `crypto-onchain`, `etf-assistant`, `fx-analysis`, `options-flow`, `interactive-brokers`, `yield-curve` |
| **Investment Frameworks** | 6 | `buffett-value`, `dalio-allweather`, `lynch-garp`, `soros-macro`, `marks-cycles`, `arkwood-fiu` |
| **Macro Economics** | 3 | `macro-dashboard`, `central-bank-watch`, `global-liquidity` |
| **Quant & Backtesting** | 4 | `backtester`, `stock-screener`, `factor-analysis`, `correlation-matrix` |
| **China Market** | 3 | `a-stock-analysis`, `akshare_data`, `tushare-finance` |
| **Commodities** | 2 | `commodity-analysis`, `commodity-tracker` |
| **Data & Utilities** | 10 | `csv_analyzer`, `excel-export`, `chart-generator`, `finance`, `news`, `weather`, `alert-monitor`, `translator` |
| **PDF Tools** | 6 | `pdf_reader`, `pdf_writer`, `pdf_merge`, `pdf_split`, `pdf_convert`, `pdf_protect` |
| **Web & Research** | 4 | `tavily`, `brave_search`, `perplexity_search`, `summarize` |
| **Communication** | 3 | `email`, `slack`, `twitter-post` |
| **Productivity** | 5 | `notion`, `obsidian`, `trello`, `n8n`, `workspace` |
| **Media** | 3 | `image_gen`, `tts`, `spotify` |
| **Developer** | 3 | `code_runner`, `github`, `http_request` |
| **System** | 10 | `investment-memory`, `skill_creator`, `model_usage`, `session_logs`, `change_persona`, `onboarding` |

### Strategy Orchestration (Core)
The agent manages **autonomous trading strategies** rather than individual trades:
- `strategy_create` / `strategy_start` / `strategy_stop` / `strategy_switch`
- Three strategy types: **prompt** (LLM template), **script** (Python), **n8n** (workflow)
- Approval mode for manual review before execution
- Scheduled via Prefect cron with full lifecycle management

### Deep Analysis Pipeline
The `deep-analysis` skill runs an adversarial research pipeline:
1. **Parallel Data Collection** — fundamentals, technicals, news, sentiment simultaneously
2. **Bull Case** — strongest arguments for the investment
3. **Bear Case** — strongest arguments against
4. **Risk Assessment** — position sizing (volatility-adjusted + Kelly Criterion), ATR stop-loss, risk/reward ratio
5. **Final Verdict** — 5-level conviction rating (Strong Buy → Strong Sell)
6. **Memory** — stores analysis for future reference and accuracy tracking

### Trend Monitoring
The `trend-monitoring` skill generates professional candlestick charts with Bollinger Bands, SMA, RSI, and MACD — then uses the configured LLM for deep technical analysis, outputting actionable signals with confidence levels.

### Communication
- **`twitter-post`** — Post tweets with image attachments via Twitter API v2
- **Telegram** — DM + group @mention support with whitelist access control
- **Discord** — Webhook-based notifications

---

## Quick Start

### 1. Installation
Install the package directly via pip (Requires Python 3.10+):

```bash
# Core only (minimal dependencies)
pip install valueclaw

# With specific extras
pip install valueclaw[telegram]          # + Telegram bot
pip install valueclaw[web]               # + Web dashboard
pip install valueclaw[telegram,web]      # + both

# Everything (all providers, channels, scheduler, etc.)
pip install valueclaw[all]
```

<details>
<summary>Available extras</summary>

| Extra | What it adds |
|-------|-------------|
| `anthropic` | Claude LLM provider |
| `gemini` | Google Gemini provider |
| `telegram` | Telegram bot channel |
| `discord` | Discord bot channel |
| `web` | FastAPI web dashboard |
| `scheduler` | Prefect cron scheduler |
| `search` | Tavily web search |
| `dense` | Dense embedding retrieval (scikit-learn) |
| `tokens` | Accurate token counting (tiktoken) |
| `all` | Everything above |

</details>

### 2. Setup Wizard
The interactive wizard configures your LLM provider, fallback, API keys, channels, and search services:

```bash
value_claw onboard
```

The wizard supports:
- **10 LLM providers** — DeepSeek, Grok, Claude (API + OAuth), Gemini, Kimi, GLM, OpenAI, and aliases
- **Fallback LLM** — automatic failover when your primary provider hits rate limits
- **Search services** — Tavily, Brave, Perplexity
- **Channels** — Telegram (DM + groups), Discord, WhatsApp
- **Skill tokens** — Twitter API, Tushare, n8n, Interactive Brokers

### 3. Launch
Start ValueClaw as a persistent background daemon:

```bash
value_claw start
```
*The local Web Chat Interface is now available at `http://localhost:7788`.*

### 4. Chat
Interact with your deployment directly from the terminal or Telegram:

```bash
value_claw chat
```

---

## Architecture Overview

```
┌──────────────────────────────────────────────────────────────────────┐
│                           ValueClaw                                  │
├──────────────┬──────────────┬────────────┬───────────────────────────┤
│  Channels    │  Strategies  │  Memory    │     Core Engine           │
│              │              │            │                           │
│  CLI         │  Prompt      │  Markdown  │  ├─ Hybrid RAG Retrieval  │
│  Web Chat    │  Script      │  Per-group │  ├─ 97 Financial Skills   │
│  Telegram*   │  n8n         │  Global    │  ├─ 2-Stage Discovery     │
│  Discord     │  Cron/Prefect│  Indexed   │  ├─ Context Compaction    │
├──────────────┴──────────────┴────────────┴───────────────────────────┤
│               LLM Provider Layer (Primary + Fallback)                │
│  Claude (API+OAuth) │ DeepSeek │ Gemini │ Grok │ Kimi │ GLM │ OpenAI│
└──────────────────────────────────────────────────────────────────────┘
 * Telegram: DM + Group @mention with whitelist access control
```

---

## Skill Discovery (Token-Efficient)

ValueClaw uses a **two-stage progressive discovery** system to minimize LLM token usage:

| Stage | What | When |
|-------|------|------|
| **Stage 1 — Categories** | 17 category names listed in system prompt | Every request |
| **Stage 2 — Skills** | `explore_category(name)` loads skill names + descriptions | On-demand |
| **Stage 3 — Instructions** | `use_skill(name)` loads full SKILL.md | On-demand |
| **Stage 4 — Resources** | Scripts, schemas, reference docs | When skill directs |

**Smart catalog optimization**:
- Tracks which skills you use most frequently (hot skills get expanded descriptions)
- `search_skills(query)` tool lets the LLM find any skill by keyword across all categories
- `explore_category(name)` drills into a specific category without loading all 97 skills
- Result: **~82% token reduction** on the skill catalog (from ~1,900 to ~330 tokens)

---

## LLM Fallback

Configure a fallback provider in `value_claw.json` for automatic failover:

```json
{
  "llm": {
    "provider": "claude",
    "fallback": "deepseek",
    "claude":   { "apiKey": "sk-ant-...", "model": "claude-sonnet-4-6" },
    "deepseek": { "apiKey": "sk-...",     "model": "deepseek-chat" }
  }
}
```

When the primary provider encounters any error (rate limit, auth failure, quota exhaustion), ValueClaw transparently retries the same request on the fallback — no user intervention needed.

---

## Configuration

All system properties, API keys, and model preferences are handled natively in `value_claw.json`. Run `value_claw onboard` for guided setup, or see [`value_claw.example.json`](value_claw.example.json) to manually configure providers, channels, and skill tokens.

---

## Roadmap

- [x] Integrate global LLM models (DeepSeek, Grok, Gemini, Claude API + OAuth).
- [x] Multi-Channel Support (Telegram DM + Group, Discord, Web UI).
- [x] 97 financial skills with progressive two-stage discovery.
- [x] Strategy orchestration engine (prompt / script / n8n).
- [x] Trend monitoring with chart generation and LLM analysis.
- [x] Token-efficient smart catalog (~82% reduction).
- [x] Deep analysis pipeline (Bull/Bear adversarial research).
- [x] Investment memory and decision tracking.
- [x] Configurable LLM fallback with automatic failover.
- [ ] **Multi-Agent Debate**: Bull vs Bear agents argue a thesis before final report.
- [ ] **Live Trade Integration**: Alpaca / Interactive Brokers paper trading APIs.
- [ ] **Visual Parsing**: Native image/PDF parsing for hedge fund reports and charts.

---

## Contributing

We welcome pull requests! Whether you are building a new financial skill, optimizing the RAG pipeline, or translating documentation—your contributions are highly valued. See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

---

## License

This project is licensed under the [MIT License](LICENSE).

---

## Disclaimer

**ValueClaw is a research and strategy management tool only. It does NOT execute real trades or connect to brokerages.**

- Investment analysis, recommendations, and reports are for **informational and educational purposes only** and do not constitute financial advice.
- Always do your own research (DYOR) before making investment decisions. Past performance does not guarantee future results.
- The developers of ValueClaw are not responsible for any financial losses incurred from decisions made based on this tool's output.
- Market data may be delayed or inaccurate. Verify all data with official sources before acting on it.

**By using ValueClaw, you acknowledge that you understand these limitations and assume all risks associated with your investment decisions.**

---

<p align="center">
  <sub>If ValueClaw saves you time or makes you money, consider giving the repo a star.</sub>
</p>
