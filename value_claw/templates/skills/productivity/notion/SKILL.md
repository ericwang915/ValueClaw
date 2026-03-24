---
name: notion
description: "Notion API for creating and managing pages, databases, and blocks. Use when: user asks to create a Notion page, query a database, search notes, add content to Notion, or manage Notion workspace items. NOT for: local file editing (use read_file/write_file), Obsidian vaults (use obsidian skill), or real-time collaboration."
dependencies: requests
metadata:
  emoji: "📝"
---

# Notion

Use the Notion API to create, read, and update pages, databases, and blocks.

## When to Use

- "Create a Notion page with my meeting notes"
- "Search my Notion for project plans"
- "Add an item to my Notion database"
- "Query my Notion task tracker"
- "Update the status of this Notion page"

## When NOT to Use

- Local Markdown files: use read_file / write_file directly
- Obsidian vaults: use obsidian skill
- Trello boards: use trello skill
- Google Docs: use google_workspace skill

## Setup

1. Create an integration at https://notion.so/my-integrations
2. Copy the API key (starts with ntn_ or secret_)
3. Configure in value_claw.json:

```json
"skills": {
  "notion": {
    "token": "ntn_your_key_here"
  }
}
```

4. Share target pages/databases with your integration

## Commands

### Search pages

```bash
python {skill_path}/notion_api.py search "query text"
```

### Get a page

```bash
python {skill_path}/notion_api.py get-page <page_id>
```

### Get page content (blocks)

```bash
python {skill_path}/notion_api.py get-blocks <page_id>
```

### Create a page in a database

```bash
python {skill_path}/notion_api.py create-page --database <db_id> --title "New Item" --props '{"Status": "Todo"}'
```

### Query a database

```bash
python {skill_path}/notion_api.py query-db <database_id>
```

### Update page properties

```bash
python {skill_path}/notion_api.py update-page <page_id> --props '{"Status": "Done"}'
```

### Append blocks to a page

```bash
python {skill_path}/notion_api.py append-blocks <page_id> --text "New paragraph content"
```

## Notes

- Page/database IDs are UUIDs (with or without dashes)
- The API cannot set database view filters (UI-only)
- Rate limit: ~3 requests/second average
- The Notion-Version header is required for direct API calls

## Resources

| File | Description |
|------|-------------|
| `notion_api.py` | Notion REST API client |
