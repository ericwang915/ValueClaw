<p align="center">
  <img src="assets/logo.png" alt="ValueClaw" width="160">
</p>

<h1 align="center">ValueClaw</h1>

<p align="center">
  <strong>Autonomous AI Strategy Orchestrator — Built entirely in Python.</strong><br>
  Strategy Management · Market Research · Trend Monitoring · Multi-Channel · 64+ Skills
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

> **⚠️ ValueClaw is a research & strategy management tool — it does NOT execute real trades or connect to brokerages. See [full disclaimer](#️-disclaimer).**

---

## 🌟 Why ValueClaw?

While other frameworks offer generic conversational AI, **ValueClaw** is engineered from the ground up as a **Strategy Orchestrator** — managing autonomous trading strategies, monitoring market conditions, and coordinating 64+ specialized skills through a token-efficient progressive discovery system.

- **Strategy Orchestrator:** Start, stop, switch, and monitor autonomous trading strategies — not individual trades.
- **Provider-Agnostic Engine:** Swap between DeepSeek, Grok, Claude (API + OAuth), Gemini, Kimi, and GLM on the fly.
- **Persistent Memory:** Remembers risk tolerance, strategy decisions, and market context across sessions.
- **Hybrid RAG Architecture:** Fuses BM25 sparse retrieval with dense embeddings for pinpoint accuracy on SEC documents.
- **Token-Efficient Skill Discovery:** Progressive 3-tier skill loading with hot-skill tracking — reduces catalog overhead by ~82%.
- **Multi-Channel:** Telegram (DM + group @mention), Discord, Web Chat — always online as a background daemon.

---

## 📈 Capabilities

ValueClaw ships with **64+ specialized skills** across 10 categories, loaded on-demand through a progressive discovery system.

### Strategy Orchestration (Core)
The agent manages **autonomous trading strategies** rather than individual trades:
- `strategy_create` / `strategy_start` / `strategy_stop` / `strategy_switch`
- Three strategy types: **prompt** (LLM template), **script** (Python), **n8n** (workflow)
- Approval mode for manual review before execution
- Scheduled via Prefect cron with full lifecycle management

### Market Data & Analysis
| Category | Key Skills |
|----------|-----------|
| **Data** | `yahoo-finance`, `tushare-finance`, `akshare_data`, `finance`, `news` |
| **Fundamentals** | `sec_filings`, `stock_fundamentals`, `earnings-tracker` |
| **Technical** | `technical_analysis`, `technical-analyst`, `trend-monitoring` |
| **Sentiment** | `market-sentiment`, `finance-news`, `twitter-news` |
| **Macro** | `market-environment-analysis`, `economic-calendar` |
| **Options & Risk** | `options-flow`, `risk-analytics`, `insider-tracker`, `institutional-holdings` |
| **Crypto** | `crypto-onchain` |
| **Strategy** | `trading-coach`, `etf-assistant`, `a-stock-analysis` |

### Trend Monitoring
The `trend-monitoring` skill generates professional candlestick charts with Bollinger Bands, SMA, RSI, and MACD — then uses the configured LLM for deep technical analysis, outputting actionable signals with confidence levels.

### Communication
- **`twitter-post`** — Post tweets with image attachments via Twitter API v2
- **Telegram** — DM + group @mention support with whitelist access control
- **Discord** — Webhook-based notifications

---

## 🌐 Web & Research

- **`perplexity_search`** — Sonar-pro model for deep geopolitical and macro research
- **`brave_search`** — Unbiased web search for breaking events and press releases
- **`tavily_search`** — Financial-optimized web search with topic filters
- **`summarize`** — Feed a URL and get a structured executive summary
- **`web-scraper`** — Extract structured data from any webpage

---

## 🚀 Quick Start

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
<summary>📦 Available extras</summary>

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

### 2. Initialization Wizard
Set up your preferred LLM provider (e.g., DeepSeek, OpenAI) and API keys securely:

```bash
value_claw onboard
```

### 3. Launch the Analyst
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

## 🧠 Architecture Overview

```
┌──────────────────────────────────────────────────────────────────────┐
│                           ValueClaw                                  │
├──────────────┬──────────────┬────────────┬───────────────────────────┤
│  Channels    │  Strategies  │  Memory    │     Core Engine           │
│              │              │            │                           │
│  CLI         │  Prompt      │  Markdown  │  ├─ Hybrid RAG Retrieval  │
│  Web Chat    │  Script      │  Per-group │  ├─ 64+ Financial Skills  │
│  Telegram*   │  n8n         │  Global    │  ├─ Smart Skill Discovery │
│  Discord     │  Cron/Prefect│  Indexed   │  ├─ Context Compaction    │
├──────────────┴──────────────┴────────────┴───────────────────────────┤
│                   LLM Provider Abstraction Layer                     │
│  DeepSeek │ Claude (API+OAuth) │ Gemini │ Grok │ Kimi │ GLM │ OpenAI│
└──────────────────────────────────────────────────────────────────────┘
 * Telegram: DM + Group @mention with whitelist access control
```

---

## 🧩 Skill Discovery (Token-Efficient)

ValueClaw uses a **3-tier progressive disclosure** system to minimize LLM token usage:

| Tier | What | When |
|------|------|------|
| **Level 1 — Catalog** | Skill names + short descriptions in system prompt | Every request |
| **Level 2 — Instructions** | Full SKILL.md loaded via `use_skill(name)` | On-demand |
| **Level 3 — Resources** | Scripts, schemas, reference docs | When skill directs |

**Smart catalog optimization** (new in v0.7.2):
- Tracks which skills you use most frequently
- Hot skills (top 12) get expanded descriptions in the catalog
- Cold skills are collapsed to name-only category lists
- `search_skills(query)` tool lets the LLM find any skill by keyword
- Result: **~82% token reduction** on the skill catalog (from ~1,900 to ~330 tokens)

---

## 🛠️ Configuration

All system properties, API keys, and model preferences are handled natively in `value_claw.json`. See the [`value_claw.example.json`](value_claw.example.json) to manually configure providers like Brave, Perplexity, or Telegram bots.

---

## 🗺️ Roadmap

- [x] Integrate global LLM models (DeepSeek, Grok, Gemini, Claude API + OAuth).
- [x] Multi-Channel Support (Telegram DM + Group, Discord, Web UI).
- [x] 64+ financial skills with progressive discovery.
- [x] Strategy orchestration engine (prompt / script / n8n).
- [x] Trend monitoring with chart generation and LLM analysis.
- [x] Token-efficient smart catalog (~82% reduction).
- [ ] **Multi-Agent Debate**: Bull vs Bear agents argue a thesis before final report.
- [ ] **Live Trade Integration**: Alpaca / Interactive Brokers paper trading APIs.
- [ ] **Visual Parsing**: Native image/PDF parsing for hedge fund reports and charts.

---

## 🤝 Contributing

We welcome pull requests! Whether you are building a new financial skill, optimizing the RAG pipeline, or translating documentation—your contributions are highly valued. See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

---

## 📜 License

This project is licensed under the [MIT License](LICENSE).

---

## ⚠️ Disclaimer

**ValueClaw is a research and strategy management tool only. It does NOT execute real trades or connect to brokerages.**

- Investment analysis, recommendations, and reports are for **informational and educational purposes only** and do not constitute financial advice.
- Always do your own research (DYOR) before making investment decisions. Past performance does not guarantee future results.
- The developers of ValueClaw are not responsible for any financial losses incurred from decisions made based on this tool's output.
- Market data may be delayed or inaccurate. Verify all data with official sources before acting on it.

**By using ValueClaw, you acknowledge that you understand these limitations and assume all risks associated with your investment decisions.**

---

<p align="center">
  <sub>If ValueClaw saves you time or makes you money, consider giving the repo a ⭐</sub>
</p>
