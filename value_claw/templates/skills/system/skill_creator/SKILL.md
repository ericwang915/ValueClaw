---
name: skill_creator
description: >
  Dynamically create new skills when no existing skill can handle the request.
  Use when: you need a capability that doesn't exist yet — write the code,
  bundle it as a skill, install dependencies, and make it available.
  NOT for: one-off tasks existing tools handle, or skills too specific to reuse.
metadata:
  emoji: "🛠️"
---
# Skill Creator

## When to Use

- [ ] The user asks for something no installed skill covers
- [ ] An existing skill is too limited and needs a better replacement
- [ ] A recurring task would benefit from a dedicated, reusable skill

## When NOT to Use

- [ ] One-off tasks that existing tools can handle (e.g., `run_command` for shell)
- [ ] Skills too specific to be reused — generalize first
- [ ] Don't hardcode user-specific values (names, URLs, topics) — use parameters

## Setup

Uses the `create_skill` tool. No API keys or external setup required.

## Usage/Commands

1. **Analyze the gap**: identify what capability is missing
2. **Plan the skill**: name, category, scripts, pip dependencies
3. **Call `create_skill`** with:
   - `name` — short, snake_case (e.g., `pdf_summarizer`)
   - `description` — one-line summary
   - `instructions` — full Markdown body
   - `category` — e.g., `data`, `dev`, `web`, `automation`
   - `resources` — dict mapping filenames to source code
   - `dependencies` — list of pip packages
4. **Activate**: `use_skill(skill_name="<name>")`
5. **Run it**: follow the loaded instructions

### Design Principles

- **Generic over specific** — parameterize everything; avoid hardcoded topics/recipients
- **Single responsibility** — one skill, one purpose
- **Parameterized** — use CLI args, not hardcoded values
- **Config-driven credentials** — read from `value_claw.json` under `skills.<name>`
- **Minimal dependencies** — only add pip packages when truly needed
- **Reusable** — ask: "Would this help someone with a different task?"

### SKILL.md Body Template

```
## Instructions
<Clear explanation and when to use.>

### Prerequisites
<Setup, API keys if needed>

### Usage
1. <steps>
2. Call: `python context/skills/<category>/<name>/<script>.py <args>`
3. <interpret results>

### Examples
**Example:** <typical use case>

## Resources
| File | Description |
|------|-------------|
| script.py | <what it does> |
```

## Notes

- Design for reuse: generalize queries, recipients, URLs
- Write production-quality Python with error handling and docstrings
- After creation, call `use_skill` to load the new instructions before running
