#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "ib_insync>=0.9.86",
# ]
# ///
"""
Interactive Brokers order management.

Usage:
    uv run ib_orders.py list
    uv run ib_orders.py place --symbol AAPL --action BUY --quantity 100 --type MKT
    uv run ib_orders.py place --symbol AAPL --action BUY --quantity 100 --type LMT --price 150.00
    uv run ib_orders.py cancel --order-id 12345
    uv run ib_orders.py trades
"""

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ib_helpers import add_connection_args, connect_ib, fmt_currency, fmt_number, now_str, print_table


def cmd_list(args):
    """List all open orders."""
    with connect_ib(args, readonly=True) as ib:
        trades = ib.openTrades()
        if not trades:
            print("No open orders.")
            return

        print(f"=== Open Orders ({now_str()}) ===\n")

        headers = ["Order ID", "Symbol", "Type", "Action", "Qty", "Order Type", "Price", "Status"]
        rows = []
        for trade in trades:
            c = trade.contract
            o = trade.order
            s = trade.orderStatus
            price = o.lmtPrice if o.orderType == "LMT" else (o.auxPrice if o.orderType in ("STP", "STP LMT") else "MKT")
            rows.append([
                str(o.orderId),
                c.localSymbol or c.symbol,
                c.secType,
                o.action,
                fmt_number(o.totalQuantity),
                o.orderType,
                fmt_currency(price) if isinstance(price, (int, float)) else str(price),
                s.status,
            ])

        print_table(headers, rows)


def cmd_place(args):
    """Place a new order."""
    from ib_insync import Forex, Future, LimitOrder, MarketOrder, Option, Stock, StopLimitOrder, StopOrder

    contract_builders = {
        "STK": lambda a: Stock(a.symbol, a.exchange or "SMART", a.currency),
        "OPT": lambda a: Option(a.symbol, a.expiry, float(a.strike), a.right, a.exchange or "SMART", currency=a.currency),
        "FUT": lambda a: Future(a.symbol, a.expiry, a.exchange or "SMART", currency=a.currency),
        "CASH": lambda a: Forex(a.symbol[:3], a.symbol[3:] if len(a.symbol) == 6 else "USD"),
    }

    sec_type = args.sec_type.upper()
    if sec_type not in contract_builders:
        print(f"Error: unsupported security type '{sec_type}'. Use: STK, OPT, FUT, CASH", file=sys.stderr)
        sys.exit(1)

    try:
        contract = contract_builders[sec_type](args)
    except Exception as e:
        print(f"Error building contract: {e}", file=sys.stderr)
        sys.exit(1)

    order_type = args.type.upper()
    action = args.action.upper()
    qty = args.quantity

    order_builders = {
        "MKT": lambda: MarketOrder(action, qty),
        "LMT": lambda: LimitOrder(action, qty, args.price),
        "STP": lambda: StopOrder(action, qty, args.stop_price),
        "STP_LMT": lambda: StopLimitOrder(action, qty, args.price, args.stop_price),
    }

    if order_type not in order_builders:
        print(f"Error: unsupported order type '{order_type}'. Use: MKT, LMT, STP, STP_LMT", file=sys.stderr)
        sys.exit(1)

    if order_type == "LMT" and args.price is None:
        print("Error: --price required for LMT orders", file=sys.stderr)
        sys.exit(1)
    if order_type in ("STP", "STP_LMT") and args.stop_price is None:
        print("Error: --stop-price required for STP/STP_LMT orders", file=sys.stderr)
        sys.exit(1)

    order = order_builders[order_type]()

    if args.tif:
        order.tif = args.tif.upper()
    if args.outside_rth:
        order.outsideRth = True

    print("=" * 50)
    print("ORDER PREVIEW")
    print("=" * 50)
    print(f"  Action:     {action}")
    print(f"  Symbol:     {args.symbol}")
    print(f"  SecType:    {sec_type}")
    print(f"  Quantity:   {qty}")
    print(f"  Order Type: {order_type}")
    if args.price:
        print(f"  Limit:      {fmt_currency(args.price, args.currency)}")
    if args.stop_price:
        print(f"  Stop:       {fmt_currency(args.stop_price, args.currency)}")
    if args.tif:
        print(f"  TIF:        {args.tif.upper()}")
    if args.outside_rth:
        print("  Outside RTH: Yes")
    print("=" * 50)

    if not args.confirm:
        print("\nDry run — order NOT submitted. Add --confirm to execute.")
        return

    with connect_ib(args) as ib:
        qualified = ib.qualifyContracts(contract)
        if not qualified:
            print(f"Error: could not qualify contract for {args.symbol}", file=sys.stderr)
            sys.exit(1)

        trade = ib.placeOrder(qualified[0], order)
        ib.sleep(2)

        status = trade.orderStatus
        print("\nOrder submitted!")
        print(f"  Order ID:  {trade.order.orderId}")
        print(f"  Status:    {status.status}")
        if status.filled:
            print(f"  Filled:    {fmt_number(status.filled)} @ {fmt_currency(status.avgFillPrice, args.currency)}")
        if status.remaining:
            print(f"  Remaining: {fmt_number(status.remaining)}")


