---
name: trello
description: "Manage Trello boards, lists, and cards via the Trello REST API. Use when: user asks to create/move/list Trello cards, check board status, manage task lists, or organise project work in Trello. NOT for: Notion databases (use notion skill), GitHub issues (use github skill), or local task lists."
dependencies: requests
metadata:
  emoji: "📋"
---

# Trello

Manage Trello boards, lists, and cards directly from value_claw.

## When to Use

✅ **USE this skill when:**

- "Show my Trello boards"
- "Create a card for the login bug"
- "Move this card to Done"
- "List all cards in the backlog"
- "Add a comment to card X"
- "Archive completed cards"

## When NOT to Use

❌ **DON'T use this skill when:**

- Notion databases → use `notion` skill
- GitHub issues or PRs → use `github` skill
- Local to-do lists → use `read_file` / `write_file`
- Google Sheets tracking → use `google_workspace` skill

## Setup

1. Get your API key: https://trello.com/app-key
2. Generate a token (click "Token" link on that page)
3. Configure in `value_claw.json`:

```json
"skills": {
  "trello": {
    "apiKey": "your-api-key",
    "token": "your-token"
  }
}
```

## Commands

### List boards

```bash
python {skill_path}/trello_api.py boards
```

### List lists in a board

```bash
python {skill_path}/trello_api.py lists <board_id>
```

### List cards in a list

```bash
python {skill_path}/trello_api.py cards <list_id>
```

### Create a card

```bash
python {skill_path}/trello_api.py create-card --list <list_id> --name "Card Title" --desc "Description"
```

### Move a card

```bash
python {skill_path}/trello_api.py move-card <card_id> --to-list <list_id>
```

### Add a comment

```bash
python {skill_path}/trello_api.py comment <card_id> --text "Your comment"
```

### Archive a card

```bash
python {skill_path}/trello_api.py archive <card_id>
```

### Alternative: Direct curl

```bash
TRELLO_KEY="your-key"
TRELLO_TOKEN="your-token"
curl -s "https://api.trello.com/1/members/me/boards?key=$TRELLO_KEY&token=$TRELLO_TOKEN" | python -m json.tool
```

## Notes

- Board/List/Card IDs can be found in Trello URLs or via the list commands
- Rate limits: 300 requests per 10 seconds per API key
- The API key and token provide full access — keep them secret

## Resources

| File | Description |
|------|-------------|
| `trello_api.py` | Trello REST API client |
