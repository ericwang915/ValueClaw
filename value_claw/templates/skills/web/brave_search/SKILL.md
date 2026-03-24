---
name: brave_search
description: >
  Search the web using the Brave Search API. Use when the user requests a web search
  via Brave or if you want an alternative to the default search.
dependencies: requests
metadata:
  emoji: "🦁"
---
# Brave Web Search

## Instructions

Run `python {skill_path}/brave.py "your search query"`

## Setup

1. Get a free API key at [brave.com/search/api/](https://brave.com/search/api/)
2. Add to your `value_claw.json`:
   ```json
   "skills": {
     "brave": { "apiKey": "BSA..." }
   }
   ```
   Or set the environment variable: `BRAVE_API_KEY`

## Usage Examples

```bash
python {skill_path}/brave.py "latest advancements in quantum computing"
```
```bash
python {skill_path}/brave.py "Tesla stock news today"
```
