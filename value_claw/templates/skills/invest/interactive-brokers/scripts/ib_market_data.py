#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "ib_insync>=0.9.86",
#     "pandas>=2.0.0",
# ]
# ///
"""
Interactive Brokers market data.

Usage:
    uv run ib_market_data.py quote AAPL
    uv run ib_market_data.py history AAPL --duration 30D --bar 1hour
    uv run ib_market_data.py chain AAPL
"""

import argparse
import json
import sys
import os
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ib_helpers import add_connection_args, connect_ib, fmt_currency, fmt_pct, fmt_number, print_table, now_str


def _make_contract(args):
    """Build a contract from args."""
    from ib_insync import Stock, Future, Forex

    sec_type = getattr(args, "sec_type", "STK").upper()
    symbol = args.symbol
    exchange = getattr(args, "exchange", "SMART") or "SMART"
    currency = getattr(args, "currency", "USD") or "USD"

    if sec_type == "STK":
        return Stock(symbol, exchange, currency)
    elif sec_type == "FUT":
        return Future(symbol, getattr(args, "expiry", ""), exchange, currency=currency)
    elif sec_type == "CASH":
        return Forex(symbol[:3], symbol[3:] if len(symbol) == 6 else "USD")
    else:
        return Stock(symbol, exchange, currency)


def cmd_quote(args):
    """Get real-time snapshot quote."""
    with connect_ib(args, readonly=True) as ib:
        contract = _make_contract(args)
        qualified = ib.qualifyContracts(contract)
        if not qualified:
            print(f"Error: could not find contract for {args.symbol}", file=sys.stderr)
            sys.exit(1)

        contract = qualified[0]
        ticker = ib.reqMktData(contract, genericTickList="", snapshot=True, regulatorySnapshot=False)
        ib.sleep(3)

        print(f"=== Quote: {contract.localSymbol or contract.symbol} ({now_str()}) ===\n")

        last = ticker.last if ticker.last == ticker.last else ticker.close  # NaN check
        prev_close = ticker.close if ticker.close == ticker.close else None
        change = None
        change_pct = None
        if last and prev_close and last == last and prev_close == prev_close:
            change = last - prev_close
            change_pct = (change / prev_close) * 100 if prev_close else None

        print(f"  Symbol:     {contract.localSymbol or contract.symbol}")
        print(f"  Exchange:   {contract.exchange} / {contract.primaryExchange}")
        print(f"  Currency:   {contract.currency}")
        print()
        print(f"  Last:       {fmt_currency(last, contract.currency) if last == last else 'N/A'}")
        print(f"  Bid:        {fmt_currency(ticker.bid, contract.currency) if ticker.bid == ticker.bid else 'N/A'}")
        print(f"  Ask:        {fmt_currency(ticker.ask, contract.currency) if ticker.ask == ticker.ask else 'N/A'}")
        print(f"  Open:       {fmt_currency(ticker.open, contract.currency) if ticker.open == ticker.open else 'N/A'}")
        print(f"  High:       {fmt_currency(ticker.high, contract.currency) if ticker.high == ticker.high else 'N/A'}")
        print(f"  Low:        {fmt_currency(ticker.low, contract.currency) if ticker.low == ticker.low else 'N/A'}")
        print(f"  Close:      {fmt_currency(prev_close, contract.currency) if prev_close and prev_close == prev_close else 'N/A'}")
        print(f"  Volume:     {fmt_number(ticker.volume) if ticker.volume == ticker.volume else 'N/A'}")
        if change is not None:
            print(f"  Change:     {fmt_currency(change, contract.currency)} ({fmt_pct(change_pct)})")

        ib.cancelMktData(contract)


