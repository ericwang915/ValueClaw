---
name: http_request
description: >
  Make HTTP requests (GET, POST, PUT, DELETE, PATCH) to any API endpoint.
  Use when: the user asks to call an API, test an endpoint, fetch JSON/data from
  a URL, or interact with a REST API. NOT for: web scraping (use web_scraper),
  web search (use tavily_search), or file downloads (use curl/wget).
dependencies: requests
metadata:
  emoji: "🌐"
---
# HTTP Request

## When to Use

- [ ] Call REST APIs (GET, POST, PUT, DELETE, PATCH)
- [ ] Test or probe API endpoints
- [ ] Fetch JSON or data from a URL
- [ ] Send request bodies and custom headers

## When NOT to Use

- [ ] Web search — use `tavily_search` (web_search tool)
- [ ] Scraping page content — use `web_scraper`
- [ ] Simple file downloads — use `curl` or `wget`
- [ ] GitHub operations — use `github` skill

## Setup

Install dependency: `pip install requests`

## Usage/Commands

```bash
python {skill_path}/request.py URL [options]
```

| Option | Description |
|--------|-------------|
| `--method GET|POST|PUT|DELETE|PATCH` | HTTP method (default: GET) |
| `--data '{"key": "value"}'` | JSON request body |
| `--header "Name: Value"` | Custom header (repeatable) |
| `--timeout N` | Timeout in seconds |
| `--format text|json|headers` | Output format |

## Notes

- For APIs requiring auth, use `--header "Authorization: Bearer <token>"`
- JSON body must be valid; escape quotes properly for shell
- Prefer this for structured API calls; use web_scraper for HTML extraction
