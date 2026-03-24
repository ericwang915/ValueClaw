---
name: youtube
description: "Get YouTube video information, metadata, and transcripts/subtitles. Use when: user asks about a YouTube video, wants a video summary, needs a transcript, or asks to extract info from a YouTube URL. NOT for: downloading videos, live streams, or private/unlisted videos."
dependencies: yt-dlp, youtube-transcript-api
metadata:
  emoji: "▶️"
---

# YouTube Skill

Extract information and transcripts from YouTube videos via yt-dlp and youtube-transcript-api.

## When to Use

✅ **USE this skill when:**
- "What's this video about? https://youtube.com/watch?v=xyz"
- "Get the transcript of this video"
- "Search YouTube for Python tutorials"
- "Video title, duration, and description"
- User provides a YouTube URL and wants metadata or transcript

## When NOT to Use

❌ **DON'T use this skill when:**
- Downloading videos or audio → use yt-dlp directly with download opts
- Live streams → transcript availability may be limited
- Private or unlisted videos → access may be restricted

## Usage/Commands

```bash
python {skill_path}/youtube_info.py URL [command] [options]
```

Commands:
- `info` (default) — video title, duration, views, description
- `transcript` — full transcript/subtitles
- `search` — search YouTube for videos (uses URL arg as search query)

Options:
- `--lang en` — transcript language (default: en)
- `--format json` — output as JSON
- `--max 5` — max results for search (default: 5)

### Examples

- "What's this video about? https://youtube.com/watch?v=xyz" → `python {skill_path}/youtube_info.py <URL> info`
- "Get the transcript of this video" → `python {skill_path}/youtube_info.py <URL> transcript`
- "Search YouTube for Python tutorials" → `python {skill_path}/youtube_info.py "Python tutorials" search`

## Notes

- Install dependencies: `pip install yt-dlp youtube-transcript-api`
- Transcript availability depends on whether the video has captions
