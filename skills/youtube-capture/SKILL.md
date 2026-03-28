---
name: youtube-capture
description: Captures knowledge from YouTube videos by extracting transcripts and converting them into markdown notes pushed to the GitHub knowledge repo. Use when the user shares a YouTube URL (youtube.com or youtu.be link) and wants to save, capture, or extract its content. Also trigger when the user says "capture this video", "save this talk", "grab that video transcript", or pastes any YouTube URL with intent to preserve the content. Works for standard videos, conference talks, podcasts, and tutorials. Pairs with the knowledge-capture skill but handles external YouTube content instead of Claude session content.
updated: 2026-03-28T10:00:00Z
---

# YouTube Capture

Fetch YouTube video transcripts, clean them into standalone markdown notes, and push to the GitHub knowledge repo (`tieubao/til`).

## Prerequisites

- GitHub MCP Worker deployed and connected as a custom connector in Claude.ai
- `web_fetch` and `web_search` tools available (used for Layer 3 fallback and metadata)
- Node.js + npm available in the container (for Layer 1 extraction)
- npm packages installed in `/home/claude`: `youtube-transcript`, `undici` (auto-installed on first run)
- For thumbnail capture: `assets` Cloudflare Worker deployed (R2 upload endpoint)
- Configure `R2_ASSETS_WORKER_URL` and `R2_UPLOAD_TOKEN` environment variables (or reference from user's context file)
- Fallback: saves to `.learned/` locally if GitHub MCP is unavailable

## Triggers

### Explicit

- User pastes a YouTube URL (`youtube.com/watch?v=*` or `youtu.be/*`)
- "capture this video" / "save this talk" / "grab this transcript"
- "push this video to my notes"
- "extract the key points from this video"

### Contextual

- User shares a YouTube URL and asks for a summary or takeaways
- After discussing a video, user says "save this" or "push it"

When the user shares a YouTube URL without clear intent, ask: "Want me to capture this to your TIL repo, or just summarize it here?"

## Pipeline

### Step 1: Parse the URL

Extract `video_id` from the URL. Handle all formats:

```
https://www.youtube.com/watch?v=VIDEO_ID
https://youtube.com/watch?v=VIDEO_ID
https://youtu.be/VIDEO_ID
https://www.youtube.com/watch?v=VIDEO_ID&t=120
https://www.youtube.com/embed/VIDEO_ID
https://youtube.com/shorts/VIDEO_ID
```

Strip query parameters (`&t=`, `&list=`, `&si=`, etc.) except `v=`. Extract the 11-character video ID.

### Step 2: Fetch video metadata

Use the **oembed API** to get structured metadata instantly. This works from any IP, no auth needed:

```bash
curl -s "https://noembed.com/embed?url=https://www.youtube.com/watch?v=VIDEO_ID"
```

Returns JSON with:
- `title`: video title
- `author_name`: channel name
- `author_url`: channel URL
- `thumbnail_url`: thumbnail image URL

This is the most reliable metadata source. It works for any public video, never gets rate-limited, and returns structured data (not HTML scraping).

If noembed fails, fall back to `web_search` for `youtube VIDEO_ID` and extract metadata from search snippets.

### Step 3: Fetch transcript

**Critical context:** YouTube blocks all cloud IPs (AWS, GCP, Azure, and Anthropic's container IPs). The `youtube-transcript-api` Python library, `yt-dlp`, YouTube's Innertube API, and Jina Reader on YouTube URLs all fail from this environment. Transcript extraction must go through third-party transcript sites.

#### 3a. Primary: youtube-transcript npm package with proxy

The `youtube-transcript` npm package works from the Claude.ai container when provided a proxy-aware `fetch` function via undici's `ProxyAgent`. This gives structured data with timestamps.

**Setup (first time only):**
```bash
cd /home/claude
npm init -y 2>/dev/null
npm install youtube-transcript undici 2>/dev/null
```

**Extraction script:**
```bash
cat > /home/claude/yt-extract.mjs << 'SCRIPT'
import { ProxyAgent, fetch as undiciFetch } from 'undici';
import { YoutubeTranscript } from './node_modules/youtube-transcript/dist/youtube-transcript.esm.js';

const videoId = process.argv[2];
if (!videoId) { console.error('Usage: node yt-extract.mjs VIDEO_ID'); process.exit(1); }

const proxyUrl = process.env.HTTPS_PROXY;
const dispatcher = new ProxyAgent({
  uri: proxyUrl,
  requestTls: { rejectUnauthorized: false }
});
const proxyFetch = (url, opts = {}) => undiciFetch(url, { ...opts, dispatcher });

try {
  const segments = await YoutubeTranscript.fetchTranscript(videoId, { fetch: proxyFetch });
  const result = {
    videoId,
    segmentCount: segments.length,
    totalWords: segments.map(s => s.text).join(' ').split(' ').length,
    segments: segments.map(s => ({
      offset: s.offset,
      duration: s.duration,
      text: s.text
    }))
  };
  console.log(JSON.stringify(result));
} catch(e) {
  console.error(JSON.stringify({ error: e.constructor.name, message: e.message }));
  process.exit(1);
}
SCRIPT

node /home/claude/yt-extract.mjs VIDEO_ID
```

**What this provides:**
- Full transcript with per-segment timestamps (offset in ms, duration in ms)
- Works for any public video with captions (auto-generated or manual)
- Structured JSON output for clean parsing
- Language selection via `{ lang: 'en' }` option

**Known failure modes:**
- `YoutubeTranscriptTooManyRequestError`: CAPTCHA triggered. YouTube rate-limits per IP. Recovery takes 1-10 minutes. Do not retry the same video immediately -- fall through to Layer 2/3.
- `YoutubeTranscriptVideoUnavailableError`: video is private, deleted, or age-restricted
- `YoutubeTranscriptDisabledError`: creator disabled captions on this video
- `YoutubeTranscriptNotAvailableError`: no captions exist at all (no auto-generated either)

**Rate-limit behavior (tested March 2026):** YouTube rate-limits per video+IP combination. After 3-5 requests to the same video in quick succession, that specific video gets blocked. Other videos on the same IP may still work. The block clears after a few minutes. The container's egress proxy IP is shared, so other sessions' YouTube requests can consume quota too.

**Why this works:** Node.js native `fetch` does NOT respect the container's `HTTPS_PROXY` env var. The `undici` package provides a `ProxyAgent` that routes requests through the container's egress proxy, which is how `curl` reaches YouTube. The `youtube-transcript` package accepts a custom `fetch` function, so we inject the proxy-aware version.

#### 3b. Fallback Layer 2: curl watch page + captionTracks parse

If Layer 1 fails (CAPTCHA or rate limit), try extracting directly via curl, which uses the container proxy natively:

```bash
python3 /home/claude/yt-transcript-extract.py VIDEO_ID --json
```

This script implements both Layer 1 (Node) and Layer 2 (curl) internally:

1. Fetch `youtube.com/watch?v=VIDEO_ID` via curl with browser User-Agent and `CONSENT=YES+1` cookie
2. Parse `captionTracks` from the `ytInitialPlayerResponse` JSON embedded in the HTML
3. Fetch the timedtext XML URL from the first English caption track
4. Parse `<text start="..." dur="...">` segments from the XML

The script tries Layer 1 first, then falls through to Layer 2 automatically. It outputs JSON with segments, timestamps, and word count.

**When Layer 2 also fails:** Both layers share the same egress IP, so if YouTube is blocking at the IP level (not just per-video), Layer 2 will fail too. This is when Layer 3 (web_search) becomes essential.

#### 3c. Fallback Layer 3: web_search for transcript pages

If both automated layers fail (both share the same egress IP), fall back to searching for the transcript on third-party sites:

```
web_search: "VIDEO_TITLE" "CHANNEL_NAME" transcript
```

Or: `web_search: "VIDEO_ID" transcript`

Known working sources (as of March 2026):
- `podscripts.co` -- podcast/YouTube transcripts with timestamps, free, good coverage
- `recapio.com` -- AI summaries + transcripts
- Creator-owned sites -- some channels host their own transcripts
- Blog posts, Reddit threads, or articles that include the full transcript

Use `web_fetch` on the most promising result to extract the transcript text. The `web_search` and `web_fetch` tools go through Anthropic's own infrastructure (different IP pool), so they work even when the container's egress proxy is rate-limited by YouTube.

**This layer is what makes the chain reliable.** Layers 1-2 give structured timestamped data when they work. Layer 3 gives unstructured text but works when YouTube blocks the container IP entirely.

#### 3d. Known paywalled/broken sources to skip

Do NOT rely on these as primary sources:
- **YTScribe** (`ytscribe.com`): paywalled as of early 2026, free tier is gone
- **youtubetranscript.com**: JS-rendered, curl/web_fetch returns empty shell
- **Tactiq**: requires their Chrome extension for most videos
- **Supadata**: requires API key ($)
- **TranscriptAPI.com**: requires API key (100 free credits, then paid)

#### 3e. Last resort: ask the user

If no automated method works, tell the user:

"I couldn't extract the transcript automatically. You can:
1. Copy the transcript from YouTube (click '...' below the video > 'Show transcript') and paste it here
2. Use a browser extension like YTScribe or Tactiq to grab it
3. If the video has no captions at all, transcription requires a paid AI service"

Do NOT silently skip or fabricate a transcript.

### Step 4: Detect content type

| Signal | Type | Typical source |
|--------|------|----------------|
| < 1000 words, single topic, quick explainer | TIL | Short tutorials, tips |
| 1000-5000 words, structured talk or tutorial | Article | Conference talks, how-tos |
| 5000+ words, long-form discussion | Article | Podcasts, interviews, lectures |
| Video is primarily a conversation/interview | Article | Podcasts, panel discussions |

Default to **Article** for most videos. Use **TIL** only for genuinely short, single-insight videos.

### Step 5: Clean content

YouTube transcripts (especially auto-generated) are messy. Apply these cleaning passes:

**Structural cleanup:**
- Remove filler words clusters: "um", "uh", "you know", "like" (when used as filler, not content)
- Fix run-on sentences where auto-captioning missed punctuation
- Add paragraph breaks at natural topic transitions (roughly every 3-5 sentences)
- Merge sentence fragments that were split across caption segments

**Content noise removal:**
- Sponsorship segments: "This video is brought to you by...", "Use code X for Y% off..."
- Self-promotion: "Don't forget to like and subscribe", "Hit the notification bell"
- Intro/outro boilerplate: "Hey guys, welcome back to...", "Thanks for watching..."
- Timestamp callouts that reference visual elements without context: "As you can see on screen..."

**Do NOT remove:**
- Technical terminology (even if it looks like jargon)
- Speaker names and attributions in multi-speaker content
- Code snippets or command-line examples mentioned verbally
- References to slides or visuals (note them as "[Visual: description]" if the reference adds context)

**For podcast/interview content:**
- Identify speakers where possible and add speaker labels
- Format as dialogue if the conversation structure is important to understanding
- If speaker identification is ambiguous, use "[Speaker 1]", "[Speaker 2]" etc.

### Step 6: Format

**For Article (most videos):**

```markdown
> Source: [VIDEO_TITLE](https://youtube.com/watch?v=VIDEO_ID)
> Channel: [CHANNEL_NAME] | Duration: [DURATION] | Date: YYYY-MM-DD

## Summary

[2-4 sentence summary of the video's core argument, insight, or teaching. Written by Claude, not extracted from the transcript. Focus on what someone would want to know before deciding to read the full transcript.]

## Transcript

[Full cleaned transcript. Preserve the speaker's structure and natural flow. Add paragraph breaks at topic transitions. For multi-speaker content, include speaker labels.]

## Key Takeaways

- [Bullet 1: most important insight or actionable point]
- [Bullet 2: second insight]
- [Bullet 3: if applicable]
- [Add more only if genuinely distinct points exist]
```

**For TIL (short videos < 1000 words):**

```markdown
> Source: [VIDEO_TITLE](https://youtube.com/watch?v=VIDEO_ID)
> Channel: [CHANNEL_NAME] | Date: YYYY-MM-DD

[Cleaned transcript content, standalone and self-contained.]
```

### Step 7: Generate title

- Use the video's core topic, not the video's clickbait title
- 3-8 words, specific, searchable
- Examples:
  - "Rust ownership model explained" (not "MIND BLOWN by Rust Memory Management")
  - "YC advice on B2B SaaS pricing" (not "This Changed How I Price My Product")
  - "State machines in React component design" (not "Senior React Developer Tips")
- If the video title is already clear and specific, use a shortened version of it

### Step 8: Pick tags

1-3 tags from the content domain. Include the channel name as a tag if they're a known domain expert (e.g., `3blue1brown` for math, `fireship` for web dev).

Common patterns:
- Domain: `ai`, `engineering`, `finance`, `design`, `startup`, `devops`
- Specific topic: `rust`, `react`, `kubernetes`, `options-pricing`
- Format: `conference-talk`, `tutorial`, `podcast`
- Channel (if notable): `channel-name`

### Step 9: Handle thumbnails (optional)

If the video has a relevant thumbnail (not just a face shot or clickbait image), capture it:

```bash
# Download YouTube thumbnail (these URLs are public, not blocked)
curl -sL "https://i.ytimg.com/vi/VIDEO_ID/maxresdefault.jpg" -o /tmp/yt-thumb.jpg

# Check if maxres exists (returns a small placeholder if not)
SIZE=$(stat -f%z /tmp/yt-thumb.jpg 2>/dev/null || stat -c%s /tmp/yt-thumb.jpg)
if [ "$SIZE" -lt 5000 ]; then
  # Fall back to high quality
  curl -sL "https://i.ytimg.com/vi/VIDEO_ID/hqdefault.jpg" -o /tmp/yt-thumb.jpg
fi

# Upload to R2
RESPONSE=$(curl -s -X POST $R2_ASSETS_WORKER_URL/upload \
  -H "Authorization: Bearer $R2_UPLOAD_TOKEN" \
  -H "Content-Type: image/jpeg" \
  -H "X-Filename: yt-VIDEO_ID-thumb" \
  --data-binary @/tmp/yt-thumb.jpg)

THUMB_URL=$(echo "$RESPONSE" | python3 -c "import sys,json; print(json.load(sys.stdin)['url'])")

rm -f /tmp/yt-thumb.jpg
```

Include at the top of the note body:
```markdown
![Thumbnail](THUMB_URL)
```

Skip thumbnail capture if:
- The thumbnail is a generic face/reaction shot (not informative)
- R2 upload fails (don't block the whole capture for a thumbnail)
- The user says they don't want it

### Step 10: Push to GitHub

Use the `Github MCP Worker:push_note` tool:

```
Tool: Github MCP Worker:push_note
Parameters:
  title: "Rust ownership model explained"
  content: "[cleaned markdown body]"
  tags: ["rust", "memory-management", "conference-talk"]
  source: "YouTube video by [CHANNEL_NAME]"
```

**Source field convention:**
- Standard video: `"YouTube video by [channel]"`
- Conference talk: `"YouTube talk by [speaker] at [conference]"`
- Podcast episode: `"YouTube podcast - [show name]"`

### Step 11: Confirm

After pushing:

```
Captured: "Rust ownership model explained"
Tags: rust, memory-management, conference-talk
Source: YouTube video by Let's Get Rusty
Path: 2026/03/2026-03-27-rust-ownership-model-explained.md
```

Include the GitHub link if returned by the tool.

## Long video handling

Videos over 5000 words (roughly 30+ minutes) need special treatment:

**Do NOT truncate.** Capture the full transcript. The TIL repo is an Obsidian vault where long notes are searchable and useful.

**Do add structure.** For long videos, insert section headers based on topic transitions in the transcript:

```markdown
## Transcript

### [Topic 1: e.g., "Background and motivation"]

[Transcript paragraphs for this section...]

### [Topic 2: e.g., "The core algorithm"]

[Transcript paragraphs for this section...]

### [Topic 3: e.g., "Benchmarks and results"]

[Transcript paragraphs for this section...]
```

These section headers are Claude's addition (not from the transcript) to make the note navigable. Keep them descriptive and specific.

## Batch mode

When the user shares multiple YouTube URLs at once:

1. List the URLs with a proposed title for each
2. Wait for user confirmation ("capture all" or selective)
3. Process each sequentially via the pipeline above
4. Report results as a summary table

## Edge cases

**Videos without captions:** Some videos have no auto-generated or manual captions. YTScribe will return empty or a 404. Tell the user the video has no available transcript.

**Non-English videos:** Capture in the original language. Add a `language: XX` tag. Do NOT auto-translate unless the user asks. If the user wants an English version, translate the transcript and note the original language.

**Live streams / premieres:** These often have delayed or missing transcripts. If the transcript is unavailable, tell the user to try again after YouTube has processed the auto-captions (usually a few hours after the stream ends).

**Music videos / mostly-visual content:** If the "transcript" is just lyrics or minimal dialogue, tell the user this video's value is visual/audio, not textual, and a transcript capture wouldn't be useful.

**Age-restricted videos:** Third-party transcript services may not be able to access these. Fall back to asking the user to paste the transcript.

**Shorts (< 60 seconds):** These are usually too short for an Article format. Default to TIL. The URL format is `youtube.com/shorts/VIDEO_ID` but the video ID works the same way.

## Integration with knowledge-capture and twitter-capture

All three skills share the same output path (GitHub MCP `push_note` to `tieubao/til`). The differences:

|                | knowledge-capture        | twitter-capture              | youtube-capture              |
|----------------|--------------------------|------------------------------|------------------------------|
| Source         | Claude chat session      | External Twitter URL         | External YouTube URL         |
| Trigger        | "save this" / checkpoint | Tweet URL pasted             | YouTube URL pasted           |
| Content origin | Claude's explanation     | Someone else's tweet/thread  | Someone else's video         |
| Cleaning       | Strip chat artifacts     | Strip Twitter UI artifacts   | Strip caption noise + filler |
| Attribution    | `source: "Claude.ai chat"` | `source: "Twitter thread by @user"` | `source: "YouTube video by [channel]"` |
| Typical size   | 200-2000 words           | 200-5000 words               | 1000-50000 words             |

All three skills can be used in the same conversation. For example: user shares a video link, discusses it with Claude, then captures both the video transcript (youtube-capture) and Claude's analysis (knowledge-capture) as separate notes.

## Important rules

1. **Always confirm before pushing.** Preview the title, tags, and a brief summary. Never auto-push.
2. **Attribute the creator.** The note must include the source URL and channel name. This is someone else's content, not Claude's.
3. **Quality gate.** If the video transcript is too thin (a 15-second clip), too noisy (unintelligible auto-captions), or not worth preserving as text (pure music, ASMR, visual-only content), tell the user it's not worth capturing and explain why. Same standard as knowledge-capture: a noisy repo is worse than a sparse one.
4. **One note per video.** A video is one note, not one note per section.
5. **Thumbnails go to R2, markdown goes to GitHub.** Same rule as the other capture skills.
6. **Don't editorialize in the transcript body.** The "Transcript" section should faithfully represent the speaker's words. Claude's analysis goes in "Summary" and "Key Takeaways" only.
7. **Respect the speaker's voice.** Clean formatting and filler, not speaking style.
8. **Transcript extraction is fragile.** YTScribe can change or go down. If extraction fails, be upfront about it and offer alternatives. Never fabricate or hallucinate transcript content.

## Known limitations and future improvements

**Current extraction pipeline (tested March 2026):**

| Priority | Method | Reliability | Notes |
|----------|--------|-------------|-------|
| Primary | `youtube-transcript` npm + undici ProxyAgent | High | Works for any video with captions. Gives timestamps. Requires npm setup. |
| Fallback | `web_search` + `web_fetch` on transcript sites | Medium | Depends on video being indexed by podscripts.co, recapio.com, etc. |
| Last resort | User pastes transcript | Always works | Manual step, but guaranteed |

**What does NOT work from cloud IPs (tested March 2026):**
- `youtube-transcript-api` (Python) -- YouTube blocks cloud IPs with "IpBlocked" error
- `yt-dlp` -- blocked (429 + bot detection + requires JS runtime)
- YouTube Innertube API (direct POST to `/youtubei/v1/player`) -- "Sign in to confirm you're not a bot"
- Jina Reader on YouTube URLs -- YouTube returns 429 to Jina's servers
- YTScribe -- paywalled, free tier removed
- Node.js native `fetch` to YouTube -- DNS fails because native fetch ignores the container's HTTPS_PROXY

**Critical discovery:** Node.js native `fetch` does NOT use the container's proxy env vars. The `undici` package with `ProxyAgent` is required to route Node.js HTTP requests through the container's egress proxy. This is why `curl` reaches YouTube but `youtube-transcript-api` (Python, uses `requests`) and `youtube-transcript` (Node, uses native `fetch`) fail by default. Injecting a proxy-aware `fetch` into the `youtube-transcript` package's options makes it work.

**What DOES work:**
- `youtube-transcript` npm + undici ProxyAgent -- full structured transcript with timestamps
- `noembed.com/embed?url=` -- reliable metadata (title, channel, thumbnail), never blocked
- `web_search` + `web_fetch` on third-party transcript sites -- works when the video is indexed
- YouTube thumbnail URLs (`i.ytimg.com/vi/VIDEO_ID/`) -- public, never blocked
- `curl` to YouTube (goes through container proxy) -- works but returns HTML/CAPTCHA pages

**Future improvements:**
- Test if the Python `youtube-transcript-api` also works with explicit proxy configuration (via `requests` proxy parameter)
- Build a self-hosted transcript CF Worker for use outside the Claude.ai container (Claude Code, Cowork)
- Evaluate TranscriptAPI.com (100 free credits) as an additional fallback for when the npm approach hits CAPTCHA