---
name: interactive-brokers
description: >
  Interactive Brokers trading interface via ib_insync. Supports account info, positions,
  portfolio, real-time quotes, historical data, options chains, contract search, and
  order management (place/cancel/modify). Use when the user wants to trade, check IB
  account, view positions, get IB market data, place orders, or manage their IB portfolio.
  Requires TWS or IB Gateway running with API enabled.
version: 1.0.0
homepage: https://interactivebrokers.com
commands:
  - /ib_account - View account summary, positions, portfolio, P&L
  - /ib_quote - Get real-time quote from IB
  - /ib_history - Historical price data
  - /ib_order - Place, cancel, or list orders
  - /ib_search - Search for contracts
  - /ib_options - View options chain
  - /ib_futures - List futures expirations
---

# Interactive Brokers Trading Interface

Trade stocks, options, futures, and forex through Interactive Brokers using the `ib_insync` Python API.

## Prerequisites

1. **TWS or IB Gateway** must be running on the user's machine
2. **API connections enabled**: TWS → File → Global Configuration → API → Settings → Enable ActiveX and Socket Clients
3. **Python package**: `pip install ib_insync` (installed automatically via `uv run`)

### Connection Ports

| Application      | Paper Trading | Live Trading |
|-----------------|--------------|-------------|
| TWS             | 7497         | 7496        |
| IB Gateway      | 4002         | 4001        |

Default: `127.0.0.1:7497` (TWS paper trading). Override with `--port`.

Environment variables: `IB_HOST`, `IB_PORT` for defaults.

## Account & Portfolio

```bash
# Account summary (balances, margin, buying power)
uv run {skill_path}/scripts/ib_account.py summary

# All positions
uv run {skill_path}/scripts/ib_account.py positions

# Portfolio with market values and unrealized P&L
uv run {skill_path}/scripts/ib_account.py portfolio --account ACCOUNT_ID

# Daily P&L
uv run {skill_path}/scripts/ib_account.py pnl --account ACCOUNT_ID

# Use live trading port
uv run {skill_path}/scripts/ib_account.py summary --port 7496
```

## Market Data

```bash
# Real-time snapshot quote
uv run {skill_path}/scripts/ib_market_data.py quote AAPL
uv run {skill_path}/scripts/ib_market_data.py quote EURUSD --sec-type CASH

# Historical data (default: 30 days, daily bars)
uv run {skill_path}/scripts/ib_market_data.py history AAPL
uv run {skill_path}/scripts/ib_market_data.py history AAPL --duration "6 M" --bar 1day
uv run {skill_path}/scripts/ib_market_data.py history AAPL --duration "5 D" --bar 1hour
uv run {skill_path}/scripts/ib_market_data.py history AAPL --duration "1 D" --bar 5min --include-ext
uv run {skill_path}/scripts/ib_market_data.py history AAPL --output json

# Options chain overview
uv run {skill_path}/scripts/ib_market_data.py chain AAPL

# Options chain with quotes for a specific expiry
uv run {skill_path}/scripts/ib_market_data.py chain AAPL --expiry 20260320
```

### Duration Formats
- `30 S` (seconds), `30 D` (days), `6 M` (months), `1 Y` (year)

### Bar Sizes
- `1min`, `5min`, `15min`, `30min`, `1hour`, `4hour`, `1day`, `1week`, `1month`

## Contract Search

```bash
# Search by symbol or company name
uv run {skill_path}/scripts/ib_contract.py search AAPL
uv run {skill_path}/scripts/ib_contract.py search "Tesla"

# Contract details (stock)
uv run {skill_path}/scripts/ib_contract.py details --symbol AAPL

# Contract details (option)
uv run {skill_path}/scripts/ib_contract.py details --symbol AAPL --sec-type OPT --expiry 20260320 --strike 200 --right C

# Contract details (futures)
uv run {skill_path}/scripts/ib_contract.py details --symbol ES --sec-type FUT --expiry 20260320 --exchange CME

# List all available futures expirations
uv run {skill_path}/scripts/ib_contract.py futures ES --exchange CME
uv run {skill_path}/scripts/ib_contract.py futures CL --exchange NYMEX
```

## Order Management

### CRITICAL SAFETY RULES

1. **ALWAYS show the user a preview before placing any order** — use dry run (without `--confirm`)
2. **ALWAYS ask for explicit confirmation** before adding `--confirm`
3. **Default is paper trading** (port 7497) — for live trading user must explicitly specify `--port 7496`
4. **Double-check** symbol, quantity, action (BUY/SELL), and price with the user

### List Orders

```bash
# Show all open orders
uv run {skill_path}/scripts/ib_orders.py list

# Show all trades (filled orders) this session
uv run {skill_path}/scripts/ib_orders.py trades
```

### Place Orders

