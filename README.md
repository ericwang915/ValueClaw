<p align="center">
  <img src="assets/logo.png" alt="ValueClaw" width="160">
</p>

<h1 align="center">ValueClaw 🦅</h1>

<p align="center">
  <strong>Your Autonomous AI Investment Analyst — Built entirely in Python.</strong><br>
  Market Research · Fundamentals Analysis · Sentiment Tracking · Web Dashboard · Multi-Channel
</p>

<p align="center">
  <a href="https://github.com/ericwang915/ValueClaw/actions/workflows/ci.yml">
    <img src="https://github.com/ericwang915/ValueClaw/actions/workflows/ci.yml/badge.svg" alt="CI">
  </a>
  <a href="https://pypi.org/project/value_claw/">
    <img src="https://img.shields.io/pypi/v/value_claw?color=blue" alt="PyPI">
  </a>
  <img src="https://img.shields.io/pypi/pyversions/value_claw" alt="Python">
  <a href="LICENSE">
    <img src="https://img.shields.io/github/license/ericwang915/ValueClaw" alt="MIT License">
  </a>
  <a href="https://github.com/ericwang915/ValueClaw/stargazers">
    <img src="https://img.shields.io/github/stars/ericwang915/ValueClaw?style=social" alt="Stars">
  </a>
</p>

<p align="center">
  <em>An intelligent, provider-agnostic native AI agent dedicated to deep financial research, SEC filing analysis, and autonomous market monitoring. Surpass human limitations with code-driven investment intelligence.</em>
</p>

---

## 🌟 Why ValueClaw?

While other frameworks offer generic conversational AI, **ValueClaw** is engineered from the ground up to be a **Tier-1 Financial Analyst**. It bridges the gap between massive LLM reasoning capabilities (like DeepSeek, GPT-4, and Claude) and hard quantitative market data. 

- **Data-Driven Objectivity:** Never hallucinates stock prices. ValueClaw pulls real-time data before answering.
- **Provider-Agnostic Engine:** Swap between DeepSeek, Grok, Claude, Gemini, Kimi, and GLM on the fly.
- **Persistent Memory:** Remembers your portfolio preferences, risk tolerance, and historical market contexts.
- **Hybrid RAG Architecture:** Fuses BM25 sparse retrieval with dense embeddings for pinpoint accuracy on massive SEC documents.
- **Always Online:** Runs as a standalone background daemon interacting with you seamlessly via Telegram, Discord, WhatsApp, or its own rich Web Dashboard.

---

## 📈 Investment Capabilities (Deep Dive)

ValueClaw's true power lies in its extensible **Financial Skills Engine**. Out of the box, it is equipped to handle complex quantitative and qualitative research tasks.

### 1. Market Data Mastery
- **`yahoo-finance`**: Instantly pull global stock prices, historical ticks, and major indices.
- **`tushare-finance`**: Deep integration with Chinese A-Shares. Fetch daily quotes, margin trading data, and macroeconomic indicators (PMI, CPI).
- **`akshare_data`**: Access an arsenal of alternative data for futures, options, and foreign exchange markets.

### 2. Corporate Fundamentals
- **`sec_filings`**: Automatically fetch 10-K and 10-Q reports directly from the SEC EDGAR database. The agent reads the raw filings, bypasses PR spin, and extracts critical risk factors and management discussions.
- **`stock_fundamentals`**: Calculates and tracks PE, PB, ROE, EPS, Free Cash Flow, and operating margins to evaluate intrinsic value.

### 3. Quantitative & Technical Analysis
- **`technical_analysis`**: Calculates dynamic indicators including RSI, MACD, Moving Averages (EMA/SMA), and Bollinger Bands to optimize entry/exit points.
- **`market-environment-analysis`**: Assesses macroeconomic trends and broader market sentiment to determine systematic risk levels.

### 4. News & Social Sentiment Engine
- **`finance-news`**: Monitors breaking financial news across global endpoints.
- **`twitter-news`**: Analyzes social media sentiment in real-time to front-run retail trends and viral market movements.

### 5. Strategy & Trading Assistants
- **`trading-coach`**: Acts as your personal quant strategist. Submit a portfolio hypothesis, and the agent will backtest the logic, pointing out historical flaws and risk exposures.
- **`etf-assistant`**: Recommends ETF allocations based on desired thematic exposure (e.g., "Give me a low-volatility semiconductor basket").

---

## 🌐 Web & Deep Research Capabilities

When financial data platforms fall short, ValueClaw takes to the open web.

- **`perplexity_search`**: Connected to the `sonar-pro` model, the agent can synthesize massive geopolitical reports, supply chain disruptions, and macro research dynamically.
- **`brave_search`**: Programmatic, unbiased web searches for the latest unindexed events and press releases.
- **`summarize`**: Feed the agent an earnings call transcript link, and receive a structured, 5-point executive summary in seconds.

---

## 🚀 Quick Start

### 1. Installation
Install the package directly via pip (Requires Python 3.10+):

```bash
pip install value_claw
```

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
*The local Web UI dashboard is now available at `http://localhost:7788`.*

### 4. Chat
Interact with your deployment directly from the terminal or Telegram:

```bash
value_claw chat
```

---

## 🧠 Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                          ValueClaw                              │
├───────────┬────────────┬─────────────┬──────────────────────────┤
│ Interface │ Lifecycle  │ Memory &    │      Core Engine         │
│           │            │ State       │                          │
│ CLI       │ Start      │ Markdown    │ ├─ Hybrid RAG Retrieval  │
│ Web UI  ◄─┤ Stop       │ Local DB    │ ├─ Financial Skills      │
│ Telegram  │ Status     │ Locks       │ ├─ Context Compaction    │
│ Discord   │ Cron Jobs  │ Per-group   │ ├─ Persona Manager       │
├───────────┴────────────┴─────────────┴──────────────────────────┤
│                 LLM Provider Abstraction Layer                  │
│ DeepSeek │ Grok │ Claude │ Gemini │ Kimi │ GLM | OpenAI API     │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🛠️ Configuration

All system properties, API keys, and model preferences are handled natively in `value_claw.json`. See the [`value_claw.example.json`](value_claw.example.json) to manually configure providers like Brave, Perplexity, or Telegram bots.

---

## 🗺️ Roadmap

- [x] Integrate global LLM models (DeepSeek, Grok, Gemini, Claude).
- [x] Multi-Channel Support (Telegram, Discord, Web UI).
- [x] Fully open-source Skills Marketplace integration.
- [ ] **Multi-Agent Debate**: Spawn two agents (a Bull and a Bear) to argue a stock thesis before finalizing a report.
- [ ] **Live Trade Integration**: Direct API hookups for Alpaca and Interactive Brokers paper trading.
- [ ] **PDF/Image Parse**: Native visual parsing for bespoke hedge fund reports and charting images.

---

## 🤝 Contributing

We welcome pull requests! Whether you are building a new financial skill, optimizing the RAG pipeline, or translating documentation—your contributions are highly valued. See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

---

## 📜 License

This project is licensed under the [MIT License](LICENSE).

---

<p align="center">
  <sub>If ValueClaw saves you time or makes you money, consider giving the repo a ⭐</sub>
</p>
