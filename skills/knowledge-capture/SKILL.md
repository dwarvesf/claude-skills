---
name: knowledge-capture
description: Captures learning moments from Claude sessions and persists them to Capacities via X-Callback URL or MCP. Use when the user says "save this to Capacities", "push this to my notes", "capture this", "extract my learnings", "checkpoint", or runs /learned. Also triggers at the end of sessions with significant learning content, or when Claude explains a root cause, makes an architectural decision, or breaks a debugging spiral. Works in Claude.ai Chat, Cowork (via Desktop Commander bash), and Claude Code (via /learned slash command).
---

# Knowledge Capture

Capture learning moments from Claude sessions and persist them to Capacities.

## Prerequisites

- macOS with Capacities desktop app running (for X-Callback URL push)
- For Claude Desktop/Cowork: Desktop Commander or similar bash MCP server installed
- For Claude Code: /learned and /push-learned commands installed at ~/.claude/commands/
- Fallback: saves to ./.learned/ (project-local) or ~/.learned/ (no project context) if Capacities is unavailable

## Triggers

### Explicit (user-initiated)
- "save this to Capacities"
- "push this to my notes"
- "capture this" or "extract my learnings"
- "checkpoint" (scans conversation since last checkpoint)
- /learned (Claude Code slash command)

### Auto-detect (suggest to user, never push without confirmation)
- Claude explains a root cause during debugging
- Claude makes a key architectural decision after code generation
- Claude breaks a debugging spiral with a concept explanation
- End of a session with 3+ substantive explanations

When auto-detecting, say: "That explanation about [topic] seems worth capturing. Want me to push it to Capacities?"

## Pipeline

### Step 1: Detect content type

| Signal | Type | Capacities object |
|--------|------|-------------------|
| Clear question + answer | Definition | Definition type |
| Short single concept, < 500 words | Atomic note (TIL) | Atomic note type |
| Multi-section, long explanation | Page (Article) | Page type |

Default to Atomic note if ambiguous.

### Step 2: Clean content

Strip ALL conversational artifacts:
- Openers: "Sure, here's...", "Great question!", "Let me explain..."
- Closers: "Let me know if...", "Want me to...", "Hope this helps!"
- Meta-commentary: "As I mentioned earlier...", "In our previous discussion..."
- Prompt improvement sections (from the prompt-improve workflow)
- References to Claude, the AI, or "this conversation"
- Key decision callout wrappers (fold substance into body, discard wrapper)

The note should read as a standalone reference, not a chat transcript.

### Step 3: Format

**For Definition:**
```markdown
## Question
[The question, clearly stated]

## Answer
[The answer, clean and direct]
```

**For Atomic note:**
```markdown
[Start directly with content. No heading needed, title is set separately.]
[End with relevant tags as hashtags: #topic #subtopic]
```

**For Page:**
```markdown
## [Section heading]
[Content organized by logical sections]
[End with tags: #topic #subtopic]
```

### Step 4: Generate title

- 3-8 words, specific, searchable
- No "How to" or "Guide to" prefixes unless it genuinely is a how-to
- Use the core concept as the title: "Python asyncio event loop internals" not "Learning about async"

### Step 5: Push to Capacities

Build the X-Callback URL and execute:

```bash
python3 -c "
import urllib.parse

title = '''[TITLE]'''
body = '''[MARKDOWN BODY]'''
obj_type = '[Definition|Atomic note|Page]'  # mapped to Capacities type

# Map to Capacities type keywords
type_map = {
    'Definition': 'definition',
    'Atomic note': 'note', 
    'Page': 'page'
}
capacities_type = type_map.get(obj_type, 'note')

url = f'capacities://x-callback-url/createNewObject?spaceId=YOUR_SPACE_ID&typeKeyword={capacities_type}&title={urllib.parse.quote(title)}&mdContent={urllib.parse.quote(body)}'
print(url)
" | xargs open
```

Replace YOUR_SPACE_ID with the user's Capacities space ID (from notion-reference.md or ask the user).

### Step 6: Confirm

After pushing, confirm with the user:
```
Pushed to Capacities: "[Title]" (Atomic note)
Tags: #topic #subtopic
```

## Fallback

If the `open capacities://...` command fails (app not running, URL too long):

Save each capture as a separate file in the project-local `.learned/` directory (or `~/.learned/` if no project context):

```bash
# Use project-local dir if in a git repo, otherwise home-level
if git rev-parse --show-toplevel &>/dev/null; then
  DIR="$(git rev-parse --show-toplevel)/.learned"
else
  DIR=~/.learned
fi
mkdir -p "$DIR"

# Generate slug from title: lowercase, spaces to hyphens, strip special chars
SLUG=$(echo "[TITLE]" | tr '[:upper:]' '[:lower:]' | sed 's/[^a-z0-9]/-/g' | sed 's/--*/-/g' | sed 's/^-//;s/-$//')
DATE=$(date +%Y-%m-%d)
FILEPATH="${DIR}/${DATE}-${SLUG}.md"

cat > "$FILEPATH" << 'EOF'
---
title: [TITLE]
type: [Definition|Atomic note|Page]
date: [ISO date]
tags: [comma-separated]
pushed: false
---

[MARKDOWN BODY]
EOF
```

Tell the user: "Capacities wasn't available. Saved to [filepath]. Run `/push-learned` later to push to Capacities."

## Batch mode

When the user says "extract my learnings" or "checkpoint":

1. Scan the current conversation context for learning moments
2. Identify candidates: explanations, root causes, architectural decisions, concept breakdowns
3. Preview the list: "I found 4 learning moments. Here's what I'd capture: [list titles]"
4. Wait for user confirmation
5. Push each one with 1.5s delay between pushes (Capacities needs time to process)

## Claude Code integration

For Claude Code, this skill's logic is split into:
- `/learned` command: cherry-pick the last response and push immediately
- `/push-learned` command: batch push all files from ./.learned/ directory
- CLAUDE.md auto-capture rules: silently save each learning to ./.learned/ during coding (one file per capture, named `YYYY-MM-DD-slug.md`)

These slash commands should be installed at `~/.claude/commands/learned.md` and `~/.claude/commands/push-learned.md`. The CLAUDE.md addition goes into the user's global CLAUDE.md.

## Important rules

1. **Never auto-push without user confirmation.** Always preview what will be captured.
2. **Strip all conversational fluff.** Notes should be standalone references.
3. **One note per concept.** Don't bundle unrelated learnings into one note.
4. **Tags are plain text hashtags in the body.** Capacities X-Callback URL doesn't support a tags parameter.
5. **Images and diagrams:** Currently text-only push. SVG/image capture requires the R2 image bucket (not yet built). Flag to user if content has important visuals.