```bash
# Market order (DRY RUN — shows preview, does NOT submit)
uv run {skill_path}/scripts/ib_orders.py place --symbol AAPL --action BUY --quantity 100 --type MKT

# Market order (EXECUTE — only after user confirms)
uv run {skill_path}/scripts/ib_orders.py place --symbol AAPL --action BUY --quantity 100 --type MKT --confirm

# Limit order
uv run {skill_path}/scripts/ib_orders.py place --symbol AAPL --action BUY --quantity 100 --type LMT --price 150.00 --confirm

# Stop order
uv run {skill_path}/scripts/ib_orders.py place --symbol AAPL --action SELL --quantity 100 --type STP --stop-price 140.00 --confirm

# Stop-limit order
uv run {skill_path}/scripts/ib_orders.py place --symbol AAPL --action SELL --quantity 50 --type STP_LMT --price 139.50 --stop-price 140.00 --confirm

# GTC (Good Till Cancel)
uv run {skill_path}/scripts/ib_orders.py place --symbol AAPL --action BUY --quantity 100 --type LMT --price 150.00 --tif GTC --confirm

# Allow outside regular trading hours
uv run {skill_path}/scripts/ib_orders.py place --symbol AAPL --action BUY --quantity 10 --type LMT --price 150.00 --outside-rth --confirm
```

### Options Orders

```bash
# Buy a call option
uv run {skill_path}/scripts/ib_orders.py place --symbol AAPL --sec-type OPT --expiry 20260320 --strike 200 --right C --action BUY --quantity 1 --type LMT --price 5.50 --confirm

# Sell a put option
uv run {skill_path}/scripts/ib_orders.py place --symbol AAPL --sec-type OPT --expiry 20260320 --strike 180 --right P --action SELL --quantity 1 --type LMT --price 3.00 --confirm
```

### Futures Orders

```bash
# Buy ES futures
uv run {skill_path}/scripts/ib_orders.py place --symbol ES --sec-type FUT --expiry 20260320 --exchange CME --action BUY --quantity 1 --type MKT --confirm
```

### Forex Orders

```bash
# Buy EUR/USD
uv run {skill_path}/scripts/ib_orders.py place --symbol EURUSD --sec-type CASH --action BUY --quantity 20000 --type MKT --confirm
```

### Cancel Orders

```bash
# Cancel by order ID (get ID from 'list' command)
uv run {skill_path}/scripts/ib_orders.py cancel --order-id 12345
```

## Order Types Reference

| Type     | Flag      | Required Args       | Description                    |
|----------|-----------|--------------------|---------------------------------|
| Market   | `MKT`     | —                  | Execute at best available price |
| Limit    | `LMT`     | `--price`          | Execute at price or better      |
| Stop     | `STP`     | `--stop-price`     | Becomes market when stop hit    |
| StopLimit| `STP_LMT` | `--price --stop-price` | Becomes limit when stop hit |

## Time in Force

| TIF  | Description                          |
|------|--------------------------------------|
| DAY  | Cancel at end of trading day (default)|
| GTC  | Good until cancelled                 |
| IOC  | Immediate or cancel                  |
| GTD  | Good till date                       |

## Security Types

| Type   | Flag   | Description          | Extra Args Needed        |
|--------|--------|---------------------|--------------------------|
| Stock  | `STK`  | Equities            | —                        |
| Option | `OPT`  | Options             | `--expiry --strike --right` |
| Future | `FUT`  | Futures             | `--expiry`               |
| Forex  | `CASH` | Currency pairs      | —                        |

## Connection Options (All Scripts)

All scripts accept these flags:

| Flag          | Default       | Description                        |
|---------------|---------------|------------------------------------|
| `--host`      | `127.0.0.1`   | TWS/Gateway hostname               |
| `--port`      | `7497`        | API port (see port table above)    |
| `--client-id` | random        | Unique client ID per connection    |
| `--timeout`   | `10`          | Connection timeout (seconds)       |

## Workflow Examples

### "查看我的账户"
1. Run `ib_account.py summary`
2. If user wants positions: run `ib_account.py positions`

### "买入100股苹果"
1. Run `ib_orders.py place --symbol AAPL --action BUY --quantity 100 --type MKT` (dry run)
2. Show preview to user, ask for confirmation
3. If confirmed: add `--confirm` and re-run

### "AAPL现在什么价"
1. Run `ib_market_data.py quote AAPL`

### "看看AAPL的期权链"
1. Run `ib_market_data.py chain AAPL`
2. If user wants specific expiry: add `--expiry YYYYMMDD`

### "帮我止损，AAPL跌到140就卖"
1. Run `ib_orders.py place --symbol AAPL --action SELL --quantity N --type STP --stop-price 140` (dry run)
2. Confirm with user
3. Add `--confirm` to execute

## Troubleshooting

| Error | Solution |
|-------|----------|
| `Cannot connect to IB` | Start TWS/Gateway, enable API |
| `Could not qualify contract` | Check symbol, exchange, sec-type |
| `No market data permissions` | Check IB market data subscriptions |
| `Order rejected` | Check account balance, margin, trading permissions |

## Disclaimer

⚠️ **REAL MONEY IS AT RISK.** This skill can place live orders. Always verify orders before confirming. The developer is not responsible for any trading losses. Use paper trading (port 7497) for testing.
