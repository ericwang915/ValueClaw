---
name: email
description: >
  Send emails via SMTP. Supports plain text, HTML, attachments, CC/BCC.
  Use when: the user asks to send an email, notification, message, or report.
  NOT for: reading/receiving mail (use google_workspace for Gmail), sending
  via Gmail API (use google_workspace instead).
metadata:
  emoji: "✉️"
---
# Email (SMTP)

## When to Use

- [ ] Send emails through SMTP (Gmail, Outlook, custom server)
- [ ] Notifications, messages, or reports
- [ ] Emails with CC, BCC, or HTML body
- [ ] When user explicitly asks to "send an email"

## When NOT to Use

- [ ] Reading or searching Gmail — use `google_workspace` with gog
- [ ] Sending via Gmail API — use `google_workspace` gmail send
- [ ] Tasks that don't involve sending email

## Setup

Configure in `value_claw.json` (or the Config dashboard):

```json
"skills": {
  "email": {
    "smtpServer": "smtp.gmail.com",
    "smtpPort": 587,
    "senderEmail": "you@gmail.com",
    "senderPassword": "your-app-password"
  }
}
```

For Gmail, use an [App Password](https://myaccount.google.com/apppasswords).

## Usage/Commands

```bash
python {skill_path}/send_email.py \
  --to "recipient@example.com" \
  --subject "Hello" \
  --body "Message body here"
```

| Option | Description |
|--------|-------------|
| `--to` | Recipient address (required) |
| `--subject` | Subject line |
| `--body` | Message body |
| `--cc "a@b.com,c@d.com"` | CC recipients |
| `--bcc "x@y.com"` | BCC recipients |
| `--html` | Treat body as HTML |

## Notes

- Always confirm before sending on behalf of the user
- For Gmail, App Password is required (not regular password)
- Credentials are read from `skills.email` in `value_claw.json`
