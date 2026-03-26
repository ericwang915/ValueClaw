#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "ib_insync>=0.9.86",
# ]
# ///
"""
Interactive Brokers contract search and details.

Usage:
    uv run ib_contract.py search AAPL
    uv run ib_contract.py details --symbol AAPL --sec-type STK
    uv run ib_contract.py details --symbol AAPL --sec-type OPT --expiry 20260320 --strike 200 --right C
"""

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ib_helpers import add_connection_args, connect_ib, now_str, print_table


def cmd_search(args):
    """Search for contracts matching a pattern."""
    with connect_ib(args, readonly=True) as ib:
        matches = ib.reqMatchingSymbols(args.pattern)
        if not matches:
            print(f"No contracts found matching '{args.pattern}'.")
            return

        print(f"=== Contract Search: '{args.pattern}' ({now_str()}) ===\n")

        headers = ["Symbol", "SecType", "Currency", "Exchange", "Description"]
        rows = []
        for desc in matches:
            c = desc.contract
            derivative_types = ", ".join(desc.derivativeSecTypes) if desc.derivativeSecTypes else ""
            rows.append([
                c.symbol,
                c.secType,
                c.currency,
                c.primaryExchange or c.exchange,
                f"{desc.contract.description or ''} [{derivative_types}]".strip(),
            ])

        print_table(headers, rows)
        print(f"\nFound {len(matches)} matching symbols.")


def cmd_details(args):
    """Get detailed contract information."""
    from ib_insync import Forex, Future, Option, Stock

    sec_type = args.sec_type.upper()

    if sec_type == "STK":
        contract = Stock(args.symbol, args.exchange or "SMART", args.currency)
    elif sec_type == "OPT":
        if not args.expiry or not args.strike or not args.right:
            print("Error: OPT requires --expiry, --strike, and --right", file=sys.stderr)
            sys.exit(1)
        contract = Option(args.symbol, args.expiry, float(args.strike), args.right, args.exchange or "SMART", currency=args.currency)
    elif sec_type == "FUT":
        if not args.expiry:
            print("Error: FUT requires --expiry", file=sys.stderr)
            sys.exit(1)
        contract = Future(args.symbol, args.expiry, args.exchange or "SMART", currency=args.currency)
    elif sec_type == "CASH":
        base = args.symbol[:3]
        quote = args.symbol[3:] if len(args.symbol) == 6 else "USD"
        contract = Forex(base, quote)
    else:
        print(f"Error: unsupported sec type '{sec_type}'", file=sys.stderr)
        sys.exit(1)

    with connect_ib(args, readonly=True) as ib:
        qualified = ib.qualifyContracts(contract)
        if not qualified:
            print(f"Error: could not qualify contract for {args.symbol} ({sec_type})", file=sys.stderr)
            sys.exit(1)

        contract = qualified[0]
        details_list = ib.reqContractDetails(contract)

        if not details_list:
            print(f"No details for {args.symbol}.")
            return

        for det in details_list:
            c = det.contract
            print(f"=== Contract Details ({now_str()}) ===\n")
            print(f"  Symbol:        {c.symbol}")
            print(f"  Local Symbol:  {c.localSymbol}")
            print(f"  SecType:       {c.secType}")
            print(f"  ConId:         {c.conId}")
            print(f"  Exchange:      {c.exchange}")
            print(f"  Primary Exch:  {c.primaryExchange}")
            print(f"  Currency:      {c.currency}")
            print(f"  Multiplier:    {c.multiplier or 'N/A'}")

            if det.longName:
                print(f"  Name:          {det.longName}")
            if det.category:
                print(f"  Category:      {det.category}")
            if det.subcategory:
                print(f"  Subcategory:   {det.subcategory}")
            if det.industry:
                print(f"  Industry:      {det.industry}")

            print(f"\n  Min Tick:      {det.minTick}")
            if det.priceMagnifier:
                print(f"  Price Mag:     {det.priceMagnifier}")

            print(f"  Trading Hours: {det.tradingHours[:80]}..." if det.tradingHours and len(det.tradingHours) > 80 else f"  Trading Hours: {det.tradingHours or 'N/A'}")

            if det.validExchanges:
                exchanges = det.validExchanges.split(",")
                print(f"  Valid Exchanges: {', '.join(exchanges[:10])}")
                if len(exchanges) > 10:
                    print(f"                   ... and {len(exchanges) - 10} more")

            if det.orderTypes:
                print(f"  Order Types:   {det.orderTypes[:100]}")

            if c.secType == "OPT":
                print(f"\n  Strike:        {c.strike}")
                print(f"  Right:         {'Call' if c.right == 'C' else 'Put'}")
                print(f"  Expiry:        {c.lastTradeDateOrContractMonth}")

            print()


def cmd_futures(args):
    """List available futures expirations for a symbol."""
    from ib_insync import Future

    with connect_ib(args, readonly=True) as ib:
        contract = Future(args.symbol, exchange=args.exchange or "SMART", currency=args.currency)
        details_list = ib.reqContractDetails(contract)

        if not details_list:
            print(f"No futures found for {args.symbol}.")
            return

        print(f"=== Futures: {args.symbol} ({now_str()}) ===\n")

        headers = ["Local Symbol", "Expiry", "Exchange", "Multiplier", "Currency"]
        rows = []
        for det in sorted(details_list, key=lambda d: d.contract.lastTradeDateOrContractMonth):
            c = det.contract
            rows.append([
                c.localSymbol,
                c.lastTradeDateOrContractMonth,
                c.exchange,
                c.multiplier or "N/A",
                c.currency,
            ])

        print_table(headers, rows)
        print(f"\nFound {len(details_list)} contracts.")


def main():
    parser = argparse.ArgumentParser(description="IB Contract Search & Details")
    add_connection_args(parser)

    sub = parser.add_subparsers(dest="command", help="Command to run")

    p_search = sub.add_parser("search", help="Search for contracts by keyword")
    p_search.add_argument("pattern", help="Search pattern (symbol or company name)")

    p_details = sub.add_parser("details", help="Get contract details")
    p_details.add_argument("--symbol", required=True, help="Ticker symbol")
    p_details.add_argument("--sec-type", default="STK", choices=["STK", "OPT", "FUT", "CASH"], help="Security type")
    p_details.add_argument("--exchange", default="SMART")
    p_details.add_argument("--currency", default="USD")
    p_details.add_argument("--expiry", help="Expiry for OPT/FUT (YYYYMMDD)")
    p_details.add_argument("--strike", type=float, help="Strike for OPT")
    p_details.add_argument("--right", choices=["C", "P"], help="Call/Put for OPT")

    p_fut = sub.add_parser("futures", help="List available futures expirations")
    p_fut.add_argument("symbol", help="Futures root symbol (e.g. ES, NQ, CL)")
    p_fut.add_argument("--exchange", default="")
    p_fut.add_argument("--currency", default="USD")

    args = parser.parse_args()

    commands = {
        "search": cmd_search,
        "details": cmd_details,
        "futures": cmd_futures,
    }

    if not args.command:
        parser.print_help()
        sys.exit(1)

    commands[args.command](args)


if __name__ == "__main__":
    main()
