---
name: obsidian
description: "Work with Obsidian vaults (plain Markdown notes). Use when: user asks to search notes, create notes, move/rename notes, or manage their Obsidian vault. NOT for: Notion pages (use notion skill), non-Markdown files, or Obsidian plugin configuration."
metadata:
  emoji: "💎"
---

# Obsidian

Work with Obsidian vaults — they are just folders of plain Markdown files.

## When to Use

✅ **USE this skill when:**

- "Search my notes for X"
- "Create a new note about Y"
- "Find all notes tagged with Z"
- "Move this note to a different folder"
- "List my recent notes"

## When NOT to Use

❌ **DON'T use this skill when:**

- Notion pages → use `notion` skill
- Non-Markdown documents → use appropriate file tools
- Obsidian plugin settings → edit `.obsidian/` config directly
- Google Docs → use `google_workspace` skill

## Vault Location

Obsidian vaults are normal folders on disk. Common locations:

- macOS: `~/Documents/Obsidian/`, `~/Library/Mobile Documents/...`
- Linux: `~/Documents/Obsidian/`, `~/Notes/`
- Windows: `%USERPROFILE%\Documents\Obsidian\`

On macOS, vault paths are tracked in:
`~/Library/Application Support/obsidian/obsidian.json`

## Commands

### Find the vault path

```bash
python {skill_path}/obsidian_vault.py locate
```

### Search note titles

```bash
python {skill_path}/obsidian_vault.py search "query"
```

### Search note content

```bash
python {skill_path}/obsidian_vault.py search-content "query"
```

### Create a new note

```bash
python {skill_path}/obsidian_vault.py create "Folder/Note Title" --content "# My Note\n\nContent here"
```

### List notes in a folder

```bash
python {skill_path}/obsidian_vault.py list "folder/path"
```

### List recent notes

```bash
python {skill_path}/obsidian_vault.py recent --limit 10
```

### Direct file editing

Since Obsidian notes are plain Markdown, you can always edit them directly:

```bash
# Read a note
cat ~/Documents/Obsidian/MyVault/Notes/example.md

# Append to a note
echo "## New Section" >> ~/Documents/Obsidian/MyVault/Notes/example.md
```

Obsidian will pick up changes automatically.

## Wikilinks

Obsidian uses `[[wikilinks]]` for inter-note links. When moving or renaming
notes, consider updating links in other files that reference the moved note.

## Notes

- Vault = normal folder; no special tools needed for basic operations
- Config lives in `.obsidian/` (workspace + plugin settings) — usually don't touch
- Avoid writing to hidden dot-folders via Obsidian URI
- Multiple vaults are common (work/personal, iCloud/local)

## Resources

| File | Description |
|------|-------------|
| `obsidian_vault.py` | Obsidian vault operations (search, create, list) |
