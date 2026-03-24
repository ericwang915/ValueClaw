---
name: tts
description: "Text-to-speech — convert text to audio using gTTS or edge-tts. Use when: user asks to read text aloud, generate an audio file from text, or create a voiceover. NOT for: speech-to-text/transcription (use Deepgram or whisper), music generation, or audio editing."
dependencies: gTTS
metadata:
  emoji: "🔊"
---

# Text-to-Speech

Convert text to spoken audio files.

## When to Use

✅ **USE this skill when:**

- "Read this text aloud"
- "Generate an audio file of this paragraph"
- "Create a voiceover for this script"
- "Convert this text to speech"
- "Say this in Spanish"

## When NOT to Use

❌ **DON'T use this skill when:**

- Speech-to-text / transcription → use Deepgram or Whisper
- Music generation → use specialised music tools
- Audio editing or effects → use ffmpeg or audio editors
- Playing existing audio files → use system player

## Usage

### Basic TTS (using gTTS — Google Translate TTS)

```bash
python {skill_path}/speak.py "Hello, this is value_claw speaking." --output hello.mp3
```

### Options

```bash
# Different language
python {skill_path}/speak.py "Bonjour le monde" --lang fr

# Slow speed
python {skill_path}/speak.py "Important message" --slow

# Custom output path
python {skill_path}/speak.py "Text here" --output ~/audio/speech.mp3
```

### Alternative: edge-tts (higher quality, more voices)

If `edge-tts` is installed (`pip install edge-tts`):

```bash
python {skill_path}/speak.py "Hello world" --engine edge --voice en-US-AriaNeural
```

### Available edge-tts voices (examples)

- `en-US-AriaNeural` — Female, US English (default)
- `en-US-GuyNeural` — Male, US English
- `en-GB-SoniaNeural` — Female, British English
- `zh-CN-XiaoxiaoNeural` — Female, Chinese
- `ja-JP-NanamiNeural` — Female, Japanese
- `de-DE-KatjaNeural` — Female, German

List all voices: `python -m edge_tts --list-voices`

## Notes

- gTTS requires internet (uses Google Translate's TTS endpoint)
- edge-tts requires internet (uses Microsoft Edge's TTS service)
- Output format is MP3 by default
- For offline TTS, consider `pyttsx3` (lower quality but no network needed)

## Resources

| File | Description |
|------|-------------|
| `speak.py` | Multi-engine TTS wrapper (gTTS + edge-tts) |
