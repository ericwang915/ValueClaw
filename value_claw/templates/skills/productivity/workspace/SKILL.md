---
name: google_workspace
description: >
  Google Workspace via gog CLI — Gmail, Calendar, Drive, Contacts, Sheets,
  and Docs. Use when: the user asks to send/search Gmail, check calendar,
  manage Drive files, read or edit Sheets, export Docs, or look up contacts.
  NOT for: Google Cloud APIs, Firebase, or services outside Workspace.
metadata:
  emoji: "📧"
---
# Google Workspace (gog CLI)

Powered by [gog](https://github.com/steipete/gogcli) — a Google Workspace CLI for Gmail, Calendar, Drive, Contacts, Sheets, and Docs.

## When to Use

- [ ] Search Gmail, send email, read or manage messages
- [ ] List or create calendar events
- [ ] Search, list, or download Drive files
- [ ] Read or edit Google Sheets (get, append, update, clear)
- [ ] Export or read Google Docs content
- [ ] List or search Contacts

## When NOT to Use

- [ ] Google Cloud Platform APIs (compute, storage, etc.)
- [ ] Firebase or other non-Workspace services
- [ ] Tasks that don't involve Gmail, Calendar, Drive, Sheets, Docs, or Contacts
- [ ] In-place editing of Google Docs (gog supports read/export only)

## Setup

1. Install gog:
   ```bash
   brew install steipete/tap/gogcli
   ```

2. Create OAuth credentials at [Google Cloud Console](https://console.cloud.google.com/apis/credentials) (Desktop App), download `client_secret.json`.

3. Authenticate:
   ```bash
   gog auth credentials /path/to/client_secret.json
   gog auth add you@gmail.com --services gmail,calendar,drive,contacts,sheets,docs
   ```

4. Optionally set `GOG_ACCOUNT=you@gmail.com` to skip `--account` on each call.

## Usage/Commands

### Gmail

| Action | Command |
|--------|---------|
| Search mail | `gog gmail search 'newer_than:7d' --max 10` |
| Send email | `gog gmail send --to user@example.com --subject "Hi" --body "Hello"` |
| Read message | `gog gmail read <message_id>` |
| Mark as read | `gog gmail labels modify <message_id> --remove UNREAD` |
| List labels | `gog gmail labels list` |

### Calendar

| Action | Command |
|--------|---------|
| List events | `gog calendar events --from 2026-02-23 --to 2026-02-28` |
| Create event | `gog calendar create --title "Meeting" --start "2026-02-24T10:00" --end "2026-02-24T11:00"` |

### Drive

| Action | Command |
|--------|---------|
| Search files | `gog drive search "query" --max 10` |
| List files | `gog drive list --max 20` |
| Download | `gog drive download <file_id> --out /tmp/file.pdf` |

### Google Sheets

| Action | Command |
|--------|---------|
| Get data | `gog sheets get <spreadsheet_id> "Sheet1!A1:D10" --json` |
| Metadata | `gog sheets metadata <spreadsheet_id> --json` |
| Append rows | `gog sheets append <spreadsheet_id> "Sheet1!A:C" --values-json '[["x","y","z"]]'` |
| Update cells | `gog sheets update <spreadsheet_id> "Sheet1!A1:B2" --values-json '[["A","B"],["1","2"]]'` |
| Clear range | `gog sheets clear <spreadsheet_id> "Sheet1!A2:Z"` |

### Google Docs

| Action | Command |
|--------|---------|
| Read content | `gog docs cat <document_id>` |
| Export | `gog docs export <document_id> --format txt --out /tmp/doc.txt` |
| Copy | `gog docs copy <document_id> --title "Copy of Doc"` |

### Contacts

| Action | Command |
|--------|---------|
| List contacts | `gog contacts list --max 20` |
| Search | `gog contacts search "name"` |

## Notes

- **Always confirm** before sending emails or creating calendar events
- For automation, use `--json` and `--no-input` flags
- Set `GOG_ACCOUNT` env var to skip `--account` on every command
- Use `gog auth list` to check configured accounts
