---
name: twitter-capture
description: Captures knowledge from Twitter/X threads and posts, converting them into markdown notes pushed to the GitHub knowledge repo. Use when the user shares a tweet URL (x.com or twitter.com link) and wants to save, capture, or extract its content. Also trigger when the user says "capture this tweet", "save this thread", "grab that Twitter post", or pastes any x.com/twitter.com URL with intent to preserve the content. Works for single tweets, threads, and X Articles. Pairs with the knowledge-capture skill but handles external Twitter content instead of Claude session content.
updated: 2026-03-28T10:00:00Z
---

# Twitter Capture

Fetch Twitter/X post and thread content, clean it into a standalone markdown note, and push to the GitHub knowledge repo (`tieubao/til`).

## Prerequisites

- GitHub MCP Worker deployed and connected as a custom connector in Claude.ai
- For image capture: `assets` Cloudflare Worker deployed (R2 upload endpoint)
- Configure `R2_ASSETS_WORKER_URL` and `R2_UPLOAD_TOKEN` environment variables (or reference from user's context file)
- Internet access from the Claude.ai container (for fetching tweet content)
- Fallback: saves to `.learned/` locally if GitHub MCP is unavailable

## Triggers

### Explicit
- User pastes a tweet URL (`x.com/*/status/*` or `twitter.com/*/status/*`)
- "capture this tweet" / "save this thread" / "grab this post"
- "push this tweet to my notes"
- "extract the key points from this thread"

### Contextual
- User shares a tweet URL and asks for a summary, analysis, or takeaways
- After summarizing a thread, user says "save this" or "push it"

When the user shares a tweet URL without clear intent, ask: "Want me to capture this to your TIL repo, or just summarize it here?"

## Pipeline

### Step 1: Parse the URL

Extract `username` and `tweet_id` from the URL. Handle both formats:

```
https://x.com/USERNAME/status/TWEET_ID
https://twitter.com/USERNAME/status/TWEET_ID
```

Strip query parameters (`?s=20`, `?t=...`, etc.) and trailing slashes.

Also handle X Article URLs:
```
https://x.com/USERNAME/article/ARTICLE_ID
```

### Step 2: Fetch content

Use a two-API strategy. The choice of primary API depends on content type.

#### 2a. Detect if the post is an X Article

X Articles are long-form posts (up to 100,000 chars) with rich formatting: headings, bold/italic, inline images, embedded posts, cover images. They have a dedicated URL pattern (`/article/`) but are also accessible via the standard `/status/` URL.

**Always probe with ADHX first** to detect article vs. regular tweet:

```bash
curl -s "https://adhx.com/api/share/tweet/USERNAME/TWEET_ID"
```

Check the response structure:
- If `article` field exists and `article.content` is non-empty: this is an **X Article**
- If `article` field is absent and `text` is non-empty: this is a **regular tweet/thread**
- If both are empty: the post may be deleted, protected, or subscriber-only

ADHX response for X Articles provides:
- `article.title`: the author's title for the piece (critical, Jina loses this)
- `article.content`: full body as markdown (with `![](image_url)` syntax)
- `article.previewText`: first ~160 chars
- `article.coverImageUrl`: hero image URL
- `author.name`, `author.username`
- `engagement`: replies, retweets, likes, views

ADHX response for regular tweets provides:
- `text`: tweet body
- `author.name`, `author.username`
- `engagement`: replies, retweets, likes, views
- No `article` field

#### 2b. Fetch full content based on type

**For X Articles: use ADHX (primary)**

ADHX already returns the full article content from the probe in Step 2a. The `article.content` field contains the complete body with markdown formatting and image URLs. Use this directly.

Why ADHX over Jina for Articles: Jina returns the body content fine, but loses the author's title (returns "X" as the title). ADHX preserves `article.title` which is essential for generating a good note title.

**For regular tweets/threads: use Jina Reader (primary)**

```bash
curl -s "https://r.jina.ai/https://x.com/USERNAME/status/TWEET_ID" \
  -H "Accept: text/markdown"
```

Returns markdown with:
- Full tweet/thread text
- Images as markdown links (`[![Image](url)](url)`)
- Author name in the title line

No API key required for basic usage.

Why Jina over ADHX for regular tweets: Jina returns clean markdown directly. For regular tweets, ADHX only gives the single tweet's text and does not unroll threads into a combined body.

**Fallback chain:**
- If Jina fails on a regular tweet: fall back to ADHX `text` field
- If ADHX fails on an X Article: fall back to Jina (accept the missing title, generate one from content)
- If both fail: tell the user extraction failed and ask them to paste the thread content directly into chat. Do not silently skip.

#### 2c. X Article-specific considerations

X Articles can contain:
- **Rich formatting**: headings (H1-H4), bold, italic, strikethrough, blockquotes. ADHX preserves these as markdown. Jina also preserves them.
- **Inline images**: charts, screenshots, diagrams scattered throughout the body. Both APIs return image URLs from `pbs.twimg.com`.
- **Embedded X posts**: quotes of other tweets within the article. ADHX renders these as part of the content. Preserve them as blockquotes.
- **Cover images**: the hero image at the top. Only ADHX provides this via `article.coverImageUrl`.
- **Subscriber-only articles**: these will return empty content from both APIs. Tell the user the article is behind a paywall.

### Step 3: Detect content type

| Signal | Type | Typical source |
|--------|------|----------------|
| Single tweet, < 280 chars, one insight | TIL | Quick takes, hot takes |
| Thread with multiple connected tweets | Article | Twitter threads (most common) |
| X Article (ADHX `article` field present) | X Article | Long-form posts with title, headings, rich formatting |
| Single tweet with a specific fact/definition | Definition | Reference-style tweets |

Default to **X Article** when ADHX returns an `article` object. Default to **Article** for Jina-fetched threads. Default to **TIL** for single short tweets.

### Step 4: Clean content

Strip the following from fetched content:

**Metadata noise:**
- "X (formerly Twitter)" boilerplate
- Navigation elements, footer text, cookie notices
- "Sign up", "Log in", "Download the app" CTAs
- Engagement metrics ("1.2K likes", "234 retweets") unless the metrics ARE the content
- "Replying to @user" prefixes (keep @mentions within body text)
- Jina Reader header lines (`Title:`, `URL Source:`, `Markdown Content:`)

**Formatting cleanup:**
- Convert Jina's image links to standard markdown: `![description](url)`
- Remove redundant image link wrappers (Jina wraps images in clickable links)
- Preserve code blocks, bullet lists, and numbered lists as-is
- Remove Twitter-specific artifacts like "Show more" / "Read more" truncation markers
- Keep @mentions and #hashtags in body text (they provide context)

**Content quality:**
- If the thread references images that are essential to understanding (charts, diagrams, data), keep the image markdown links
- If images are decorative (memes, reaction images), drop them
- Preserve the author's paragraph structure; don't merge or split paragraphs

### Step 5: Format

**For X Article (long-form posts with `article` field from ADHX):**

```markdown
> Source: [@USERNAME](https://x.com/USERNAME/status/TWEET_ID) | YYYY-MM-DD
> Original title: "[article.title from ADHX]"

![Cover](COVER_IMAGE_R2_URL)

## Summary

[2-3 sentence summary of the article's core argument or insight. Written by Claude, not extracted from the article.]

## Article

[Full cleaned article content from `article.content`. Preserve the author's headings, structure, and voice. Keep all inline images that are essential to understanding. The article body often already has proper markdown formatting from ADHX -- preserve it.]

## Key Takeaways

- [Bullet 1: most important insight]
- [Bullet 2: second insight]
- [Bullet 3: if applicable]
```

Notes for X Articles:
- Use the author's original title from `article.title` for the "Original title" line. This preserves attribution.
- The note's own title (Step 6) should be topic-based and searchable, not necessarily the author's title.
- Include the cover image at the top if `article.coverImageUrl` exists. Upload to R2 first.
- The section header is "Article" not "Thread" since X Articles are single cohesive pieces, not stitched tweets.
- X Articles can be 10,000+ words. Do NOT truncate. Capture everything.

**For Article (threads -- multiple connected tweets, no `article` field):**

```markdown
> Source: [@USERNAME](https://x.com/USERNAME/status/TWEET_ID) | YYYY-MM-DD

## Summary

[2-3 sentence summary of the thread's core argument or insight. Written by Claude, not extracted from the thread.]

## Thread

[Full cleaned thread content. Preserve the author's structure and voice. Keep section breaks between distinct tweet boundaries if visible.]

## Key Takeaways

- [Bullet 1: most important insight]
- [Bullet 2: second insight]
- [Bullet 3: if applicable]
```

**For TIL (single tweets):**

```markdown
> Source: [@USERNAME](https://x.com/USERNAME/status/TWEET_ID) | YYYY-MM-DD

[Tweet content, cleaned and standalone.]
```

**For Definition:**

```markdown
> Source: [@USERNAME](https://x.com/USERNAME/status/TWEET_ID) | YYYY-MM-DD

## Definition

[The definition or concept from the tweet.]

## Context

[Why this matters, when you'd encounter it.]
```

### Step 6: Generate title

- Use the thread's core topic, not the author's name
- 3-8 words, specific, searchable
- Examples:
  - "Bitcoin ETF sell-off mechanics Feb 2025" (not "Jeff Park's thread")
  - "Structured concurrency in Python asyncio" (not "Cool thread about async")
  - "YC advice on pricing SaaS products" (not "Twitter thread on pricing")

### Step 7: Pick tags

1-3 tags from the content domain. Include the author's Twitter handle as a tag if they're a known domain expert (e.g., `jeff-park` for crypto/macro analysis).

Common patterns:
- Domain: `crypto`, `finance`, `ai`, `engineering`, `design`, `startup`
- Specific topic: `bitcoin-etf`, `options`, `asyncio`, `pricing`
- Author (if notable): `author-handle`

### Step 8: Handle images

**For images in the thread content:**

If images are essential to understanding (charts, data, diagrams):

1. Download the image from the Twitter CDN URL (`pbs.twimg.com/media/...`)
2. Upload to R2 via the assets worker:

```bash
# Download
curl -sL "https://pbs.twimg.com/media/XXXXX.jpg" -o /tmp/tweet-img.jpg

# Upload to R2
RESPONSE=$(curl -s -X POST $R2_ASSETS_WORKER_URL/upload \
  -H "Authorization: Bearer $R2_UPLOAD_TOKEN" \
  -H "Content-Type: image/jpeg" \
  -H "X-Filename: tweet-TWEET_ID-N" \
  --data-binary @/tmp/tweet-img.jpg)

IMAGE_URL=$(echo "$RESPONSE" | python3 -c "import sys,json; print(json.load(sys.stdin)['url'])")

rm -f /tmp/tweet-img.jpg
```

3. Replace the Twitter CDN URL in the markdown body with the R2 URL

**If image upload fails or R2 is unavailable:** Keep the original Twitter CDN URLs. They may expire eventually, but the text content is what matters most.

**For cover images on X Articles:** Upload the cover image and include it at the top of the note body.

### Step 9: Push to GitHub

Use the `Github MCP Worker:push_note` tool:

```
Tool: Github MCP Worker:push_note
Parameters:
  title: "Bitcoin ETF sell-off mechanics Feb 2025"
  content: "[cleaned markdown body]"
  tags: ["crypto", "bitcoin-etf", "options", "jeff-park"]
  source: "Twitter thread"
```

**Source field convention:**
- Single tweet: `"Twitter post"`
- Thread: `"Twitter thread"`
- X Article: `"X Article"`
- Append author: `"Twitter thread by @username"`

### Step 10: Confirm

After pushing:
```
Captured: "Bitcoin ETF sell-off mechanics Feb 2025"
Tags: crypto, bitcoin-etf, options, jeff-park
Source: Twitter thread by @dgt10011
Path: 2026/03/2026-03-27-bitcoin-etf-sell-off-mechanics-feb-2025.md
```

Include the GitHub link if returned by the tool.

## Batch mode

When the user shares multiple tweet URLs at once:

1. List the URLs with a proposed title for each
2. Wait for user confirmation ("capture all" or selective)
3. Process each sequentially via the pipeline above
4. Report results as a summary table

## Edge cases

**Thread with quoted tweets:** Include the quoted tweet content inline, prefixed with a blockquote (`>`) and attributed to the quoted author.

**Thread with polls:** Describe the poll options and results as a markdown list. Polls are ephemeral content, so capturing the snapshot is valuable.

**Deleted or protected tweets:** Jina/ADHX will fail. Tell the user the tweet is unavailable and ask them to paste the content manually.

**Very long threads (20+ tweets):** These are common for technical deep-dives. Do NOT truncate. Capture the full content. The TIL repo is an Obsidian vault where long notes are fine.

**Tweets in non-English languages:** Capture in the original language. Add a `language: XX` tag. Do NOT auto-translate unless the user asks.

## Integration with knowledge-capture

This skill and `knowledge-capture` share the same output path (GitHub MCP `push_note` to `tieubao/til`). The difference:

| | knowledge-capture | twitter-capture |
|---|---|---|
| Source | Claude chat session | External Twitter URL |
| Trigger | "save this" / "checkpoint" | Tweet URL pasted |
| Content origin | Claude's explanation | Someone else's content |
| Cleaning | Strip conversational artifacts | Strip Twitter UI artifacts |
| Attribution | `source: "Claude.ai chat"` | `source: "Twitter thread by @user"` |

Both skills can be used in the same conversation. For example: user shares a tweet, discusses it with Claude, then captures both the tweet (twitter-capture) and Claude's analysis (knowledge-capture) as separate notes.

## Important rules

1. **Always confirm before pushing.** Preview the title, tags, and a brief summary. Never auto-push.
2. **Attribute the author.** The note must include the source URL and author handle. This is someone else's content, not Claude's.
3. **Quality gate.** If the tweet is trivial (a meme, a one-word reply, pure self-promotion), tell the user it's not worth capturing and explain why. Same standard as knowledge-capture: a noisy repo is worse than a sparse one.
4. **One note per thread.** A thread is one note, not one note per tweet in the thread.
5. **Images go to R2, markdown goes to GitHub.** Same rule as knowledge-capture.
6. **Don't editorialize in the thread body.** The "Thread" section should faithfully represent the author's content. Claude's analysis goes in "Summary" and "Key Takeaways" only.
7. **Respect the author's voice.** Don't rewrite their sentences. Clean formatting artifacts, not writing style.