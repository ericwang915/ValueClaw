---
name: github
description: >
  GitHub operations via gh CLI or Python API. Use when: listing repos, creating/viewing
  issues and PRs, checking CI runs, managing releases, or querying the GitHub API.
  NOT for: general git commands (use git directly), cloning private repos without auth.
dependencies: requests
metadata:
  emoji: "🦑"
---
# GitHub

## When to Use

- [ ] List repositories, issues, or pull requests
- [ ] Create or view issues and PRs
- [ ] Check CI/workflow run status
- [ ] Create or manage releases
- [ ] Query GitHub REST or GraphQL API
- [ ] Review PR checks, comments, or status

## When NOT to Use

- [ ] General git commands (commit, push, branch) — use `git` directly
- [ ] Cloning public repos — use `git clone` without this skill
- [ ] Tasks that don't involve GitHub (e.g., local file operations)

## Setup

1. **For gh CLI**: Install with `brew install gh` (macOS) or see [cli.github.com](https://cli.github.com/)
2. **Auth**: Run `gh auth login` or set `GH_TOKEN` / `GITHUB_TOKEN`
3. **For Python fallback**: Create a PAT at https://github.com/settings/tokens and add to `value_claw.json`:

```json
"skills": {
  "github": {
    "token": "ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
  }
}
```

## Usage/Commands

### gh CLI (Preferred)

| Action | Command |
|--------|---------|
| List PRs | `gh pr list --repo owner/repo` |
| View PR | `gh pr view <number> --repo owner/repo` |
| Create PR | `gh pr create --repo owner/repo --title "..." --body "..."` |
| PR checks | `gh pr checks <number> --repo owner/repo` |
| List issues | `gh issue list --repo owner/repo` |
| Create issue | `gh issue create --repo owner/repo --title "..." --body "..."` |
| Workflow runs | `gh run list --repo owner/repo` |
| View run | `gh run view <run_id> --repo owner/repo` |
| REST API | `gh api /repos/owner/repo` |
| GraphQL | `gh api graphql -f query='{ viewer { login } }'` |

### Python Fallback

When `gh` is not installed or for custom logic:

```bash
python {skill_path}/gh.py <command> [options]
```

- `repos <user>` — list user's public repositories
- `repo <owner/repo>` — get repository details
- `issues <owner/repo>` — list open issues
- `create-issue <owner/repo> --title "..." --body "..."` — create an issue
- `prs <owner/repo>` — list open pull requests
- `pr <owner/repo> <number>` — get PR details

## Notes

- Prefer `gh` CLI for standard operations; it handles auth, pagination, and output formatting
- Use `{skill_path}/gh.py` when you need Python-specific behavior or gh is unavailable
- For CI runs, `gh run list` and `gh run view` show Actions workflow status
