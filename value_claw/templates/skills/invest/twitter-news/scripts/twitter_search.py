#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "tweepy>=4.14",
#     "duckduckgo-search>=5.0",
# ]
# ///
"""Search Twitter/X for recent posts about any topic.

Uses Twitter API v2 (via tweepy) when TWITTER_BEARER_TOKEN is set,
otherwise falls back to DuckDuckGo search scoped to x.com.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone


# ---------------------------------------------------------------------------
# Twitter API v2 backend
# ---------------------------------------------------------------------------

def _load_bearer_token() -> str:
    """Load Twitter bearer token from value_claw.json or env var."""
    token = os.environ.get("TWITTER_BEARER_TOKEN", "")
    if token:
        return token
    for candidate in [
        os.path.expanduser("~/.value_claw/value_claw.json"),
        os.path.join(os.getcwd(), "value_claw.json"),
    ]:
        if os.path.isfile(candidate):
            try:
                with open(candidate, "r", encoding="utf-8") as f:
                    cfg = json.load(f)
                token = (cfg.get("skills", {}).get("twitter", {}).get("bearerToken", ""))
                if token:
                    return token
            except (OSError, json.JSONDecodeError):
                pass
    return ""


def _search_twitter_api(
    query: str,
    max_results: int = 10,
    lang: str = "en",
) -> list[dict]:
    """Search recent tweets via Twitter API v2."""
    try:
        import tweepy
    except ImportError:
        print("tweepy not installed. Run: pip install tweepy", file=sys.stderr)
        return []

    bearer = _load_bearer_token()
    if not bearer:
        return []

    client = tweepy.Client(bearer_token=bearer, wait_on_rate_limit=True)

    api_max = min(max_results, 100)
    try:
        resp = client.search_recent_tweets(
            query=f"{query} lang:{lang} -is:retweet",
            max_results=max(api_max, 10),
            tweet_fields=["created_at", "public_metrics", "author_id", "lang"],
            user_fields=["username", "name", "verified"],
            expansions=["author_id"],
        )
    except tweepy.errors.TweepyException as exc:
        print(f"Twitter API error: {exc}", file=sys.stderr)
        return []

    if not resp.data:
        return []

    users_map: dict[str, dict] = {}
    if resp.includes and "users" in resp.includes:
        for u in resp.includes["users"]:
            users_map[str(u.id)] = {
                "username": u.username,
                "name": u.name,
                "verified": getattr(u, "verified", False),
            }

    results = []
    for tweet in resp.data[:max_results]:
        author = users_map.get(str(tweet.author_id), {})
        metrics = tweet.public_metrics or {}
        results.append({
            "author": f"@{author.get('username', '?')}",
            "author_name": author.get("name", ""),
            "verified": author.get("verified", False),
            "text": tweet.text[:500],
            "date": tweet.created_at.isoformat() if tweet.created_at else "",
            "likes": metrics.get("like_count", 0),
            "retweets": metrics.get("retweet_count", 0),
            "replies": metrics.get("reply_count", 0),
            "url": f"https://x.com/i/status/{tweet.id}",
            "source": "twitter_api",
        })
    return results


def _user_tweets_api(
    username: str,
    max_results: int = 10,
) -> list[dict]:
    """Fetch recent tweets from a specific user via Twitter API v2."""
    try:
        import tweepy
    except ImportError:
        return []

    bearer = _load_bearer_token()
    if not bearer:
        return []

    client = tweepy.Client(bearer_token=bearer, wait_on_rate_limit=True)

    try:
        user_resp = client.get_user(username=username, user_fields=["name", "verified"])
        if not user_resp.data:
            print(f"User @{username} not found.", file=sys.stderr)
            return []
        user = user_resp.data
        user_info = {
            "username": user.username,
            "name": user.name,
            "verified": getattr(user, "verified", False),
        }

        api_max = min(max_results, 100)
        tweets_resp = client.get_users_tweets(
            id=user.id,
            max_results=max(api_max, 5),
            tweet_fields=["created_at", "public_metrics"],
            exclude=["retweets"],
        )
    except tweepy.errors.TweepyException as exc:
        print(f"Twitter API error: {exc}", file=sys.stderr)
        return []

    if not tweets_resp.data:
        return []

    results = []
    for tweet in tweets_resp.data[:max_results]:
        metrics = tweet.public_metrics or {}
        results.append({
            "author": f"@{user_info['username']}",
            "author_name": user_info["name"],
            "verified": user_info["verified"],
            "text": tweet.text[:500],
            "date": tweet.created_at.isoformat() if tweet.created_at else "",
            "likes": metrics.get("like_count", 0),
            "retweets": metrics.get("retweet_count", 0),
            "replies": metrics.get("reply_count", 0),
            "url": f"https://x.com/i/status/{tweet.id}",
            "source": "twitter_api",
        })
    return results


# ---------------------------------------------------------------------------
# DuckDuckGo fallback
# ---------------------------------------------------------------------------

def _search_ddg(query: str, max_results: int = 10) -> list[dict]:
    """Fallback: search DuckDuckGo for recent x.com/twitter.com posts."""
    try:
        from duckduckgo_search import DDGS
    except ImportError:
        print(
            "duckduckgo-search not installed. Run: pip install duckduckgo-search",
            file=sys.stderr,
        )
        return []

    combined_query = f"site:x.com OR site:twitter.com {query}"
    with DDGS() as ddgs:
        raw = list(ddgs.text(combined_query, max_results=max_results))

    results = []
    for r in raw:
        url = r.get("href", r.get("url", ""))
        body = r.get("body", r.get("snippet", ""))[:500]

        author = ""
        if "x.com/" in url or "twitter.com/" in url:
            parts = url.split("/")
            for i, p in enumerate(parts):
                if p in ("x.com", "twitter.com") and i + 1 < len(parts):
                    author = f"@{parts[i + 1]}"
                    break

        results.append({
            "author": author,
            "author_name": "",
            "verified": False,
            "text": body,
            "date": r.get("date", ""),
            "likes": 0,
            "retweets": 0,
            "replies": 0,
            "url": url,
            "source": "duckduckgo",
        })
    return results


def _user_tweets_ddg(username: str, max_results: int = 10) -> list[dict]:
    """Fallback: search DuckDuckGo for tweets from a specific user."""
    return _search_ddg(f"from:@{username}", max_results=max_results)


# ---------------------------------------------------------------------------
# Unified interface
# ---------------------------------------------------------------------------

def search_tweets(
    query: str,
    max_results: int = 10,
    lang: str = "en",
) -> list[dict]:
    """Search recent tweets; auto-selects API or DDG backend."""
    results = _search_twitter_api(query, max_results, lang)
    if results:
        return results
    return _search_ddg(query, max_results)


def user_tweets(username: str, max_results: int = 10) -> list[dict]:
    """Fetch recent tweets from a user; auto-selects backend."""
    results = _user_tweets_api(username, max_results)
    if results:
        return results
    return _user_tweets_ddg(username, max_results)


# ---------------------------------------------------------------------------
# Output formatting
# ---------------------------------------------------------------------------

def _format_text(results: list[dict]) -> str:
    if not results:
        return "No results found."

    lines: list[str] = []
    backend = results[0].get("source", "unknown")
    lines.append(f"[Source: {backend}]  Found {len(results)} result(s)\n")

    for i, r in enumerate(results, 1):
        author = r["author"] or "unknown"
        name = f" ({r['author_name']})" if r["author_name"] else ""
        verified = " ✓" if r["verified"] else ""
        lines.append(f"{'─' * 60}")
        lines.append(f"{i}. {author}{name}{verified}")
        if r["date"]:
            lines.append(f"   📅 {r['date']}")
        lines.append(f"   {r['text']}")
        if backend == "twitter_api":
            lines.append(
                f"   ❤️ {r['likes']}  🔁 {r['retweets']}  💬 {r['replies']}"
            )
        if r["url"]:
            lines.append(f"   🔗 {r['url']}")
        lines.append("")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Search Twitter/X for recent posts.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # --- search ---
    p_search = sub.add_parser("search", help="Search tweets by keyword")
    p_search.add_argument("query", help="Search query (e.g. '$AAPL earnings')")
    p_search.add_argument("--max", type=int, default=10, help="Max results")
    p_search.add_argument("--format", choices=["text", "json"], default="text")
    p_search.add_argument("--lang", default="en", help="Language filter (API mode)")

    # --- user ---
    p_user = sub.add_parser("user", help="Get recent tweets from a user")
    p_user.add_argument("username", help="Twitter username (without @)")
    p_user.add_argument("--max", type=int, default=10, help="Max results")
    p_user.add_argument("--format", choices=["text", "json"], default="text")

    # --- cashtag ---
    p_cash = sub.add_parser("cashtag", help="Search by cashtag (e.g. AAPL → $AAPL)")
    p_cash.add_argument("symbol", help="Ticker symbol (without $)")
    p_cash.add_argument("--max", type=int, default=10, help="Max results")
    p_cash.add_argument("--format", choices=["text", "json"], default="text")
    p_cash.add_argument("--lang", default="en", help="Language filter (API mode)")

    args = parser.parse_args()

    if args.command == "search":
        results = search_tweets(args.query, args.max, args.lang)
    elif args.command == "user":
        results = user_tweets(args.username, args.max)
    elif args.command == "cashtag":
        results = search_tweets(f"${args.symbol}", args.max, args.lang)
    else:
        parser.print_help()
        sys.exit(1)

    if args.format == "json":
        print(json.dumps(results, indent=2, ensure_ascii=False))
    else:
        print(_format_text(results))


if __name__ == "__main__":
    main()
