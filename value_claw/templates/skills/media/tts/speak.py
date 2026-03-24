#!/usr/bin/env python3
"""Multi-engine text-to-speech wrapper (gTTS + edge-tts)."""
import argparse
import asyncio
import os
import sys


def _tts_gtts(text: str, lang: str, slow: bool, output: str):
    try:
        from gtts import gTTS
    except ImportError:
        print("Error: gTTS is not installed. Run: pip install gTTS", file=sys.stderr)
        sys.exit(1)
    tts = gTTS(text=text, lang=lang, slow=slow)
    tts.save(output)
    print(f"Saved: {output} (gTTS, lang={lang})")


async def _tts_edge(text: str, voice: str, output: str):
    try:
        import edge_tts
    except ImportError:
        print("Error: edge-tts is not installed. Run: pip install edge-tts", file=sys.stderr)
        sys.exit(1)
    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(output)
    print(f"Saved: {output} (edge-tts, voice={voice})")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("text", help="Text to speak")
    parser.add_argument("--engine", default="gtts", choices=["gtts", "edge"])
    parser.add_argument("--lang", default="en", help="Language code for gTTS (default: en)")
    parser.add_argument("--voice", default="en-US-AriaNeural", help="Voice for edge-tts")
    parser.add_argument("--slow", action="store_true", help="Slow speech (gTTS only)")
    parser.add_argument("--output", "-o", default="speech.mp3", help="Output file path")
    args = parser.parse_args()

    os.makedirs(os.path.dirname(args.output) or ".", exist_ok=True)

    if args.engine == "edge":
        asyncio.run(_tts_edge(args.text, args.voice, args.output))
    else:
        _tts_gtts(args.text, args.lang, args.slow, args.output)


if __name__ == "__main__":
    main()
