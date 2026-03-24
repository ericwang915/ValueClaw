"""
Shared helpers for Interactive Brokers scripts.

Provides connection management, argument parsing, and output formatting.
Not intended to be run directly — imported by sibling scripts.
"""

from __future__ import annotations

import argparse
import os
import random
import sys
from contextlib import contextmanager
from datetime import datetime

def _load_ib_config() -> dict:
    """Load IB connection defaults from value_claw.json or env vars."""
    defaults = {"host": "127.0.0.1", "port": 7497, "clientId": 1}
    for candidate in [
        os.path.expanduser("~/.value_claw/value_claw.json"),
        os.path.join(os.getcwd(), "value_claw.json"),
    ]:
        if os.path.isfile(candidate):
            try:
                import json
                with open(candidate, "r", encoding="utf-8") as f:
                    cfg = json.load(f)
                ib_cfg = cfg.get("skills", {}).get("interactiveBrokers", {})
                if ib_cfg:
                    defaults["host"] = ib_cfg.get("host", defaults["host"])
                    defaults["port"] = int(ib_cfg.get("port", defaults["port"]))
                    defaults["clientId"] = int(ib_cfg.get("clientId", defaults["clientId"]))
                    break
            except (OSError, ValueError):
                pass
    defaults["host"] = os.environ.get("IB_HOST", defaults["host"])
    defaults["port"] = int(os.environ.get("IB_PORT", str(defaults["port"])))
    return defaults

_IB_DEFAULTS = _load_ib_config()
DEFAULT_HOST = _IB_DEFAULTS["host"]
DEFAULT_PORT = _IB_DEFAULTS["port"]  # 7497=TWS paper, 7496=TWS live, 4002=GW paper, 4001=GW live


def add_connection_args(parser: argparse.ArgumentParser) -> None:
    """Add standard IB connection arguments to an argparse parser."""
    parser.add_argument(
        "--host", default=DEFAULT_HOST,
        help=f"TWS/Gateway host (default: {DEFAULT_HOST})",
    )
    parser.add_argument(
        "--port", type=int, default=DEFAULT_PORT,
        help=f"TWS/Gateway port (default: {DEFAULT_PORT}). "
             "7497=TWS paper, 7496=TWS live, 4002=GW paper, 4001=GW live",
    )
    parser.add_argument(
        "--client-id", type=int, default=None,
        help="Client ID (default: random). Must be unique per connection.",
    )
    parser.add_argument(
        "--timeout", type=int, default=10,
        help="Connection timeout in seconds (default: 10)",
    )


@contextmanager
def connect_ib(args, readonly: bool = False):
    """Context manager: connect to IB, yield the IB instance, disconnect on exit.

    Uses a random clientId by default to avoid conflicts with other sessions.
    """
    try:
        from ib_insync import IB
    except ImportError:
        print("Error: ib_insync is not installed. Install with: pip install ib_insync", file=sys.stderr)
        sys.exit(1)

    client_id = args.client_id if args.client_id is not None else random.randint(100, 9999)
    ib = IB()
    try:
        ib.connect(
            args.host, args.port,
            clientId=client_id,
            readonly=readonly,
            timeout=args.timeout,
        )
    except ConnectionRefusedError:
        print(
            f"Error: Cannot connect to IB on {args.host}:{args.port}.\n"
            "Make sure TWS or IB Gateway is running and API connections are enabled.\n"
            "  TWS: File → Global Configuration → API → Settings → Enable ActiveX and Socket Clients\n"
            "  Gateway: Configure → Settings → API → Settings → Enable ActiveX and Socket Clients",
            file=sys.stderr,
        )
        sys.exit(1)
    except Exception as e:
        print(f"Error connecting to IB: {e}", file=sys.stderr)
        sys.exit(1)

    try:
        yield ib
    finally:
        if ib.isConnected():
            ib.disconnect()


def fmt_currency(value: float | None, currency: str = "USD", decimals: int = 2) -> str:
    if value is None:
        return "N/A"
    if currency == "USD":
        return f"${value:,.{decimals}f}"
    return f"{value:,.{decimals}f} {currency}"


def fmt_pct(value: float | None, decimals: int = 2) -> str:
    if value is None:
        return "N/A"
    sign = "+" if value > 0 else ""
    return f"{sign}{value:.{decimals}f}%"


def fmt_number(value: float | None, decimals: int = 0) -> str:
    if value is None:
        return "N/A"
    return f"{value:,.{decimals}f}"


def print_table(headers: list[str], rows: list[list[str]], min_width: int = 8) -> None:
    """Print a formatted text table."""
    if not rows:
        print("(no data)")
        return

    widths = [max(len(h), min_width) for h in headers]
    for row in rows:
        for i, cell in enumerate(row):
            if i < len(widths):
                widths[i] = max(widths[i], len(str(cell)))

    header_line = " | ".join(h.ljust(w) for h, w in zip(headers, widths))
    sep_line = "-+-".join("-" * w for w in widths)
    print(header_line)
    print(sep_line)
    for row in rows:
        cells = [str(row[i]).ljust(widths[i]) if i < len(row) else "".ljust(widths[i]) for i in range(len(headers))]
        print(" | ".join(cells))


def now_str() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
