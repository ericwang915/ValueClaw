---
name: twitter-news
description: >
  Search Twitter/X for latest posts about stocks, crypto, markets, or any topic.
  Use when the user asks about Twitter sentiment, social media buzz, what people
  are saying on Twitter/X, cashtag mentions ($AAPL, $BTC), or wants to monitor
  KOL/influencer opinions. Supports keyword search, cashtag search, and user
  timeline lookup. Triggers on: twitter news, what's trending on twitter,
  twitter sentiment, social media buzz, X posts about, tweets about.
dependencies: tweepy,duckduckgo-search
metadata:
  emoji: "🐦"
---

# Twitter/X News — Social Sentiment Monitor

Search Twitter/X for the latest posts on any topic — stocks, crypto, macro, or general news.

## When to Use

✅ **USE this skill when:**
- "What are people saying about $AAPL on Twitter?"
- "Twitter sentiment on Bitcoin"
- "Latest tweets from @elonmusk"
- "What's trending on X about AI stocks?"
- "Social media buzz on NVDA earnings"
- User wants to gauge market sentiment from social media

## When NOT to Use

❌ **DON'T use this skill when:**
- User wants structured market data → use `yfinance` or `openbb`
- User wants news articles → use `finance-news` or `news` skill
- User wants technical chart analysis → use `technical-analyst` skill

## Setup

The skill works in two modes:

### Mode A — Twitter API v2 (recommended, richer data)

Add your bearer token to `value_claw.json` under `skills.twitter.bearerToken`:

```json
{
  "skills": {
    "twitter": {
      "bearerToken": "AAAAAAAAAAAAAAAAAAAAAxxxxxxx"
    }
  }
}
```

Alternatively, set the `TWITTER_BEARER_TOKEN` environment variable.
Free tier: 500K tweets/month read access.

### Mode B — DuckDuckGo fallback (no API key needed)

If no bearer token is configured, the script automatically falls back to DuckDuckGo
search scoped to `x.com`, which still provides useful results.

## Commands

### Search by keyword or cashtag

```bash
python {skill_path}/scripts/twitter_search.py search "AAPL earnings" --max 15
python {skill_path}/scripts/twitter_search.py search "$BTC" --max 10
python {skill_path}/scripts/twitter_search.py search "Fed rate cut" --max 20
```

### Search tweets from a specific user

```bash
python {skill_path}/scripts/twitter_search.py user "elonmusk" --max 10
python {skill_path}/scripts/twitter_search.py user "DeItaone" --max 5
```

### Cashtag shortcut (prepends $ automatically)

```bash
python {skill_path}/scripts/twitter_search.py cashtag AAPL --max 10
python {skill_path}/scripts/twitter_search.py cashtag BTC --max 10
```

### JSON output (for programmatic use)

```bash
python {skill_path}/scripts/twitter_search.py search "NVDA" --max 10 --format json
```

## Options

| Flag | Default | Description |
|------|---------|-------------|
| `--max` | `10` | Maximum number of results |
| `--format` | `text` | Output format: `text` or `json` |
| `--lang` | `en` | Language filter (Twitter API mode only) |

## Example Workflows

**Gauge sentiment before earnings:**
```
1. python {skill_path}/scripts/twitter_search.py cashtag AAPL --max 15
2. Summarize the overall sentiment (bullish/bearish/neutral)
3. Note key concerns or excitement themes
```

**Monitor KOL opinions:**
```
1. python {skill_path}/scripts/twitter_search.py user "unusual_whales" --max 10
2. python {skill_path}/scripts/twitter_search.py user "zaboranalyst" --max 10
3. Cross-reference their views with portfolio holdings
```

**Check social buzz on a trending topic:**
```
1. python {skill_path}/scripts/twitter_search.py search "tariff China stocks" --max 20
2. Identify which tickers are most mentioned
3. Assess whether the sentiment aligns with current positions
```

## Output Format

Each result shows:
- **Author** — Username and display name
- **Content** — Tweet text (truncated to 500 chars)
- **Engagement** — Likes, retweets, replies (Twitter API mode)
- **Date** — When the tweet was posted
- **URL** — Direct link to the tweet

## Notes

- Twitter API mode provides richer metadata (engagement counts, verified status)
- DuckDuckGo fallback is best-effort; results may be less fresh
- Cashtag searches (e.g. `$AAPL`) tend to surface more finance-focused content
- Rate limits apply: Twitter free tier allows ~100 requests per 15 minutes
