#!/usr/bin/env python3
"""Execute Python code in an isolated subprocess with timeout."""

import argparse
import json
import os
import subprocess
import sys
import tempfile


def run_code(code: str, timeout: int = 30, cwd: str | None = None) -> dict:
    """Run Python code in a subprocess and capture output."""
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".py", delete=False, encoding="utf-8"
    ) as f:
        f.write(code)
        tmp_path = f.name

    try:
        python = sys.executable
        result = subprocess.run(
            [python, tmp_path],
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=cwd,
        )
        return {
            "exitCode": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "timedOut": False,
        }
    except subprocess.TimeoutExpired:
        return {
            "exitCode": -1,
            "stdout": "",
            "stderr": f"Execution timed out after {timeout}s",
            "timedOut": True,
        }
    except Exception as exc:
        return {
            "exitCode": -1,
            "stdout": "",
            "stderr": str(exc),
            "timedOut": False,
        }
    finally:
        os.unlink(tmp_path)


def run_file(path: str, timeout: int = 30) -> dict:
    """Run a Python file in a subprocess."""
    try:
        python = sys.executable
        result = subprocess.run(
            [python, path],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return {
            "exitCode": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "timedOut": False,
        }
    except subprocess.TimeoutExpired:
        return {
            "exitCode": -1,
            "stdout": "",
            "stderr": f"Execution timed out after {timeout}s",
            "timedOut": True,
        }
    except Exception as exc:
        return {
            "exitCode": -1,
            "stdout": "",
            "stderr": str(exc),
            "timedOut": False,
        }


def main():
    parser = argparse.ArgumentParser(description="Execute Python code safely.")
    parser.add_argument("--code", default=None, help="Python code to execute")
    parser.add_argument("--file", default=None, help="Python file to execute")
    parser.add_argument("--timeout", type=int, default=30, help="Timeout in seconds")
    parser.add_argument("--format", choices=["text", "json"], default="text")
    args = parser.parse_args()

    if args.file:
        result = run_file(args.file, timeout=args.timeout)
    elif args.code:
        result = run_code(args.code, timeout=args.timeout)
    elif not sys.stdin.isatty():
        code = sys.stdin.read()
        result = run_code(code, timeout=args.timeout)
    else:
        parser.error("Provide --code, --file, or pipe code via stdin.")
        return

    if args.format == "json":
        print(json.dumps(result, indent=2))
    else:
        if result["stdout"]:
            print(result["stdout"], end="")
        if result["stderr"]:
            print(result["stderr"], end="", file=sys.stderr)
        if result["timedOut"]:
            print(f"\n[Timed out after {args.timeout}s]", file=sys.stderr)
        sys.exit(result["exitCode"])


if __name__ == "__main__":
    main()
