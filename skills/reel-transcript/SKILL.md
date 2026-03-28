---
name: reel-transcript
description: Extracts transcripts from short-form video URLs and files using Supadata MCP (primary) or local whisper (fallback). Use when the user shares a video URL from Instagram Reels, Facebook videos/reels, Threads video posts, TikTok, Twitter/X, or uploads any video file (mp4, mov, webm). Trigger on "transcribe this reel", "extract transcript from reel", "what does this reel say", "transcribe this video", or any instagram.com/reel/*, facebook.com/watch/*, facebook.com/reel/*, threads.net/*/post/*, tiktok.com/*, x.com/*/status/* URL. Pairs with knowledge-capture to push transcripts to the GitHub repo.
updated: 2026-03-28T08:56:00Z
---

# Reel Transcript

Extract transcripts from Instagram Reels, Facebook videos, Threads posts, TikToks, X/Twitter videos, and uploaded video files.

## Prerequisites

- **Supadata MCP** connected as a custom connector in Claude.ai (primary path)
- For fallback only: `ffmpeg`, `faster-whisper`, `yt-dlp` in the container

## Triggers

### Explicit

- User pastes an Instagram Reel URL (`instagram.com/reel/*` or `instagram.com/p/*`)
- User pastes a Facebook video URL (`facebook.com/watch/*`, `facebook.com/reel/*`, `fb.watch/*`)
- User pastes a Threads video URL (`threads.net/@*/post/*`)
- User pastes a TikTok URL (`tiktok.com/@*/video/*`)
- User pastes a Twitter/X video URL (`x.com/*/status/*`, `twitter.com/*/status/*`)
- User uploads a video file and asks for a transcript
- "transcribe this reel" / "what does this reel say" / "extract transcript"
- "capture this reel" (triggers reel-transcript + knowledge-capture)

### Contextual

- User shares any short video URL from a supported platform
- User uploads an mp4/mov/webm and wants text extraction

## Pipeline

### Step 1: Determine input type

**URL provided** -> Go to Step 2 (Supadata path)
**File uploaded** -> Go to Step 4 (Local whisper path)

### Step 2: Fetch metadata via Supadata (URL path)

Use the `Supadata:supadata_metadata` tool to get video context:

```
Tool: Supadata:supadata_metadata
Parameters:
  url: "<video_url>"
```

This returns: platform, author (username, displayName), description, tags, duration, stats (views, likes, comments), thumbnail URL, and creation date.

### Step 3: Fetch transcript via Supadata (URL path)

Use the `Supadata:supadata_transcript` tool:

```
Tool: Supadata:supadata_transcript
Parameters:
  url: "<video_url>"
```

By default (no `text` param), this returns **timestamped segments**. Set `text: true` only when you want flat text.

**Parameters:**
- `url` (required): The video URL
- `text` (optional): Set to `true` to get plain text string. Omit or set `false` to get timestamped segments.
- `chunkSize` (optional): Max characters per segment. Higher values merge small segments together. Cannot split below the platform's native caption granularity (~5s segments).
- `lang` (optional): Language code (e.g., "en", "vi") to request a specific language transcript
- `mode` (optional): Set to "auto" to force AI transcription when platform captions are unavailable

**Response formats:**

Timestamped segments (default, `text` omitted or `false`):
```json
{
  "lang": "en",
  "availableLangs": ["en"],
  "content": [
    {"text": "First sentence...", "offset": 142, "duration": 4681},
    {"text": "Second sentence...", "offset": 4883, "duration": 4761}
  ]
}
```
- `offset`: start time in milliseconds from video start
- `duration`: segment length in milliseconds

Plain text (`text: true`):
```json
{
  "lang": "en",
  "availableLangs": ["en"],
  "content": "The full transcript text..."
}
```

Async (longer videos, returns a job ID):
```json
{
  "jobId": "abc123"
}
```

If you get a `jobId`, poll with `Supadata:supadata_check_transcript_status`:
```
Tool: Supadata:supadata_check_transcript_status
Parameters:
  id: "<jobId>"
```

Poll every 3-5 seconds until status is "completed" or "failed".

**Credit usage:** 1 credit per transcript. AI-generated transcripts (when no captions exist) cost 2 credits per minute of video. The free tier has 100 credits/month.

**If Supadata fails**, fall through to Step 4 (local whisper). Common failure reasons:
- Video is private or deleted
- Platform temporarily blocking Supadata's servers
- No audio track in the video

### Step 4: Local whisper fallback (uploaded files or Supadata failure)

For uploaded files or when Supadata fails:

1. If the input is a URL and Supadata failed, try `yt-dlp`:
   ```bash
   yt-dlp --no-check-certificates -f "best[ext=mp4]" -o "/tmp/reel-%(id)s.%(ext)s" "URL" 2>&1
   ```
   Note: `yt-dlp` works for TikTok, X/Twitter, Reddit. It will fail (403) for all Meta platforms (Instagram, Facebook, Threads).

2. If the input is an uploaded file, find it at `/mnt/user-data/uploads/`.

3. Run the transcription script:
   ```bash
   python3 /home/claude/reel-transcribe.py <video_path> [model_size]
   ```

4. If the script doesn't exist, create it (see "Helper Script" section below).

**If both Supadata and local download fail** (Meta URLs without file upload):
Tell the user: "I couldn't fetch the transcript remotely. Save the video from the app and upload it here, and I'll transcribe it locally."

### Step 5: Format output

**Default: use timestamped segments** (omit `text` param). Format with human-readable timestamps:

```
**Transcript** (@username on Instagram, 14.7s)

[0:00] First sentence of the reel...
[0:04] Second sentence continues here...
[0:09] And so on through the video...

---
Language: en | Words: ~52 | Duration: 14.7s
Tags: #letthem #melrobbins
```

Convert `offset` from milliseconds to `M:SS` format: `Math.floor(offset/60000)` for minutes, `Math.floor((offset%60000)/1000)` for seconds.

**When to use `text: true` instead:**
- User only wants the raw text to copy/paste
- Feeding into knowledge-capture (the note body should be clean prose, not timestamped lines)
- Very short Reels (under 15s) where timestamps add noise

Include metadata when available (author, platform, duration, tags).

### Step 6: Optional - Push to knowledge repo

If the user says "capture this" or "save this", use the `Github MCP Worker:push_note` tool:

```
Tool: Github MCP Worker:push_note
Parameters:
  title: "[Reel topic/summary]"
  content: "[formatted transcript with metadata and source attribution]"
  tags: ["reel", "platform-name", "topic-tag"]
  source: "[Platform] video by @[username]"
```

## Helper Script

If `/home/claude/reel-transcribe.py` doesn't exist, create it:

```python
#!/usr/bin/env python3
"""
Reel/video transcription pipeline (local fallback).
Input: video file path (mp4, mov, etc.)
Output: JSON with transcript segments + full text
"""

import sys
import json
import subprocess
import tempfile
import os

def extract_audio(video_path, audio_path):
    cmd = [
        "ffmpeg", "-i", video_path,
        "-vn", "-acodec", "pcm_s16le",
        "-ar", "16000", "-ac", "1", "-y",
        audio_path
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg failed: {result.stderr}")

def transcribe(audio_path, model_size="tiny"):
    from faster_whisper import WhisperModel
    model = WhisperModel(model_size, device="cpu", compute_type="int8")
    segments, info = model.transcribe(audio_path, beam_size=5)
    
    result_segments = []
    full_text_parts = []
    for segment in segments:
        result_segments.append({
            "start": round(segment.start, 2),
            "end": round(segment.end, 2),
            "text": segment.text.strip()
        })
        full_text_parts.append(segment.text.strip())
    
    return {
        "language": info.language,
        "language_probability": round(info.language_probability, 3),
        "duration_seconds": round(info.duration, 1),
        "segment_count": len(result_segments),
        "word_count": len(" ".join(full_text_parts).split()),
        "segments": result_segments,
        "full_text": " ".join(full_text_parts)
    }

def main():
    if len(sys.argv) < 2:
        print(json.dumps({"error": "Usage: python3 reel-transcribe.py <video_path> [model_size]"}))
        sys.exit(1)
    
    video_path = sys.argv[1]
    model_size = sys.argv[2] if len(sys.argv) > 2 else "tiny"
    
    if not os.path.exists(video_path):
        print(json.dumps({"error": f"File not found: {video_path}"}))
        sys.exit(1)
    
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        audio_path = tmp.name
    
    try:
        extract_audio(video_path, audio_path)
        result = transcribe(audio_path, model_size)
        print(json.dumps(result, indent=2))
    finally:
        if os.path.exists(audio_path):
            os.unlink(audio_path)

if __name__ == "__main__":
    main()
```

## Advanced: Structured extraction

Supadata also supports AI-powered structured extraction from videos. Use `Supadata:supadata_extract` to pull structured data beyond just the transcript:

```
Tool: Supadata:supadata_extract
Parameters:
  url: "<video_url>"
  prompt: "Extract the main advice, who is speaking, and any books or resources mentioned"
  schema: {
    "type": "object",
    "properties": {
      "speaker": { "type": "string" },
      "main_advice": { "type": "string" },
      "resources_mentioned": { "type": "array", "items": { "type": "string" } },
      "tone": { "type": "string", "enum": ["motivational", "educational", "casual", "professional"] }
    }
  }
```

This is async. Use `Supadata:supadata_check_extract_status` to poll for results.

## Edge cases

**No speech detected:** Supadata returns minimal or empty content. Tell the user the video appears to have no speech (music-only, ambient, etc.).

**Non-English audio:** Supadata auto-detects language. Report the detected language. Use `lang` parameter if the user wants a specific language.

**Supadata rate limit:** Free tier is 1 req/sec, paid is 10/sec. If rate-limited, wait briefly and retry, or fall back to local whisper.

**Private or deleted videos:** Supadata can only access public videos. Tell the user the video isn't accessible and suggest uploading the file directly.

**Long videos (>5 min):** Supadata returns a jobId for async processing. Poll `supadata_check_transcript_status` until complete. For local fallback on long videos, suggest `base` model over `tiny` for better accuracy.

## Known limitations

| Layer | Platform | Status |
|-------|----------|--------|
| Supadata (primary) | Instagram, Facebook, Threads, TikTok, X, YouTube | Works for public videos |
| yt-dlp (fallback download) | TikTok, X, Reddit | Works |
| yt-dlp (fallback download) | Instagram, Facebook, Threads | Blocked (403) |
| Local whisper (fallback transcription) | Any uploaded file | Works |

## Integration

This skill pairs with:
- **knowledge-capture**: Push transcript to GitHub repo (`Github MCP Worker:push_note`)
- **twitter-capture**: For X/Twitter, twitter-capture handles tweet context; this skill handles video audio
- **youtube-capture**: For YouTube, youtube-capture has its own transcript pipeline; this skill can also handle YouTube via Supadata