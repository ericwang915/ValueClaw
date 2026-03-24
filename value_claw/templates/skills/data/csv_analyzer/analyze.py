#!/usr/bin/env python3
"""Analyze CSV/Excel files with pandas."""

import argparse
import json
import sys

try:
    import pandas as pd
except ImportError:
    print("Error: pandas not installed.  Run: pip install pandas openpyxl",
          file=sys.stderr)
    sys.exit(1)


def load_data(path: str, columns: str | None = None) -> pd.DataFrame:
    ext = path.rsplit(".", 1)[-1].lower()
    if ext in ("xls", "xlsx"):
        df = pd.read_excel(path)
    elif ext == "tsv":
        df = pd.read_csv(path, sep="\t")
    else:
        df = pd.read_csv(path)
    if columns:
        cols = [c.strip() for c in columns.split(",")]
        df = df[cols]
    return df


def cmd_info(df: pd.DataFrame, as_json: bool) -> None:
    info = {
        "shape": list(df.shape),
        "columns": [
            {"name": c, "dtype": str(df[c].dtype), "missing": int(df[c].isna().sum())}
            for c in df.columns
        ],
        "memoryMB": round(df.memory_usage(deep=True).sum() / 1e6, 2),
    }
    if as_json:
        print(json.dumps(info, indent=2))
    else:
        print(f"Shape: {df.shape[0]} rows x {df.shape[1]} columns")
        print(f"Memory: {info['memoryMB']} MB\n")
        print(f"{'Column':<30} {'Type':<15} {'Missing'}")
        print("-" * 55)
        for c in info["columns"]:
            print(f"{c['name']:<30} {c['dtype']:<15} {c['missing']}")


def cmd_head(df: pd.DataFrame, rows: int, as_json: bool) -> None:
    subset = df.head(rows)
    if as_json:
        print(subset.to_json(orient="records", indent=2, force_ascii=False))
    else:
        print(subset.to_string(index=False))


def cmd_stats(df: pd.DataFrame, as_json: bool) -> None:
    numeric = df.select_dtypes(include="number")
    if numeric.empty:
        print("No numeric columns found.")
        return
    desc = numeric.describe()
    if as_json:
        print(desc.to_json(indent=2))
    else:
        print(desc.to_string())


def cmd_query(df: pd.DataFrame, expr: str, rows: int, as_json: bool) -> None:
    result = df.query(expr)
    subset = result.head(rows)
    print(f"Matched {len(result)} rows (showing first {min(rows, len(result))}):\n")
    if as_json:
        print(subset.to_json(orient="records", indent=2, force_ascii=False))
    else:
        print(subset.to_string(index=False))


def cmd_groupby(df: pd.DataFrame, col: str, agg: str, as_json: bool) -> None:
    numeric = df.select_dtypes(include="number").columns.tolist()
    if col in numeric:
        numeric.remove(col)
    if not numeric:
        print("No numeric columns to aggregate.")
        return
    result = df.groupby(col)[numeric].agg(agg).reset_index()
    if as_json:
        print(result.to_json(orient="records", indent=2, force_ascii=False))
    else:
        print(result.to_string(index=False))


def main():
    parser = argparse.ArgumentParser(description="Analyze CSV/Excel files.")
    parser.add_argument("path", help="Data file path (.csv, .tsv, .xlsx)")
    parser.add_argument("command", nargs="?", default="info",
                        choices=["info", "head", "stats", "query", "groupby", "columns"])
    parser.add_argument("--rows", type=int, default=10)
    parser.add_argument("--query", dest="expr", default=None)
    parser.add_argument("--groupby", default=None)
    parser.add_argument("--agg", default="mean",
                        choices=["mean", "sum", "count", "min", "max"])
    parser.add_argument("--columns", default=None)
    parser.add_argument("--format", choices=["text", "json"], default="text")
    args = parser.parse_args()

    try:
        df = load_data(args.path, args.columns)
    except Exception as exc:
        print(f"Error loading {args.path}: {exc}", file=sys.stderr)
        sys.exit(1)

    as_json = args.format == "json"

    if args.command == "info":
        cmd_info(df, as_json)
    elif args.command == "head":
        cmd_head(df, args.rows, as_json)
    elif args.command == "stats":
        cmd_stats(df, as_json)
    elif args.command == "query":
        if not args.expr:
            print("Error: --query expression required.", file=sys.stderr)
            sys.exit(1)
        cmd_query(df, args.expr, args.rows, as_json)
    elif args.command == "groupby":
        if not args.groupby:
            print("Error: --groupby column required.", file=sys.stderr)
            sys.exit(1)
        cmd_groupby(df, args.groupby, args.agg, as_json)
    elif args.command == "columns":
        for c in df.columns:
            print(f"  {c}  ({df[c].dtype})")


if __name__ == "__main__":
    main()