def cmd_history(args):
    """Get historical price data."""
    with connect_ib(args, readonly=True) as ib:
        contract = _make_contract(args)
        qualified = ib.qualifyContracts(contract)
        if not qualified:
            print(f"Error: could not find contract for {args.symbol}", file=sys.stderr)
            sys.exit(1)

        contract = qualified[0]

        bar_size_map = {
            "1min": "1 min", "5min": "5 mins", "15min": "15 mins", "30min": "30 mins",
            "1hour": "1 hour", "4hour": "4 hours", "1day": "1 day", "1week": "1 week", "1month": "1 month",
        }

        bar_size = bar_size_map.get(args.bar, args.bar)

        bars = ib.reqHistoricalData(
            contract,
            endDateTime="",
            durationStr=args.duration,
            barSizeSetting=bar_size,
            whatToShow=args.data_type,
            useRTH=not args.include_ext,
            formatDate=1,
        )

        if not bars:
            print(f"No historical data for {args.symbol}.")
            return

        print(f"=== Historical Data: {contract.localSymbol or contract.symbol} ({now_str()}) ===")
        print(f"    Duration: {args.duration}, Bar: {bar_size}, Type: {args.data_type}\n")

        if args.output == "json":
            import pandas as pd
            df = ib_insync_util_df(bars)
            print(df.to_json(orient="records", indent=2, date_format="iso"))
            return

        headers = ["Date", "Open", "High", "Low", "Close", "Volume"]
        rows = []
        for bar in bars[-args.limit:]:
            rows.append([
                str(bar.date)[:19],
                fmt_currency(bar.open, contract.currency),
                fmt_currency(bar.high, contract.currency),
                fmt_currency(bar.low, contract.currency),
                fmt_currency(bar.close, contract.currency),
                fmt_number(bar.volume),
            ])

        print_table(headers, rows)

        if len(bars) > args.limit:
            print(f"\n(Showing last {args.limit} of {len(bars)} bars. Use --limit to see more.)")

        first = bars[0]
        last = bars[-1]
        pct = ((last.close - first.open) / first.open * 100) if first.open else 0
        print(f"\nPeriod Return: {first.open} → {last.close} ({fmt_pct(pct)})")


def cmd_chain(args):
    """Get options chain for a symbol."""
    with connect_ib(args, readonly=True) as ib:
        from ib_insync import Stock

        contract = Stock(args.symbol, args.exchange or "SMART", args.currency or "USD")
        qualified = ib.qualifyContracts(contract)
        if not qualified:
            print(f"Error: could not find contract for {args.symbol}", file=sys.stderr)
            sys.exit(1)

        contract = qualified[0]
        chains = ib.reqSecDefOptParams(
            contract.symbol, "", contract.secType, contract.conId,
        )

        if not chains:
            print(f"No options chains found for {args.symbol}.")
            return

        print(f"=== Options Chain: {args.symbol} ({now_str()}) ===\n")

        for chain in chains:
            print(f"Exchange: {chain.exchange}")
            print(f"  Trading Class: {chain.tradingClass}")
            print(f"  Multiplier:    {chain.multiplier}")

            expirations = sorted(chain.expirations)
            if args.max_expiry:
                expirations = [e for e in expirations if e <= args.max_expiry]

            print(f"  Expirations:   {len(expirations)} available")
            for exp in expirations[:8]:
                print(f"    - {exp}")
            if len(expirations) > 8:
                print(f"    ... and {len(expirations) - 8} more")

            strikes = sorted(chain.strikes)
            print(f"  Strikes:       {len(strikes)} ({strikes[0]} - {strikes[-1]})")
            print()

        if args.expiry:
            _show_chain_detail(ib, contract, chains[0], args.expiry, args)