def cmd_cancel(args):
    """Cancel an order by order ID."""
    with connect_ib(args) as ib:
        trades = ib.openTrades()
        target = None
        for trade in trades:
            if str(trade.order.orderId) == str(args.order_id):
                target = trade
                break

        if not target:
            print(f"Error: no open order found with ID {args.order_id}", file=sys.stderr)
            print("Open order IDs:", ", ".join(str(t.order.orderId) for t in trades) or "(none)")
            sys.exit(1)

        c = target.contract
        o = target.order
        print(f"Cancelling order {o.orderId}: {o.action} {fmt_number(o.totalQuantity)} {c.symbol} ({o.orderType})")

        ib.cancelOrder(o)
        ib.sleep(2)

        print(f"Cancel request sent. Status: {target.orderStatus.status}")


def cmd_trades(args):
    """Show all trades (filled orders) for the session."""
    with connect_ib(args, readonly=True) as ib:
        trades = ib.trades()
        if not trades:
            print("No trades in this session.")
            return

        print(f"=== Trades ({now_str()}) ===\n")

        headers = ["Order ID", "Symbol", "Action", "Qty", "Filled", "Avg Price", "Status", "Time"]
        rows = []
        for trade in trades:
            c = trade.contract
            o = trade.order
            s = trade.orderStatus

            fill_time = ""
            if trade.fills:
                fill_time = str(trade.fills[-1].time)[:19]

            rows.append([
                str(o.orderId),
                c.localSymbol or c.symbol,
                o.action,
                fmt_number(o.totalQuantity),
                fmt_number(s.filled),
                fmt_currency(s.avgFillPrice, c.currency) if s.avgFillPrice else "—",
                s.status,
                fill_time,
            ])

        print_table(headers, rows)


def main():
    parser = argparse.ArgumentParser(description="IB Order Management")
    add_connection_args(parser)

    sub = parser.add_subparsers(dest="command", help="Command to run")

    sub.add_parser("list", help="List all open orders")
    sub.add_parser("trades", help="Show all trades (filled) for the session")

    p_place = sub.add_parser("place", help="Place a new order")
    p_place.add_argument("--symbol", required=True, help="Ticker symbol (e.g. AAPL, EURUSD)")
    p_place.add_argument("--action", required=True, choices=["BUY", "SELL"], help="BUY or SELL")
    p_place.add_argument("--quantity", type=float, required=True, help="Order quantity")
    p_place.add_argument("--type", default="MKT", choices=["MKT", "LMT", "STP", "STP_LMT"], help="Order type")
    p_place.add_argument("--price", type=float, help="Limit price (required for LMT, STP_LMT)")
    p_place.add_argument("--stop-price", type=float, help="Stop price (required for STP, STP_LMT)")
    p_place.add_argument("--sec-type", default="STK", choices=["STK", "OPT", "FUT", "CASH"], help="Security type")
    p_place.add_argument("--exchange", default="SMART", help="Exchange (default: SMART)")
    p_place.add_argument("--currency", default="USD", help="Currency (default: USD)")
    p_place.add_argument("--expiry", help="Expiry date for OPT/FUT (YYYYMMDD)")
    p_place.add_argument("--strike", type=float, help="Strike price for OPT")
    p_place.add_argument("--right", choices=["C", "P"], help="C(all) or P(ut) for OPT")
    p_place.add_argument("--tif", choices=["DAY", "GTC", "IOC", "GTD"], help="Time in force")
    p_place.add_argument("--outside-rth", action="store_true", help="Allow execution outside regular trading hours")
    p_place.add_argument("--confirm", action="store_true", help="Actually submit the order (without this flag, dry run only)")

    p_cancel = sub.add_parser("cancel", help="Cancel an open order")
    p_cancel.add_argument("--order-id", required=True, help="Order ID to cancel")

    args = parser.parse_args()

    commands = {
        "list": cmd_list,
        "place": cmd_place,
        "cancel": cmd_cancel,
        "trades": cmd_trades,
    }

    if not args.command:
        parser.print_help()
        sys.exit(1)

    commands[args.command](args)


if __name__ == "__main__":
    main()
