#!/usr/bin/env python3
"""Make arbitrary HTTP requests to any API endpoint."""

import argparse
import json
import sys

try:
    import requests
except ImportError:
    print("Error: requests not installed.  Run: pip install requests", file=sys.stderr)
    sys.exit(1)


def http_request(
    url: str,
    method: str = "GET",
    data: str | None = None,
    headers: dict | None = None,
    timeout: int = 30,
) -> dict:
    headers = headers or {}
    body = None
    if data:
        try:
            body = json.loads(data)
            headers.setdefault("Content-Type", "application/json")
        except json.JSONDecodeError:
            body = data

    resp = requests.request(
        method=method.upper(),
        url=url,
        json=body if isinstance(body, (dict, list)) else None,
        data=body if isinstance(body, str) else None,
        headers=headers,
        timeout=timeout,
    )

    try:
        resp_body = resp.json()
    except Exception:
        resp_body = resp.text[:5000]

    return {
        "status": resp.status_code,
        "headers": dict(resp.headers),
        "body": resp_body,
    }


def main():
    parser = argparse.ArgumentParser(description="Make HTTP requests.")
    parser.add_argument("url", help="Request URL")
    parser.add_argument("--method", default="GET", choices=["GET", "POST", "PUT", "DELETE", "PATCH"])
    parser.add_argument("--data", default=None, help="Request body (JSON string)")
    parser.add_argument("--header", action="append", default=[], help="Header in 'Name: Value' format")
    parser.add_argument("--timeout", type=int, default=30)
    parser.add_argument("--format", choices=["text", "json", "headers"], default="text")
    args = parser.parse_args()

    headers = {}
    for h in args.header:
        if ":" in h:
            k, v = h.split(":", 1)
            headers[k.strip()] = v.strip()

    try:
        result = http_request(args.url, args.method, args.data, headers, args.timeout)
    except Exception as exc:
        print(f"Request failed: {exc}", file=sys.stderr)
        sys.exit(1)

    if args.format == "json":
        print(json.dumps(result, indent=2, ensure_ascii=False))
    elif args.format == "headers":
        print(f"Status: {result['status']}")
        for k, v in result["headers"].items():
            print(f"  {k}: {v}")
    else:
        print(f"Status: {result['status']}")
        body = result["body"]
        if isinstance(body, (dict, list)):
            print(json.dumps(body, indent=2, ensure_ascii=False))
        else:
            print(body)


if __name__ == "__main__":
    main()
