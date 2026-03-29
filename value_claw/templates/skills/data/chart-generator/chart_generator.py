#!/usr/bin/env python3
"""Generate publication-quality charts from data or yfinance tickers."""

from __future__ import annotations

import argparse
import datetime
import json
import os
import sys

try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
except ImportError:
    print("Error: matplotlib not installed.  Run: pip install matplotlib", file=sys.stderr)
    sys.exit(1)

try:
    import yfinance as yf
    HAS_YF = True
except ImportError:
    HAS_YF = False

CHART_DIR = os.path.expanduser("~/.value_claw/charts")


def fetch_ticker_data(tickers: list[str], period: str) -> dict[str, dict]:
    """Fetch historical close prices from yfinance."""
    if not HAS_YF:
        return {}
    data = {}
    for sym in tickers:
        hist = yf.Ticker(sym).history(period=period)
        if not hist.empty:
            dates = [d.strftime("%Y-%m-%d") for d in hist.index]
            data[sym.upper()] = {"dates": dates, "values": [round(float(c), 2) for c in hist["Close"]]}
    return data


def _extract_labels_values(data: dict) -> tuple[list, list]:
    """Extract labels/values from dict data for bar/pie charts."""
    if "labels" in data and "values" in data:
        return data["labels"], data["values"]
    labels, values = list(data.keys()), []
    for v in data.values():
        if isinstance(v, dict) and "values" in v:
            values.append(v["values"][-1] if v["values"] else 0)
        elif isinstance(v, (int, float)):
            values.append(v)
        else:
            values.append(0)
    return labels, values


def _save(fig, output: str) -> str:
    fig.tight_layout()
    fig.savefig(output, dpi=150)
    plt.close(fig)
    return output


def chart_line(data: dict, title: str, xlabel: str, ylabel: str, output: str) -> str:
    fig, ax = plt.subplots(figsize=(12, 6))
    for label, series in data.items():
        dates = series.get("dates", list(range(len(series["values"]))))
        step = max(1, len(dates) // 20)
        ax.plot(series["values"], label=label)
        ax.set_xticks(range(0, len(dates), step))
        ax.set_xticklabels([dates[i] for i in range(0, len(dates), step)], rotation=45, fontsize=7)
    ax.set_title(title)
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    if len(data) > 1:
        ax.legend()
    ax.grid(True, alpha=0.3)
    return _save(fig, output)


def chart_bar(data: dict, title: str, xlabel: str, ylabel: str, output: str) -> str:
    fig, ax = plt.subplots(figsize=(10, 6))
    labels, values = _extract_labels_values(data)
    ax.bar(labels, values)
    ax.set_title(title)
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.grid(True, alpha=0.3, axis="y")
    return _save(fig, output)


def chart_pie(data: dict, title: str, output: str) -> str:
    fig, ax = plt.subplots(figsize=(8, 8))
    labels, values = _extract_labels_values(data)
    ax.pie(values, labels=labels, autopct="%1.1f%%", startangle=90)
    ax.set_title(title)
    return _save(fig, output)


def chart_heatmap(data: dict, title: str, output: str) -> str:
    fig, ax = plt.subplots(figsize=(10, 8))
    if isinstance(data, dict) and "matrix" in data:
        matrix = data["matrix"]
        xlabels = data.get("xlabels", [str(i) for i in range(len(matrix[0]))])
        ylabels = data.get("ylabels", [str(i) for i in range(len(matrix))])
    else:
        ylabels = list(data.keys())
        matrix = [v["values"][:len(ylabels)] for v in data.values() if isinstance(v, dict) and "values" in v]
        xlabels = list(range(len(matrix[0]))) if matrix else []
    im = ax.imshow(matrix, aspect="auto", cmap="RdYlGn")
    ax.set_xticks(range(len(xlabels)))
    ax.set_xticklabels(xlabels, rotation=45, fontsize=8)
    ax.set_yticks(range(len(ylabels)))
    ax.set_yticklabels(ylabels, fontsize=8)
    fig.colorbar(im, ax=ax)
    ax.set_title(title)
    return _save(fig, output)


CHART_FN = {"line": chart_line, "bar": chart_bar, "pie": chart_pie, "heatmap": chart_heatmap}


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate charts from data or tickers")
    parser.add_argument("--type", choices=["line", "bar", "pie", "heatmap"], default="line")
    parser.add_argument("--tickers", nargs="+", help="Fetch data from yfinance")
    parser.add_argument("--input", help="JSON input file")
    parser.add_argument("--period", default="1y", help="Data period (1m,3m,6m,1y,5y)")
    parser.add_argument("--title", default="Chart")
    parser.add_argument("--xlabel", default="")
    parser.add_argument("--ylabel", default="")
    parser.add_argument("--format", choices=["text", "json"], default="text")
    args = parser.parse_args()

    os.makedirs(CHART_DIR, exist_ok=True)
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = os.path.join(CHART_DIR, "chart_{}_{}.png".format(args.type, ts))

    if args.tickers:
        data = fetch_ticker_data(args.tickers, args.period)
    elif args.input:
        with open(args.input) as f:
            raw = json.load(f)
        if isinstance(raw, list):
            data = {"labels": [r.get("label", str(i)) for i, r in enumerate(raw)],
                    "values": [r.get("value", 0) for r in raw]}
        else:
            data = raw
    else:
        print("Provide --tickers or --input.", file=sys.stderr)
        sys.exit(1)
    if not data:
        print("No data available.", file=sys.stderr)
        sys.exit(1)

    fn = CHART_FN[args.type]
    if args.type in ("line", "bar"):
        fn(data, args.title, args.xlabel, args.ylabel, output_path)
    else:
        fn(data, args.title, output_path)

    if args.format == "json":
        print(json.dumps({"chart_type": args.type, "output_path": os.path.abspath(output_path)}, indent=2))
    else:
        print("Chart saved: {}".format(os.path.abspath(output_path)))


if __name__ == "__main__":
    main()
