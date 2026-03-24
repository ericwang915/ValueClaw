---
name: slack
description: "Slack API integration — send/read messages, react to messages, pin items, and fetch member info. Use when: user wants to send a Slack message, check Slack channels, react to a message, or manage pins. NOT for: Discord (use Discord channel), email (use email skill), or real-time Slack event streaming."
dependencies: requests
metadata:
  emoji: "💬"
---

# Slack

Interact with Slack workspaces via the Slack Web API.

## When to Use

✅ **USE this skill when:**

- "Send a message to #general"
- "React to that Slack message with a thumbs up"
- "Read recent messages from #engineering"
- "Pin this message in the channel"
- "Who is user U12345?"
- "List pinned items in #announcements"

## When NOT to Use

❌ **DON'T use this skill when:**

- Discord messaging → use the Discord channel directly
- Email → use `email` skill
- Real-time Slack event listening → requires a Slack app with event subscriptions
- File uploads → use Slack's files.upload API directly

## Setup

1. Create a Slack app at https://api.slack.com/apps
2. Add Bot Token Scopes: `chat:write`, `channels:read`, `channels:history`, `reactions:write`, `reactions:read`, `pins:write`, `pins:read`, `users:read`
3. Install the app to your workspace
4. Copy the Bot User OAuth Token (starts with `xoxb-`)
5. Configure in `value_claw.json`:

```json
"skills": {
  "slack": {
    "token": "xoxb-your-bot-token"
  }
}
```

## Commands

### Send a message

```bash
python {skill_path}/slack_api.py send --channel "#general" --text "Hello from value_claw"
```

### Read recent messages

```bash
python {skill_path}/slack_api.py read --channel "#general" --limit 10
```

### React to a message

```bash
python {skill_path}/slack_api.py react --channel "C123" --timestamp "1712023032.1234" --emoji "white_check_mark"
```

### Pin a message

```bash
python {skill_path}/slack_api.py pin --channel "C123" --timestamp "1712023032.1234"
```

### Get member info

```bash
python {skill_path}/slack_api.py user --user-id "U123"
```

### List channels

```bash
python {skill_path}/slack_api.py channels
```

## Notes

- Channel names can be used with `#` prefix or as channel IDs (C...)
- Message timestamps serve as unique message IDs in Slack
- Rate limits: ~1 request/second for most methods
- Bot must be invited to channels to read/post messages

## Resources

| File | Description |
|------|-------------|
| `slack_api.py` | Slack Web API client |