def _show_chain_detail(ib, underlying, chain, expiry, args):
    """Show detailed option quotes for a specific expiry."""
    from ib_insync import Option

    print(f"--- Expiry: {expiry} ---\n")

    strikes = sorted(chain.strikes)
    ticker_data = ib.reqMktData(underlying, genericTickList="", snapshot=True)
    ib.sleep(2)
    spot = ticker_data.last if ticker_data.last == ticker_data.last else ticker_data.close

    if spot and spot == spot:
        near_strikes = [s for s in strikes if abs(s - spot) / spot < 0.15]
    else:
        near_strikes = strikes[:20]

    headers = ["Strike", "Call Bid", "Call Ask", "Call Last", "Put Bid", "Put Ask", "Put Last"]
    rows = []

    for strike in near_strikes:
        call = Option(underlying.symbol, expiry, strike, "C", chain.exchange)
        put = Option(underlying.symbol, expiry, strike, "P", chain.exchange)

        contracts = ib.qualifyContracts(call, put)
        if len(contracts) < 2:
            continue

        call_ticker = ib.reqMktData(contracts[0], snapshot=True)
        put_ticker = ib.reqMktData(contracts[1], snapshot=True)

    ib.sleep(3)

    for strike in near_strikes:
        call = Option(underlying.symbol, expiry, strike, "C", chain.exchange)
        put = Option(underlying.symbol, expiry, strike, "P", chain.exchange)

        try:
            ib.qualifyContracts(call, put)
            ct = ib.reqMktData(call, snapshot=True)
            pt = ib.reqMktData(put, snapshot=True)
            ib.sleep(0.5)

            rows.append([
                fmt_currency(strike),
                fmt_currency(ct.bid) if ct.bid == ct.bid else "—",
                fmt_currency(ct.ask) if ct.ask == ct.ask else "—",
                fmt_currency(ct.last) if ct.last == ct.last else "—",
                fmt_currency(pt.bid) if pt.bid == pt.bid else "—",
                fmt_currency(pt.ask) if pt.ask == pt.ask else "—",
                fmt_currency(pt.last) if pt.last == pt.last else "—",
            ])
        except Exception:
            continue

    if spot and spot == spot:
        print(f"Underlying spot: {fmt_currency(spot)}\n")
    print_table(headers, rows)


def main():
    parser = argparse.ArgumentParser(description="IB Market Data")
    add_connection_args(parser)

    sub = parser.add_subparsers(dest="command", help="Command to run")

    p_quote = sub.add_parser("quote", help="Snapshot quote for a symbol")
    p_quote.add_argument("symbol", help="Ticker symbol")
    p_quote.add_argument("--sec-type", default="STK", choices=["STK", "FUT", "CASH"], help="Security type")
    p_quote.add_argument("--exchange", default="SMART")
    p_quote.add_argument("--currency", default="USD")
    p_quote.add_argument("--expiry", help="Expiry for FUT (YYYYMMDD)")

    p_hist = sub.add_parser("history", help="Historical bars")
    p_hist.add_argument("symbol", help="Ticker symbol")
    p_hist.add_argument("--duration", default="30 D", help="Duration (e.g. '30 D', '6 M', '1 Y')")
    p_hist.add_argument("--bar", default="1day", help="Bar size: 1min, 5min, 15min, 30min, 1hour, 4hour, 1day, 1week, 1month")
    p_hist.add_argument("--data-type", default="TRADES", choices=["TRADES", "MIDPOINT", "BID", "ASK", "ADJUSTED_LAST"], help="Data type")
    p_hist.add_argument("--include-ext", action="store_true", help="Include extended hours data")
    p_hist.add_argument("--limit", type=int, default=50, help="Max bars to display (default: 50)")
    p_hist.add_argument("--output", choices=["text", "json"], default="text")
    p_hist.add_argument("--sec-type", default="STK", choices=["STK", "FUT", "CASH"])
    p_hist.add_argument("--exchange", default="SMART")
    p_hist.add_argument("--currency", default="USD")
    p_hist.add_argument("--expiry", help="Expiry for FUT (YYYYMMDD)")

    p_chain = sub.add_parser("chain", help="Options chain")
    p_chain.add_argument("symbol", help="Underlying symbol")
    p_chain.add_argument("--expiry", help="Show detailed quotes for this expiry (YYYYMMDD)")
    p_chain.add_argument("--max-expiry", help="Filter expirations up to this date (YYYYMMDD)")
    p_chain.add_argument("--exchange", default="SMART")
    p_chain.add_argument("--currency", default="USD")

    args = parser.parse_args()

    commands = {
        "quote": cmd_quote,
        "history": cmd_history,
        "chain": cmd_chain,
    }

    if not args.command:
        parser.print_help()
        sys.exit(1)

    commands[args.command](args)


if __name__ == "__main__":
    main()
