#!/usr/bin/env python3
"""Notion REST API client for value_claw."""
import argparse
import json
import os
import sys

try:
    import requests
except ImportError:
    print("Error: requests is not installed. Run: pip install requests", file=sys.stderr)
    sys.exit(1)

BASE_URL = "https://api.notion.com/v1"
NOTION_VERSION = "2022-06-28"


def _get_token() -> str:
    token = os.environ.get("NOTION_API_KEY", "")
    if token:
        return token
    for path in [os.path.expanduser("~/.value_claw/value_claw.json"), "value_claw.json"]:
        if os.path.isfile(path):
            try:
                with open(path) as f:
                    cfg = json.load(f)
                token = cfg.get("skills", {}).get("notion", {}).get("token", "")
                if token:
                    return token
            except (json.JSONDecodeError, OSError):
                continue
    print("Error: Notion token not configured. Set skills.notion.token in value_claw.json", file=sys.stderr)
    sys.exit(1)


def _headers(token: str) -> dict:
    return {
        "Authorization": f"Bearer {token}",
        "Notion-Version": NOTION_VERSION,
        "Content-Type": "application/json",
    }


def _api(method: str, path: str, token: str, body: dict | None = None) -> dict:
    url = f"{BASE_URL}/{path}"
    resp = getattr(requests, method)(url, headers=_headers(token), json=body, timeout=15)
    resp.raise_for_status()
    return resp.json()


def cmd_search(args, token):
    data = _api("post", "search", token, {"query": args.query})
    for result in data.get("results", []):
        obj_type = result.get("object", "")
        title_parts = []
        if obj_type == "page":
            props = result.get("properties", {})
            for prop in props.values():
                if prop.get("type") == "title":
                    for t in prop.get("title", []):
                        title_parts.append(t.get("plain_text", ""))
        title = " ".join(title_parts) or "(untitled)"
        print(f"[{obj_type}] {title} — {result['id']}")


def cmd_get_page(args, token):
    data = _api("get", f"pages/{args.page_id}", token)
    print(json.dumps(data, indent=2, ensure_ascii=False))


def cmd_get_blocks(args, token):
    data = _api("get", f"blocks/{args.page_id}/children", token)
    for block in data.get("results", []):
        btype = block.get("type", "")
        content = block.get(btype, {})
        texts = []
        for rt in content.get("rich_text", []):
            texts.append(rt.get("plain_text", ""))
        if texts:
            print(f"[{btype}] {''.join(texts)}")


def cmd_create_page(args, token):
    body = {
        "parent": {"database_id": args.database},
        "properties": {
            "Name": {"title": [{"text": {"content": args.title}}]},
        },
    }
    if args.props:
        extra = json.loads(args.props)
        for k, v in extra.items():
            if isinstance(v, str):
                body["properties"][k] = {"select": {"name": v}}
            else:
                body["properties"][k] = v
    data = _api("post", "pages", token, body)
    print(f"Created page: {data['id']}")


def cmd_query_db(args, token):
    body = {}
    if args.filter:
        body["filter"] = json.loads(args.filter)
    data = _api("post", f"databases/{args.database_id}/query", token, body)
    for page in data.get("results", []):
        props = page.get("properties", {})
        title_parts = []
        for prop in props.values():
            if prop.get("type") == "title":
                for t in prop.get("title", []):
                    title_parts.append(t.get("plain_text", ""))
        title = " ".join(title_parts) or "(untitled)"
        print(f"  {title} — {page['id']}")


def cmd_update_page(args, token):
    props = json.loads(args.props)
    formatted = {}
    for k, v in props.items():
        if isinstance(v, str):
            formatted[k] = {"select": {"name": v}}
        else:
            formatted[k] = v
    _api("patch", f"pages/{args.page_id}", token, {"properties": formatted})
    print(f"Updated page: {args.page_id}")


def cmd_append_blocks(args, token):
    body = {
        "children": [{
            "object": "block",
            "type": "paragraph",
            "paragraph": {
                "rich_text": [{"text": {"content": args.text}}]
            },
        }]
    }
    _api("patch", f"blocks/{args.page_id}/children", token, body)
    print(f"Appended block to: {args.page_id}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("search")
    p.add_argument("query")

    p = sub.add_parser("get-page")
    p.add_argument("page_id")

    p = sub.add_parser("get-blocks")
    p.add_argument("page_id")

    p = sub.add_parser("create-page")
    p.add_argument("--database", required=True)
    p.add_argument("--title", required=True)
    p.add_argument("--props", default=None)

    p = sub.add_parser("query-db")
    p.add_argument("database_id")
    p.add_argument("--filter", default=None)

    p = sub.add_parser("update-page")
    p.add_argument("page_id")
    p.add_argument("--props", required=True)

    p = sub.add_parser("append-blocks")
    p.add_argument("page_id")
    p.add_argument("--text", required=True)

    args = parser.parse_args()
    token = _get_token()

    handlers = {
        "search": cmd_search, "get-page": cmd_get_page, "get-blocks": cmd_get_blocks,
        "create-page": cmd_create_page, "query-db": cmd_query_db,
        "update-page": cmd_update_page, "append-blocks": cmd_append_blocks,
    }
    handlers[args.command](args, token)


if __name__ == "__main__":
    main()
