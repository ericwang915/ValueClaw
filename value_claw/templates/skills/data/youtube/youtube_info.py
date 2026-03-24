#!/usr/bin/env python3
"""Extract YouTube video info and transcripts."""

import argparse
import json
import sys


def _try_import(pkg, install_name):
    try:
        return __import__(pkg)
    except ImportError:
        print(f"Error: {install_name} not installed.  Run: pip install {install_name}",
              file=sys.stderr)
        sys.exit(1)


def get_info(url: str) -> dict:
    yt_dlp = _try_import("yt_dlp", "yt-dlp")
    opts = {
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
    }
    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=False)

    return {
        "title": info.get("title", ""),
        "channel": info.get("uploader", ""),
        "duration": info.get("duration", 0),
        "durationFormatted": _format_duration(info.get("duration", 0)),
        "views": info.get("view_count", 0),
        "likes": info.get("like_count"),
        "uploadDate": info.get("upload_date", ""),
        "description": (info.get("description") or "")[:1000],
        "url": info.get("webpage_url", url),
        "thumbnail": info.get("thumbnail", ""),
    }


def get_transcript(url: str, lang: str = "en") -> list[dict]:
    _try_import("yt_dlp", "yt-dlp")
    ytt = _try_import("youtube_transcript_api", "youtube-transcript-api")

    video_id = _extract_video_id(url)
    if not video_id:
        raise ValueError(f"Could not extract video ID from: {url}")

    api = ytt.YouTubeTranscriptApi()
    try:
        transcript = api.fetch(video_id, languages=[lang])
    except Exception:
        transcript = api.fetch(video_id)

    return [
        {
            "start": round(entry.start, 1),
            "duration": round(entry.duration, 1),
            "text": entry.text,
        }
        for entry in transcript
    ]


def search_youtube(query: str, max_results: int = 5) -> list[dict]:
    yt_dlp = _try_import("yt_dlp", "yt-dlp")
    opts = {
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
        "extract_flat": True,
        "playlist_items": f"1:{max_results}",
    }
    with yt_dlp.YoutubeDL(opts) as ydl:
        result = ydl.extract_info(f"ytsearch{max_results}:{query}", download=False)

    entries = result.get("entries", [])
    return [
        {
            "title": e.get("title", ""),
            "url": e.get("url", ""),
            "channel": e.get("uploader", e.get("channel", "")),
            "duration": e.get("duration"),
        }
        for e in entries
    ]


def _extract_video_id(url: str) -> str | None:
    import re
    patterns = [
        r"(?:v=|/v/|youtu\.be/)([a-zA-Z0-9_-]{11})",
        r"^([a-zA-Z0-9_-]{11})$",
    ]
    for p in patterns:
        m = re.search(p, url)
        if m:
            return m.group(1)
    return None


def _format_duration(seconds: int) -> str:
    if not seconds:
        return "N/A"
    h, remainder = divmod(seconds, 3600)
    m, s = divmod(remainder, 60)
    if h:
        return f"{h}:{m:02d}:{s:02d}"
    return f"{m}:{s:02d}"


def main():
    parser = argparse.ArgumentParser(description="YouTube video info & transcripts.")
    parser.add_argument("url", help="YouTube URL or search query")
    parser.add_argument("command", nargs="?", default="info",
                        choices=["info", "transcript", "search"])
    parser.add_argument("--lang", default="en", help="Transcript language")
    parser.add_argument("--max", type=int, default=5, help="Max search results")
    parser.add_argument("--format", choices=["text", "json"], default="text")
    args = parser.parse_args()

    try:
        if args.command == "info":
            data = get_info(args.url)
            if args.format == "json":
                print(json.dumps(data, indent=2, ensure_ascii=False))
            else:
                print(f"Title: {data['title']}")
                print(f"Channel: {data['channel']}")
                print(f"Duration: {data['durationFormatted']}")
                print(f"Views: {data['views']:,}")
                if data["likes"]:
                    print(f"Likes: {data['likes']:,}")
                print(f"Uploaded: {data['uploadDate']}")
                print(f"URL: {data['url']}")
                if data["description"]:
                    print(f"\nDescription:\n{data['description']}")

        elif args.command == "transcript":
            entries = get_transcript(args.url, lang=args.lang)
            if args.format == "json":
                print(json.dumps(entries, indent=2, ensure_ascii=False))
            else:
                for e in entries:
                    ts = _format_duration(int(e["start"]))
                    print(f"[{ts}] {e['text']}")

        elif args.command == "search":
            results = search_youtube(args.url, max_results=args.max)
            if args.format == "json":
                print(json.dumps(results, indent=2, ensure_ascii=False))
            else:
                for i, r in enumerate(results, 1):
                    dur = _format_duration(r["duration"]) if r["duration"] else "?"
                    print(f"{i}. {r['title']}  [{dur}]")
                    print(f"   {r['channel']}")
                    print(f"   {r['url']}")
                    print()

    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
