---
name: perplexity_search
description: >
  Search the web and get AI-synthesized answers using the Perplexity API (sonar-pro model). 
  Use when the user requests deep research or an AI summary of current events.
dependencies: requests
metadata:
  emoji: "🔮"
---
# Perplexity Web Search

## Instructions

Run `python {skill_path}/perplexity.py "your deep research question"`

## Setup

1. Get a Perplexity API key at [perplexity.ai](https://www.perplexity.ai/settings/api)
2. Add to your `value_claw.json`:
   ```json
   "skills": {
     "perplexity": { "apiKey": "pplx-..." }
   }
   ```
   Or set the environment variable: `PERPLEXITY_API_KEY`

## Usage Examples

```bash
python {skill_path}/perplexity.py "What are the key policy changes affecting semiconductor exports to China in 2026?"
```
```bash
python {skill_path}/perplexity.py "Summarize the latest Q3 earnings report for Apple Inc."
```
