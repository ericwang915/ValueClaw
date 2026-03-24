---
name: finance
description: "Fetch stock quotes, crypto prices, forex rates, and financial data via Yahoo Finance. Use when: user asks about stock price, market data, company ticker, cryptocurrency price, or forex exchange rates. NOT for: options/futures data, fundamental analysis, or real-time tick-by-tick data."
dependencies: yfinance
metadata:
  emoji: "📈"
---

# Finance Skill

Fetch real-time financial data for stocks, crypto, and forex using Yahoo Finance (yfinance).

## When to Use

✅ **USE this skill when:**
- "What's Tesla's stock price?"
- "Compare AAPL and MSFT"
- "Show Bitcoin price"
- "EUR/USD exchange rate"
- "How is [company] stock doing?"
- User asks about stock, crypto, or forex prices

## When NOT to Use

❌ **DON'T use this skill when:**
- Options or futures data → use specialized financial APIs
- Fundamental analysis (P/E, ratios, financials) → use dedicated analytics tools
- Real-time tick-by-tick data → use professional trading feeds

## Usage/Commands

```bash
python {skill_path}/fetch_quote.py SYMBOL [SYMBOL2 ...]
```

Options:
- `--format json` — output as JSON (default: human-readable text)
- `--history 5d` — include price history (1d, 5d, 1mo, 3mo, 6mo, 1y, 5y, max)

### Examples

- "What's Tesla's stock price?" → `python {skill_path}/fetch_quote.py TSLA`
- "Compare AAPL and MSFT" → `python {skill_path}/fetch_quote.py AAPL MSFT`
- "Show Bitcoin price" → `python {skill_path}/fetch_quote.py BTC-USD`
- "EUR/USD exchange rate" → `python {skill_path}/fetch_quote.py EURUSD=X`

## Notes

- Install dependency: `pip install yfinance`
- No API key needed — Yahoo Finance is free
- Symbols: stocks (e.g., AAPL), crypto (BTC-USD), forex (EURUSD=X)
