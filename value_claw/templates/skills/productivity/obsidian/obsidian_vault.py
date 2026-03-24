#!/usr/bin/env python3
"""Obsidian vault operations — search, create, list notes."""
import argparse
import json
import sys
from datetime import datetime
from pathlib import Path


def _find_vault() -> Path | None:
    """Try to locate the default Obsidian vault."""
    obsidian_config = Path.home() / "Library" / "Application Support" / "obsidian" / "obsidian.json"
    if obsidian_config.is_file():
        try:
            data = json.loads(obsidian_config.read_text())
            vaults = data.get("vaults", {})
            for vid, info in vaults.items():
                vault_path = Path(info.get("path", ""))
                if vault_path.is_dir() and info.get("open"):
                    return vault_path
            for vid, info in vaults.items():
                vault_path = Path(info.get("path", ""))
                if vault_path.is_dir():
                    return vault_path
        except (json.JSONDecodeError, OSError):
            pass

    for candidate in [
        Path.home() / "Documents" / "Obsidian",
        Path.home() / "Notes",
        Path.home() / "Documents" / "Notes",
    ]:
        if candidate.is_dir() and any(candidate.glob("*.md")):
            return candidate

    return None


def cmd_locate(args):
    vault = _find_vault()
    if vault:
        print(vault)
    else:
        print("No Obsidian vault found. Set --vault explicitly.", file=sys.stderr)
        sys.exit(1)


def cmd_search(args):
    vault = Path(args.vault) if args.vault else _find_vault()
    if not vault or not vault.is_dir():
        print("Vault not found", file=sys.stderr)
        sys.exit(1)

    query = args.query.lower()
    for md in sorted(vault.rglob("*.md")):
        if md.parts and any(p.startswith(".") for p in md.relative_to(vault).parts):
            continue
        if query in md.stem.lower():
            print(f"  {md.relative_to(vault)}")


def cmd_search_content(args):
    vault = Path(args.vault) if args.vault else _find_vault()
    if not vault or not vault.is_dir():
        print("Vault not found", file=sys.stderr)
        sys.exit(1)

    query = args.query.lower()
    for md in sorted(vault.rglob("*.md")):
        if any(p.startswith(".") for p in md.relative_to(vault).parts):
            continue
        try:
            text = md.read_text(encoding="utf-8", errors="replace")
            lines = text.splitlines()
            for i, line in enumerate(lines):
                if query in line.lower():
                    print(f"  {md.relative_to(vault)}:{i+1}: {line.strip()[:100]}")
        except OSError:
            continue


def cmd_create(args):
    vault = Path(args.vault) if args.vault else _find_vault()
    if not vault or not vault.is_dir():
        print("Vault not found", file=sys.stderr)
        sys.exit(1)

    note_path = vault / args.path
    if not note_path.suffix:
        note_path = note_path.with_suffix(".md")
    note_path.parent.mkdir(parents=True, exist_ok=True)
    content = args.content or f"# {note_path.stem}\n\nCreated: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n"
    note_path.write_text(content, encoding="utf-8")
    print(f"Created: {note_path.relative_to(vault)}")


def cmd_list(args):
    vault = Path(args.vault) if args.vault else _find_vault()
    if not vault or not vault.is_dir():
        print("Vault not found", file=sys.stderr)
        sys.exit(1)

    folder = vault / args.path if args.path else vault
    if not folder.is_dir():
        print(f"Folder not found: {args.path}", file=sys.stderr)
        sys.exit(1)

    for md in sorted(folder.rglob("*.md")):
        if any(p.startswith(".") for p in md.relative_to(vault).parts):
            continue
        print(f"  {md.relative_to(vault)}")


def cmd_recent(args):
    vault = Path(args.vault) if args.vault else _find_vault()
    if not vault or not vault.is_dir():
        print("Vault not found", file=sys.stderr)
        sys.exit(1)

    files = []
    for md in vault.rglob("*.md"):
        if any(p.startswith(".") for p in md.relative_to(vault).parts):
            continue
        files.append((md.stat().st_mtime, md))

    files.sort(reverse=True)
    for mtime, md in files[:args.limit]:
        dt = datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M")
        print(f"  {dt}  {md.relative_to(vault)}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--vault", default=None, help="Path to Obsidian vault")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("locate", help="Find vault path")

    p = sub.add_parser("search", help="Search note titles")
    p.add_argument("query")

    p = sub.add_parser("search-content", help="Search note content")
    p.add_argument("query")

    p = sub.add_parser("create", help="Create a note")
    p.add_argument("path", help="Note path relative to vault (e.g. Folder/Note)")
    p.add_argument("--content", default=None)

    p = sub.add_parser("list", help="List notes")
    p.add_argument("path", nargs="?", default=None)

    p = sub.add_parser("recent", help="Recent notes")
    p.add_argument("--limit", type=int, default=10)

    args = parser.parse_args()
    handlers = {
        "locate": cmd_locate, "search": cmd_search,
        "search-content": cmd_search_content, "create": cmd_create,
        "list": cmd_list, "recent": cmd_recent,
    }
    handlers[args.command](args)


if __name__ == "__main__":
    main()
