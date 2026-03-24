#!/usr/bin/env python3
"""Slack Web API client for value_claw."""
import argparse
import json
import os
import sys

try:
    import requests
except ImportError:
    print("Error: requests is not installed. Run: pip install requests", file=sys.stderr)
    sys.exit(1)

BASE_URL = "https://slack.com/api"


def _get_token() -> str:
    """Read Slack token from value_claw.json or environment."""
    token = os.environ.get("SLACK_BOT_TOKEN", "")
    if token:
        return token

    config_paths = [
        os.path.expanduser("~/.value_claw/value_claw.json"),
        "value_claw.json",
    ]
    for path in config_paths:
        if os.path.isfile(path):
            try:
                with open(path, "r") as f:
                    cfg = json.load(f)
                token = cfg.get("skills", {}).get("slack", {}).get("token", "")
                if token:
                    return token
            except (json.JSONDecodeError, OSError):
                continue

    print("Error: Slack token not configured. Set skills.slack.token in value_claw.json", file=sys.stderr)
    sys.exit(1)


def _api(method: str, token: str, **params) -> dict:
    """Call a Slack API method."""
    resp = requests.post(
        f"{BASE_URL}/{method}",
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        json={k: v for k, v in params.items() if v is not None},
        timeout=10,
    )
    resp.raise_for_status()
    data = resp.json()
    if not data.get("ok"):
        print(f"Slack API error: {data.get('error', 'unknown')}", file=sys.stderr)
        sys.exit(1)
    return data


def _resolve_channel(token: str, name: str) -> str:
    """Resolve a #channel-name to a channel ID."""
    if name.startswith("C") and not name.startswith("#"):
        return name
    name = name.lstrip("#")
    data = _api("conversations.list", token, limit=200, types="public_channel,private_channel")
    for ch in data.get("channels", []):
        if ch["name"] == name:
            return ch["id"]
    print(f"Channel not found: #{name}", file=sys.stderr)
    sys.exit(1)


def cmd_send(args, token):
    ch = _resolve_channel(token, args.channel)
    data = _api("chat.postMessage", token, channel=ch, text=args.text)
    print(f"Message sent to {args.channel} (ts: {data['ts']})")


def cmd_read(args, token):
    ch = _resolve_channel(token, args.channel)
    data = _api("conversations.history", token, channel=ch, limit=args.limit)
    for msg in reversed(data.get("messages", [])):
        user = msg.get("user", "bot")
        text = msg.get("text", "")
        ts = msg.get("ts", "")
        print(f"[{ts}] {user}: {text}")


def cmd_react(args, token):
    _api("reactions.add", token, channel=args.channel, timestamp=args.timestamp, name=args.emoji)
    print(f"Reacted with :{args.emoji}:")


def cmd_pin(args, token):
    _api("pins.add", token, channel=args.channel, timestamp=args.timestamp)
    print("Message pinned")


def cmd_user(args, token):
    data = _api("users.info", token, user=args.user_id)
    user = data.get("user", {})
    print(json.dumps({
        "id": user.get("id"),
        "name": user.get("name"),
        "real_name": user.get("real_name"),
        "email": user.get("profile", {}).get("email"),
        "is_admin": user.get("is_admin"),
    }, indent=2))


def cmd_channels(args, token):
    data = _api("conversations.list", token, limit=200, types="public_channel,private_channel")
    for ch in data.get("channels", []):
        status = "archived" if ch.get("is_archived") else "active"
        print(f"  #{ch['name']} ({ch['id']}) [{status}]")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    p_send = sub.add_parser("send", help="Send a message")
    p_send.add_argument("--channel", required=True)
    p_send.add_argument("--text", required=True)

    p_read = sub.add_parser("read", help="Read recent messages")
    p_read.add_argument("--channel", required=True)
    p_read.add_argument("--limit", type=int, default=10)

    p_react = sub.add_parser("react", help="React to a message")
    p_react.add_argument("--channel", required=True)
    p_react.add_argument("--timestamp", required=True)
    p_react.add_argument("--emoji", required=True)

    p_pin = sub.add_parser("pin", help="Pin a message")
    p_pin.add_argument("--channel", required=True)
    p_pin.add_argument("--timestamp", required=True)

    p_user = sub.add_parser("user", help="Get user info")
    p_user.add_argument("--user-id", required=True)

    sub.add_parser("channels", help="List channels")

    args = parser.parse_args()
    token = _get_token()

    handlers = {
        "send": cmd_send, "read": cmd_read, "react": cmd_react,
        "pin": cmd_pin, "user": cmd_user, "channels": cmd_channels,
    }
    handlers[args.command](args, token)


if __name__ == "__main__":
    main()
