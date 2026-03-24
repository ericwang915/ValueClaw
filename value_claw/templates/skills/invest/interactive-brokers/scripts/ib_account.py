#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "ib_insync>=0.9.86",
# ]
# ///
"""
Interactive Brokers account information.

Usage:
    uv run ib_account.py summary [--host HOST] [--port PORT]
    uv run ib_account.py positions [--host HOST] [--port PORT]
    uv run ib_account.py portfolio [--host HOST] [--port PORT]
    uv run ib_account.py pnl [--host HOST] [--port PORT]
"""

import argparse
import sys
import os
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ib_helpers import add_connection_args, connect_ib, fmt_currency, fmt_pct, fmt_number, print_table, now_str


def cmd_summary(args):
    """Show account summary: balances, margin, buying power."""
    with connect_ib(args, readonly=True) as ib:
        ib.reqAccountSummary()
        time.sleep(1)

        summary = ib.accountSummary()
        if not summary:
            print("No account summary available.")
            return

        print(f"=== Account Summary ({now_str()}) ===\n")

        key_fields = {
            "NetLiquidation": "Net Liquidation",
            "TotalCashValue": "Total Cash",
            "GrossPositionValue": "Gross Position Value",
            "MaintMarginReq": "Maintenance Margin",
            "AvailableFunds": "Available Funds",
            "BuyingPower": "Buying Power",
            "ExcessLiquidity": "Excess Liquidity",
            "FullInitMarginReq": "Initial Margin",
            "UnrealizedPnL": "Unrealized P&L",
            "RealizedPnL": "Realized P&L",
        }

        accounts = {}
        for item in summary:
            accounts.setdefault(item.account, {})[item.tag] = (item.value, item.currency)

        for acct, fields in accounts.items():
            print(f"Account: {acct}")
            print("-" * 40)
            for tag, label in key_fields.items():
                if tag in fields:
                    val, cur = fields[tag]
                    try:
                        print(f"  {label:<24} {fmt_currency(float(val), cur)}")
                    except (ValueError, TypeError):
                        print(f"  {label:<24} {val}")
            print()

        ib.cancelAccountSummary()


def cmd_positions(args):
    """Show all positions across accounts."""
    with connect_ib(args, readonly=True) as ib:
        positions = ib.positions()
        if not positions:
            print("No open positions.")
            return

        print(f"=== Positions ({now_str()}) ===\n")

        headers = ["Account", "Symbol", "Type", "Exchange", "Quantity", "Avg Cost", "Value"]
        rows = []
        for pos in positions:
            c = pos.contract
            value = pos.position * pos.avgCost
            rows.append([
                pos.account,
                c.localSymbol or c.symbol,
                c.secType,
                c.exchange or c.primaryExchange,
                fmt_number(pos.position),
                fmt_currency(pos.avgCost, c.currency),
                fmt_currency(value, c.currency),
            ])

        print_table(headers, rows)
        print(f"\nTotal positions: {len(positions)}")


def cmd_portfolio(args):
    """Show portfolio with market values and P&L."""
    with connect_ib(args, readonly=True) as ib:
        ib.reqAccountUpdates(subscribe=True, account=args.account or "")
        time.sleep(2)

        portfolio = ib.portfolio()
        if not portfolio:
            print("No portfolio items. (Try specifying --account YOUR_ACCOUNT_ID)")
            return

        print(f"=== Portfolio ({now_str()}) ===\n")

        headers = ["Symbol", "Type", "Qty", "Mkt Price", "Mkt Value", "Avg Cost", "Unrealized P&L", "P&L %"]
        rows = []
        total_value = 0
        total_pnl = 0

        for item in portfolio:
            c = item.contract
            pnl_pct = (item.unrealizedPNL / (item.averageCost * item.position) * 100) if item.averageCost and item.position else 0
            total_value += item.marketValue
            total_pnl += item.unrealizedPNL

            rows.append([
                c.localSymbol or c.symbol,
                c.secType,
                fmt_number(item.position),
                fmt_currency(item.marketPrice, c.currency),
                fmt_currency(item.marketValue, c.currency),
                fmt_currency(item.averageCost, c.currency),
                fmt_currency(item.unrealizedPNL, c.currency),
                fmt_pct(pnl_pct),
            ])

        print_table(headers, rows)
        print(f"\nTotal Market Value: {fmt_currency(total_value)}")
        print(f"Total Unrealized P&L: {fmt_currency(total_pnl)}")

        ib.reqAccountUpdates(subscribe=False, account=args.account or "")


def cmd_pnl(args):
    """Show daily P&L."""
    with connect_ib(args, readonly=True) as ib:
        acct = args.account or ""

        pnl_obj = ib.reqPnL(acct)
        time.sleep(2)

        print(f"=== Daily P&L ({now_str()}) ===\n")

        if pnl_obj:
            print(f"  Account:        {acct or '(default)'}")
            print(f"  Daily P&L:      {fmt_currency(pnl_obj.dailyPnL)}")
            print(f"  Unrealized P&L: {fmt_currency(pnl_obj.unrealizedPnL)}")
            print(f"  Realized P&L:   {fmt_currency(pnl_obj.realizedPnL)}")
        else:
            print("No P&L data available.")

        ib.cancelPnL(pnl_obj) if pnl_obj else None


def main():
    parser = argparse.ArgumentParser(description="IB Account Information")
    parser.add_argument("--account", default="", help="Account ID (leave empty for default)")
    add_connection_args(parser)

    sub = parser.add_subparsers(dest="command", help="Command to run")
    sub.add_parser("summary", help="Account summary (balances, margin, buying power)")
    sub.add_parser("positions", help="All open positions")
    sub.add_parser("portfolio", help="Portfolio with market values and P&L")
    sub.add_parser("pnl", help="Daily P&L")

    args = parser.parse_args()

    commands = {
        "summary": cmd_summary,
        "positions": cmd_positions,
        "portfolio": cmd_portfolio,
        "pnl": cmd_pnl,
    }

    if not args.command:
        parser.print_help()
        sys.exit(1)

    commands[args.command](args)


if __name__ == "__main__":
    main()
