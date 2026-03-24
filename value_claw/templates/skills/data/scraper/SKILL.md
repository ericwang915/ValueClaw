---
name: web_scraper
description: >
  Scrape and extract content from web pages. Supports extracting text,
  links, headings, and structured data. Use when the user asks to read
  a web page, extract information from a URL, or scrape website content.
dependencies: requests, beautifulsoup4
---

## Instructions

Scrape and extract readable content from any web page.

### Prerequisites

Install dependencies: `pip install requests beautifulsoup4`

### Usage

```bash
python {skill_path}/scrape.py URL [--format text|json|links|headings]
```

Formats:
- `text` (default) — cleaned readable text
- `json` — structured JSON with title, text, links, headings
- `links` — all links on the page
- `headings` — all headings (h1–h6)

### Examples

- "Read the content of https://example.com"
- "Extract all links from https://news.ycombinator.com"
- "What does this page say? https://some-article.com/post"

## Resources

| File | Description |
|------|-------------|
| `scrape.py` | Generic web page scraper |
