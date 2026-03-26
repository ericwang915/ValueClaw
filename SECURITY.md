# Security Policy

## Supported Versions

| Version | Supported          |
|---------|--------------------|
| 0.7.x   | ✅ Current release  |
| < 0.7   | ❌ Not supported    |

## Reporting a Vulnerability

If you discover a security vulnerability in ValueClaw, please report it responsibly:

1. **DO NOT** open a public GitHub issue for security vulnerabilities.
2. Email the maintainer directly at: **wangchen2007915@gmail.com**
3. Include a detailed description of the vulnerability, steps to reproduce, and potential impact.
4. You will receive a response within 72 hours acknowledging the report.

## Security Considerations

### API Keys & Credentials
- All API keys are stored in `value_claw.json` which is gitignored by default.
- The web dashboard masks sensitive values (API keys, tokens) in the config viewer.
- Never commit `value_claw.json` to version control.

### Command Execution
- The `run_command` tool executes shell commands within a sandboxed directory.
- File write operations are restricted to the `~/.value_claw/` sandbox.
- **Note:** `read_file` currently does not enforce sandbox restrictions — this is a known limitation being addressed.

### Web Dashboard
- The web dashboard (port 7788) does **not** include authentication by default.
- If exposing to a network, use a reverse proxy (nginx/caddy) with authentication.
- Do not expose port 7788 to the public internet without additional security measures.

### Network Requests
- All SEC EDGAR requests use a proper User-Agent header as required by SEC policy.
- Web scraping respects rate limits with built-in `time.sleep()` delays.
- No data is sent to third parties beyond the configured LLM provider and data APIs.

## Best Practices

1. Run ValueClaw on a trusted machine — it has access to your file system within `~/.value_claw/`.
2. Use `allowedUsers` in Telegram/Discord config to restrict bot access.
3. Regularly rotate API keys, especially LLM provider keys.
4. Keep ValueClaw updated to the latest version for security patches.
