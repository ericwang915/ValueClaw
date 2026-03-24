#!/usr/bin/env python3
"""Trello REST API client for value_claw."""
import argparse
import json
import os
import sys

try:
    import requests
except ImportError:
    print("Error: requests is not installed. Run: pip install requests", file=sys.stderr)
    sys.exit(1)

BASE_URL = "https://api.trello.com/1"


def _get_creds() -> tuple[str, str]:
    """Read Trello API key and token from config or environment."""
    api_key = os.environ.get("TRELLO_API_KEY", "")
    token = os.environ.get("TRELLO_TOKEN", "")
    if api_key and token:
        return api_key, token

    for path in [os.path.expanduser("~/.value_claw/value_claw.json"), "value_claw.json"]:
        if os.path.isfile(path):
            try:
                with open(path) as f:
                    cfg = json.load(f)
                trello = cfg.get("skills", {}).get("trello", {})
                api_key = trello.get("apiKey", api_key)
                token = trello.get("token", token)
                if api_key and token:
                    return api_key, token
            except (json.JSONDecodeError, OSError):
                continue

    print("Error: Trello credentials not configured. Set skills.trello.apiKey and skills.trello.token", file=sys.stderr)
    sys.exit(1)


def _get(path: str, key: str, token: str, **params) -> dict | list:
    params.update({"key": key, "token": token})
    resp = requests.get(f"{BASE_URL}/{path}", params=params, timeout=10)
    resp.raise_for_status()
    return resp.json()


def _post(path: str, key: str, token: str, **data) -> dict:
    data.update({"key": key, "token": token})
    resp = requests.post(f"{BASE_URL}/{path}", data=data, timeout=10)
    resp.raise_for_status()
    return resp.json()


def _put(path: str, key: str, token: str, **data) -> dict:
    data.update({"key": key, "token": token})
    resp = requests.put(f"{BASE_URL}/{path}", data=data, timeout=10)
    resp.raise_for_status()
    return resp.json()


def cmd_boards(args, key, token):
    boards = _get("members/me/boards", key, token, fields="name,id,url")
    for b in boards:
        print(f"  {b['name']} — {b['id']}")


def cmd_lists(args, key, token):
    lists = _get(f"boards/{args.board_id}/lists", key, token)
    for lst in lists:
        print(f"  {lst['name']} — {lst['id']}")


def cmd_cards(args, key, token):
    cards = _get(f"lists/{args.list_id}/cards", key, token, fields="name,id,desc,due")
    for c in cards:
        due = f" (due: {c.get('due', '')[:10]})" if c.get("due") else ""
        print(f"  {c['name']}{due} — {c['id']}")


def cmd_create_card(args, key, token):
    data = _post("cards", key, token, idList=args.list, name=args.name, desc=args.desc or "")
    print(f"Created card: {data['name']} — {data['id']}")


def cmd_move_card(args, key, token):
    _put(f"cards/{args.card_id}", key, token, idList=args.to_list)
    print(f"Moved card {args.card_id} to list {args.to_list}")


def cmd_comment(args, key, token):
    _post(f"cards/{args.card_id}/actions/comments", key, token, text=args.text)
    print(f"Comment added to {args.card_id}")


def cmd_archive(args, key, token):
    _put(f"cards/{args.card_id}", key, token, closed="true")
    print(f"Archived card {args.card_id}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("boards")

    p = sub.add_parser("lists")
    p.add_argument("board_id")

    p = sub.add_parser("cards")
    p.add_argument("list_id")

    p = sub.add_parser("create-card")
    p.add_argument("--list", required=True)
    p.add_argument("--name", required=True)
    p.add_argument("--desc", default=None)

    p = sub.add_parser("move-card")
    p.add_argument("card_id")
    p.add_argument("--to-list", required=True)

    p = sub.add_parser("comment")
    p.add_argument("card_id")
    p.add_argument("--text", required=True)

    p = sub.add_parser("archive")
    p.add_argument("card_id")

    args = parser.parse_args()
    key, token = _get_creds()

    handlers = {
        "boards": cmd_boards, "lists": cmd_lists, "cards": cmd_cards,
        "create-card": cmd_create_card, "move-card": cmd_move_card,
        "comment": cmd_comment, "archive": cmd_archive,
    }
    handlers[args.command](args, key, token)


if __name__ == "__main__":
    main()
