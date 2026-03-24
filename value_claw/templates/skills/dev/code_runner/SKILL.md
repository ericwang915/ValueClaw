---
name: code_runner
description: >
  Execute Python code snippets safely in an isolated subprocess with timeout
  protection. Use when: the user asks to run, test, or evaluate Python code,
  calculate expressions, or prototype logic. NOT for: running shell commands,
  executing other languages, or code that needs filesystem/network access.
metadata:
  emoji: "▶️"
---
# Code Runner

## When to Use

- [ ] Run or test Python code snippets
- [ ] Evaluate expressions (e.g., "calculate 2^100")
- [ ] Prototype logic or verify algorithms
- [ ] Execute user-provided Python code safely

## When NOT to Use

- [ ] Running shell commands or external programs — use `run_command` / terminal
- [ ] Executing non-Python code (JavaScript, etc.)
- [ ] Code requiring heavy I/O, network calls, or persistent state
- [ ] Editing or analyzing code without running it

## Setup

No API keys or credentials needed. Uses the bundled `run_code.py` script.

## Usage/Commands

```bash
python {skill_path}/run_code.py [options]
```

**Input methods:**

| Method | Example |
|--------|---------|
| Inline code | `--code "print(2+2)"` |
| From file | `--file script.py` |
| Stdin | Pipe code via stdin |

**Options:**

| Option | Description | Default |
|--------|-------------|---------|
| `--timeout N` | Max execution time (seconds) | 30 |
| `--format json` | Output as JSON (stdout, stderr, exit_code) | text |
| `--no-capture` | Stream output directly | off |

## Notes

- Code runs in a **subprocess** (not eval/exec in the agent process) for safety
- Timeout prevents infinite loops
- Working directory is the project root
- For shell commands or other languages, use the terminal directly
