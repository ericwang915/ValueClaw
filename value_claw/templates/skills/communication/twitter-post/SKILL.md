---
name: twitter-post
description: "Post tweets to Twitter/X with optional image attachments. Supports text-only tweets and tweets with images (PNG/JPG). Uses Twitter API v2 for posting and v1.1 for media upload. Use when: user wants to post to Twitter, share analysis charts on X, tweet stock reports, or publish any content to their Twitter account."
metadata:
  emoji: "🐦"
  tokens:
    - name: Twitter API Key
      config_path: skills.twitter.apiKey
      required: true
    - name: Twitter API Secret
      config_path: skills.twitter.apiSecret
      required: true
    - name: Twitter Access Token
      config_path: skills.twitter.accessToken
      required: true
    - name: Twitter Access Token Secret
      config_path: skills.twitter.accessTokenSecret
      required: true
---

# Twitter Post Skill

Post tweets to Twitter/X with optional image attachments.

## When to Use

✅ **USE this skill when:**
- "Post this analysis to Twitter"
- "Tweet the TSLA chart"
- "Share this report on X"
- "Post a tweet about today's market"

## Usage/Commands

```bash
# Post a text-only tweet
python {skill_path}/twitter_post.py "Hello from Value Claw!"

# Post a tweet with an image
python {skill_path}/twitter_post.py "TSLA Analysis 📊" --image /path/to/chart.png

# Post with image, truncate to fit 280 chars
python {skill_path}/twitter_post.py "Very long text that might exceed the character limit..." --image /path/to/image.png

# JSON output (returns tweet ID and status)
python {skill_path}/twitter_post.py "Test tweet" --format json
```

## Token Configuration

All four Twitter OAuth 1.0a credentials must be set in `value_claw.json`:

```json
{
  "skills": {
    "twitter": {
      "apiKey": "your-api-key",
      "apiSecret": "your-api-secret",
      "accessToken": "your-access-token",
      "accessTokenSecret": "your-access-token-secret"
    }
  }
}
```

To obtain these keys:
1. Go to https://developer.twitter.com/en/portal/dashboard
2. Create a project & app (Free tier allows posting)
3. Under "Keys and tokens", generate Consumer Keys (API Key + Secret)
4. Generate Access Token and Secret (with Read and Write permissions)

## Notes

- Tweet text is truncated to 280 characters automatically
- Image upload uses Twitter API v1.1 (`media/upload`), tweet creation uses v2
- Supported image formats: PNG, JPG, GIF (up to 5 MB for images, 15 MB for GIFs)
- Requires `tweepy` package: `pip install tweepy`
