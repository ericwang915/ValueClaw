#!/usr/bin/env python3
"""Post tweets to Twitter/X with optional image attachments."""

import argparse
import json
import os
import sys


def find_config():
    """Search for value_claw.json in standard locations."""
    candidates = [
        os.path.join(os.getcwd(), "value_claw.json"),
        os.path.expanduser("~/.value_claw/value_claw.json"),
    ]
    d = os.path.dirname(os.path.abspath(__file__))
    for _ in range(8):
        candidates.append(os.path.join(d, "value_claw.json"))
        d = os.path.dirname(d)
    for p in candidates:
        if os.path.exists(p):
            return p
    return None


def load_twitter_config(config_path=None):
    """Load Twitter credentials from value_claw.json."""
    path = config_path or find_config()
    if not path or not os.path.exists(path):
        return {}
    with open(path) as f:
        cfg = json.load(f)
    return cfg.get("skills", {}).get("twitter", {})


def post_tweet(text, image_path=None, config_path=None):
    """Post a tweet with optional image. Returns (success, tweet_id_or_error)."""
    try:
        import tweepy
    except ImportError:
        return False, "tweepy not installed. Run: pip install tweepy"

    tw = load_twitter_config(config_path)
    api_key = tw.get("apiKey", "")
    api_secret = tw.get("apiSecret", "")
    access_token = tw.get("accessToken", "")
    access_secret = tw.get("accessTokenSecret", "")

    missing = []
    if not api_key:
        missing.append("skills.twitter.apiKey")
    if not api_secret:
        missing.append("skills.twitter.apiSecret")
    if not access_token:
        missing.append("skills.twitter.accessToken")
    if not access_secret:
        missing.append("skills.twitter.accessTokenSecret")
    if missing:
        return False, f"Missing Twitter credentials in value_claw.json: {', '.join(missing)}"

    auth = tweepy.OAuth1UserHandler(api_key, api_secret, access_token, access_secret)
    api = tweepy.API(auth)
    client = tweepy.Client(
        consumer_key=api_key,
        consumer_secret=api_secret,
        access_token=access_token,
        access_token_secret=access_secret,
    )

    tweet_text = text[:280]
    media_id = None

    if image_path and os.path.exists(image_path):
        try:
            media = api.media_upload(filename=image_path)
            media_id = media.media_id
            print(f"Image uploaded: {os.path.basename(image_path)} (media_id: {media_id})")
        except Exception as e:
            print(f"Warning: image upload failed ({e}), posting text only", file=sys.stderr)

    kwargs = {"text": tweet_text}
    if media_id:
        kwargs["media_ids"] = [media_id]

    try:
        resp = client.create_tweet(**kwargs)
        tweet_id = resp.data["id"]
        tweet_url = f"https://twitter.com/i/web/status/{tweet_id}"
        return True, {"id": tweet_id, "url": tweet_url, "text": tweet_text}
    except Exception as e:
        return False, str(e)


def main():
    parser = argparse.ArgumentParser(description="Post a tweet to Twitter/X")
    parser.add_argument("text", help="Tweet text (max 280 characters)")
    parser.add_argument("--image", help="Path to image file to attach")
    parser.add_argument("--config", help="Path to value_claw.json")
    parser.add_argument("--format", choices=["text", "json"], default="text")
    args = parser.parse_args()

    success, result = post_tweet(args.text, image_path=args.image, config_path=args.config)

    if args.format == "json":
        print(json.dumps({"success": success, "result": result}, indent=2))
    else:
        if success:
            print("Tweet posted successfully!")
            print(f"  ID: {result['id']}")
            print(f"  URL: {result['url']}")
            print(f"  Text: {result['text']}")
        else:
            print(f"Failed to post tweet: {result}", file=sys.stderr)
            sys.exit(1)


if __name__ == "__main__":
    main()
