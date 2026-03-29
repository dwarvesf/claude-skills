---
name: knowledge-capture
description: Captures learning moments from Claude sessions and persists them to a GitHub knowledge repo via the GitHub MCP Worker. Use when the user says "save this", "push this to my notes", "capture this", "extract my learnings", "checkpoint", or runs /learned. Also triggers at the end of sessions with significant learning content, or when Claude explains a root cause, makes an architectural decision, or breaks a debugging spiral. Works in Claude.ai Chat, Cowork (via Desktop Commander bash), and Claude Code (via /learned slash command).
updated: 2026-03-29T06:00:00Z
---

# Knowledge Capture

Capture learning moments from Claude sessions and persist them to the GitHub knowledge repo (`tieubao/til`).

## Prerequisites

- GitHub MCP Worker deployed and connected as a custom connector in Claude.ai
- For image capture: `assets` Cloudflare Worker deployed (R2 upload endpoint)
- For SVG-to-PNG: `cairosvg` Python package (Claude.ai container) or `rsvg-convert` (macOS)
- Fallback: saves to `.learned/` locally if GitHub MCP is unavailable

## Triggers

### Explicit (user-initiated)
- "save this" / "push this to my notes" / "push to GitHub"
- "capture this" or "extract my learnings"
- "checkpoint" (scans conversation since last checkpoint)
- /learned (Claude Code slash command)

### Auto-detect (suggest to user, never push without confirmation)
- Claude explains a root cause during debugging
- Claude makes a key architectural decision after code generation
- Claude breaks a debugging spiral with a concept explanation
- End of a session with 3+ substantive explanations

When auto-detecting, say: "That explanation about [topic] seems worth capturing. Want me to push it to GitHub?"

## Pipeline

### Step 1: Detect content type

| Signal | Type | Notes |
|--------|------|-------|
| User asked a question, Claude answered | Q&A | Most common pattern |
| "What is X" or concept lookup | Definition | Reference card for a term or concept |
| Short single concept, < 500 words, no question | TIL | Quick insight or fact |
| Multi-section, long explanation | Article | Longer reference |
| Comparison of tools, frameworks, approaches | Comparison | Table-driven, verdict-oriented |
| Design decisions with rationale and tradeoffs | Decision Record | ADR-style: context, decision, alternatives, consequences |
| Evaluation or scoring of a tool/approach | Evaluation | Rubric-scored, verdict at the end |
| Step-by-step workflow or process | Playbook | Sequential steps with decision points |
| Architecture, system design, or structural explanation | Architecture | Component descriptions, relationships, data flow |

Default to Q&A if the conversation had a question-answer flow. Use Definition when the answer is essentially "here's what this thing is" with no deeper investigation. Default to TIL if ambiguous and no clear question.

**Match the note structure to the content, not the other way around.** The 4 original types (Q&A, Definition, TIL, Article) are starting points. If the content is a comparison matrix, don't force it into Q&A format -- use a comparison structure with a table. If it's a decision with tradeoffs, use an ADR structure. The repo should feel like a library of diverse reference materials, not a monotonous stack of Q&A cards.

### Step 2: Clean content

Strip ALL conversational artifacts:
- Openers: "Sure, here's...", "Great question!", "Let me explain..."
- Closers: "Let me know if...", "Want me to...", "Hope this helps!"
- Meta-commentary: "As I mentioned earlier...", "In our previous discussion..."
- Prompt improvement sections (from the prompt-improve workflow)
- References to Claude, the AI, or "this conversation"
- Key decision callout wrappers (fold substance into body, discard wrapper)

The note should read as a standalone reference, not a chat transcript.

**Q&A-specific cleaning:** Rewrite the user's question to be clear and context-free. The original question might be sloppy, shorthand, or assume shared context ("why doesn't this work?" becomes "Why does Python's asyncio.run() raise RuntimeError inside Jupyter notebooks?"). The answer should be direct and self-contained, not a reply to someone.

### Step 3: Format

**Reference templates (use as starting points, not rigid molds):**

**For Q&A (most common):**
```markdown
## Question

[The question, rewritten to be clear, specific, and standalone]

## Answer

[The answer, clean and direct. Include code examples if the original had them.]

## Key Takeaway

[1-2 sentence summary of the core insight. Optional -- skip if the answer is already short enough.]
```

**For Definition (reference card):**
```markdown
## Definition

[Concise, precise definition of the term or concept. 1-3 sentences.]

## Context

[When you'd encounter this, why it matters, how it relates to adjacent concepts. Keep brief.]

## Example

[A concrete example, code snippet, or analogy. Optional -- skip if the definition is self-explanatory.]
```

**For TIL:**
```markdown
[Start directly with content. No heading needed, title is set separately.]
[Content should be standalone and self-contained.]
```

**For Article:**
```markdown
## [Section heading]
[Content organized by logical sections]
```

**For Comparison:**
```markdown
[Opening paragraph: what is being compared and why]

| Dimension | Option A | Option B | Option C |
|-----------|----------|----------|----------|
| [criterion 1] | [assessment] | [assessment] | [assessment] |
| [criterion 2] | [assessment] | [assessment] | [assessment] |

## Verdict

[Which option wins, for whom, under what conditions. Be opinionated.]
```

**For Decision Record (ADR-style):**
```markdown
## Context

[What prompted this decision. The problem or tradeoff being resolved.]

## Decision

[What was decided. Be specific.]

## Alternatives considered

[What was rejected and why. Brief per alternative.]

## Consequences

[What this means going forward. Both positive and negative.]
```

**For Evaluation:**
```markdown
[Brief description of what is being evaluated]

| Criterion | Score | Rationale |
|-----------|-------|-----------|
| [criterion] | [X/N] | [why this score] |

## Verdict: [ADOPT / BOOKMARK / SKIP]

[One paragraph summary with recommendation and conditions.]
```

**For Playbook:**
```markdown
## When to use

[The situation or trigger that calls for this playbook]

## Steps

### 1. [Step name]
[What to do, what to check, what output to expect]

### 2. [Step name]
[Continue. Include decision points: "If X, do Y. If Z, do W."]

## Common pitfalls

[What goes wrong and how to avoid it]
```

**For Architecture:**
```markdown
## Overview

[What this system/component does, one paragraph]

## Components

[Description of each component, its responsibility, and how it connects to others. Use a table or bullet list depending on count.]

## Data flow

[How data moves through the system. Include a diagram if available.]

## Key decisions

[Why it's built this way, not another way]
```

**Choosing the right format:** The templates above are reference patterns, not rigid molds. After detecting the content type, design the actual layout to fit the specific learning content and its context. Two notes of the same type can (and should) have different structures if the content calls for it.

**The layout design process:**
1. Read the content being captured. What are the key pieces of information?
2. Choose a type (Q&A, Comparison, Decision Record, etc.) as a starting point
3. Look at the reference template for that type
4. Adapt the sections to fit THIS specific content. Add sections the template doesn't have if the content needs them. Drop sections the template has if they'd be empty or forced. Rename sections if a different heading better describes what's in them.

**Examples of adaptive layout:**

A "Comparison" note about 3 CLI tools might use the standard table format. But a "Comparison" note about architectural approaches might work better as side-by-side prose sections with a "when to use which" summary, because the nuances don't compress into table cells.

A "Q&A" about a simple API gotcha uses the standard Question/Answer/Takeaway format. But a "Q&A" about a complex debugging journey might use Question/Investigation/Root cause/Fix/Why this happens, because the debugging process IS the learning.

A "Decision Record" for a tech stack choice follows the ADR template closely. But a "Decision Record" about a workflow design might add a "How we'll know this was wrong" section because the decision is harder to reverse.

**The bar:** Would someone reading this note in 6 months find the structure helpful for quickly locating the information they need? If a section heading doesn't help them navigate, it shouldn't exist. If a piece of information is buried because the template didn't have a place for it, add a section.

**The repo should feel like a curated library, not a database dump.** Each note should feel like it was written for this specific topic, not stamped from a template factory.

### Step 4: Generate title

- 3-8 words, specific, searchable
- No "How to" or "Guide to" prefixes unless it genuinely is a how-to
- Use the core concept as the title: "Python asyncio event loop internals" not "Learning about async"
- Title becomes the filename slug (e.g. `python-asyncio-event-loop-internals.md`)

### Step 4.5: Pick topic folder

The `topic` param determines which folder the note lands in. The repo is organized as an Obsidian vault with topic-based folders.

**First, check existing topics** by calling `Github MCP Worker:list_notes` to see the current folder structure. Prefer placing notes in existing folders when the content genuinely fits.

**Topic selection rules:**
1. **Existing folder fits clearly** -- use it. E.g. a note about MCP schema caching goes in `mcp/`.
2. **No existing folder fits** -- propose a new one. Keep it short, lowercase, hyphenated. E.g. `nodejs`, `finance`, `devops`.
3. **Content spans multiple domains** -- prefer the **vertical/domain** folder over the technique/tool folder. The repo is organized by "what is this about" not "what tool was used." "Extracting YouTube transcripts via Node.js proxy tricks" goes in `youtube/` (the domain), not `nodejs/` (the technique). The reasoning: you'll search the repo by domain ("what do I know about YouTube?"), not by implementation detail ("what have I done with undici?").
4. **Ambiguous or could go either way** -- present 2-3 options to the user with a brief rationale for each and a recommended pick.

**Always preview** the proposed topic, title, and tags before pushing. Never auto-push without user confirmation.

**Avoid date-based paths.** Always provide a topic. If you truly can't categorize something, use `misc/` rather than falling back to `YYYY/MM/`.

### Step 5: Pick tags

Tags serve as topic categorization. Pick 1-3 tags from the content domain.

Common tag patterns:
- Tech stack: `mcp`, `cloudflare`, `go`, `python`, `typescript`, `react`
- Domain: `finance`, `crypto`, `devops`, `security`, `ai`
- Concept type: `architecture`, `debugging`, `config`, `workflow`
- Company: `dwarves`, `ops`

Tags are passed as an array to `push_note` and written into YAML frontmatter by the tool.

### Step 5.5: Handle visual content

**Default behavior: preserve visuals from the conversation.** If the conversation produced diagrams, charts, SVGs, or visualizer output that are relevant to the note being captured, they should be included in the note. Don't drop visuals just because the capture pipeline is text-focused.

**Four sources of visuals to check:**

1. **Visualizer/Excalidraw output generated during this conversation** -- these were created to explain the concept being captured. They belong in the note. Convert to PNG, upload to R2, embed.
2. **User-uploaded images** (screenshots, diagrams they shared) -- if the image is essential context for the note, upload to R2 and embed. If it's incidental (e.g. a screenshot of an error that's already described in text), skip it.
3. **New diagrams generated at capture time** -- if the note would benefit from a visual that wasn't created during the conversation (e.g. a summary diagram, architecture overview, or comparison table that didn't exist yet), generate it fresh during the capture step.
4. **HTML widget output from Visualizer** -- the Visualizer tool produces HTML widgets (comparison tables, phase mappings, interactive diagrams) that render inline in claude.ai. These are often the most information-dense visuals in a conversation and should be captured.

**When to generate a new diagram vs reuse an existing one:**
- If the conversation produced a diagram that covers the concept well, reuse it. Don't regenerate for the sake of it.
- If the conversation didn't produce a visual but the note would be significantly better with one (e.g. a fallback chain, architecture diagram, or comparison chart), generate one during capture.
- If an existing diagram was interactive (JSX/HTML) and needs to become static for the note, re-express it as SVG or a markdown table.

**Detect visuals:** Check if the conversation turns being captured contained:
- SVG output (from Excalidraw or Visualizer tool calls)
- HTML widget output (from Visualizer show_widget calls -- comparison tables, phase maps, interactive explainers)
- Mermaid diagrams
- React/JSX artifacts with visual output (common on Claude iOS)
- Any content where the explanation depends on seeing the image

**Four pipelines depending on source format:**

#### Pipeline A: SVG (Claude.ai web, Cowork, Claude Code)

```bash
# 1. Save SVG to temp file
cat > /tmp/capture-diagram.svg << 'SVGEOF'
[SVG CONTENT]
SVGEOF

# 2. Convert SVG to PNG
python3 -c "from cairosvg import svg2png; svg2png(url='/tmp/capture-diagram.svg', write_to='/tmp/capture-diagram.png', output_width=1200)"

# 3. Upload PNG to R2
RESPONSE=$(curl -s -X POST $R2_UPLOAD_ENDPOINT \
  -H "Authorization: Bearer REDACTED_TOKEN" \
  -H "Content-Type: image/png" \
  -H "X-Filename: [SLUG]" \
  --data-binary @/tmp/capture-diagram.png)

# 4. Extract URL
IMAGE_URL=$(echo "$RESPONSE" | python3 -c "import sys,json; print(json.load(sys.stdin)['url'])")

# 5. Clean up
rm -f /tmp/capture-diagram.svg /tmp/capture-diagram.png
```

**For Claude.ai chat container:** Install `cairosvg` first: `pip install cairosvg --break-system-packages`

**For Cowork/Claude Code (macOS):** `pip3 install cairosvg` or `brew install librsvg` (for `rsvg-convert`)

#### Pipeline B: JSX artifacts (Claude iOS, Claude.ai web)

GitHub and Obsidian cannot render JSX. Instead of trying to screenshot JSX with Puppeteer, **re-express the visual as SVG before capture**.

Most JSX artifacts from Claude are charts, diagrams, tables, or simple layouts. These can be faithfully recreated as SVG, which renders natively on GitHub and in Obsidian.

**Process:**
1. Look at the JSX artifact that was generated in the conversation
2. Re-express the visual content as SVG (Claude can do this directly)
3. Upload the SVG to R2 using Pipeline A (convert to PNG first) or upload SVG directly
4. Reference the R2 URL in the note markdown

**If the JSX is too complex to re-express as SVG** (heavy interactivity, animations, deeply nested state), fall back to:
1. Include a text description of what the visual shows
2. Embed the JSX source in a collapsed code block for later reference

#### Pipeline C: Mermaid diagrams

```bash
# 1. Save mermaid source
cat > /tmp/capture-diagram.mmd << 'MMDEOF'
[MERMAID SOURCE]
MMDEOF

# 2. Render with mermaid-cli (if available)
npx -y @mermaid-js/mermaid-cli mmdc -i /tmp/capture-diagram.mmd -o /tmp/capture-diagram.png -w 1200

# 3. Upload to R2 (same as Pipeline A step 3)
```

If mermaid-cli is not available, fall back to including the mermaid source in a code block.

#### Pipeline D: HTML widgets (Visualizer output)

The Visualizer tool produces HTML widgets that render inline in claude.ai. These often contain the most valuable visual summaries (comparison matrices, phase maps, scoring tables, workflow diagrams). They need special handling because:
- They use CSS variables (--color-text-primary, etc.) that only resolve inside claude.ai
- They may contain interactive elements (buttons with sendPrompt, sliders) that don't work outside the chat
- They are often more information-dense than prose and worth preserving

**Capture strategy (prioritized):**

1. **Convert to markdown table** (preferred for data-heavy widgets). If the HTML widget is essentially a styled table, comparison matrix, or scored list, convert it to a clean markdown table. This is the most portable format and renders everywhere (GitHub, Obsidian, any markdown viewer).

2. **Convert to SVG** (for diagrams and flowcharts). If the HTML widget contains an inline SVG diagram, extract the SVG and run through Pipeline A.

3. **Preserve as HTML file** (for complex interactive content). If the widget is genuinely interactive and the interactivity is the point (a calculator, a configurator, an interactive explainer), save the HTML source alongside the note:
   - Push the HTML file via `push_note` to a parallel path: `{topic}/{slug}-widget.html`
   - Reference it from the note: `See [interactive version](./{slug}-widget.html)` 
   - Also include a static markdown summary of what the widget shows, so the note is useful without the HTML

4. **Screenshot fallback** (if none of the above work). Take a screenshot of the widget rendering and upload to R2 as PNG. This is the last resort because screenshots are not searchable or editable.

**Decision framework for HTML widgets:**
- Widget is mostly a table/list/matrix? -> markdown table (option 1)
- Widget is an SVG diagram inside HTML wrapper? -> extract SVG (option 2)
- Widget has meaningful interactivity? -> preserve HTML (option 3)
- None of the above? -> screenshot (option 4)

**Embed in markdown body using standard image syntax:**
```markdown
![Brief description of diagram](IMAGE_URL)
```

Since the GitHub repo is an Obsidian vault, standard markdown image links render correctly.

### Step 6: Push to GitHub

Use the `Github MCP Worker:push_note` tool:

```
Tool: Github MCP Worker:push_note
Parameters:
  title: "Python asyncio event loop internals"
  content: "[cleaned markdown body]"
  tags: ["python", "async", "architecture"]
  topic: "python"
  source: "Claude.ai chat"
```

The tool handles:
- Generating YAML frontmatter (title, date, tags, source)
- Creating the file at `{topic}/{slug}.md` (or `YYYY/MM/YYYY-MM-DD-slug.md` if topic is omitted)
- Committing to the `tieubao/til` repo

**Always pass the `topic` param.** See Step 4.5 for how to pick it.

**Source field convention:**
- Claude.ai chat: `"Claude.ai chat"`
- Claude iOS: `"Claude iOS"`
- Claude Code: `"Claude Code session"`
- Cowork: `"Cowork session"`
- If a specific project context is active, append it: `"Claude Code - capacities-mcp"`

### Step 7: Confirm

After pushing, confirm with the user:
```
Captured: "Python asyncio event loop internals"
Topic: python/
Tags: python, async, architecture
Path: python/python-asyncio-event-loop-internals.md
Link: https://github.com/tieubao/til/blob/master/python/python-asyncio-event-loop-internals.md
```

Include the GitHub link if returned by the tool.

## Fallback

If the GitHub MCP tool is unavailable (connector not connected, worker down):

Save each capture as a separate file in the project-local `.learned/` directory (or `~/.learned/` if no project context):

```bash
# Use project-local dir if in a git repo, otherwise home-level
if git rev-parse --show-toplevel &>/dev/null; then
  DIR="$(git rev-parse --show-toplevel)/.learned"
else
  DIR=~/.learned
fi
mkdir -p "$DIR"

# Generate slug from title
SLUG=$(echo "[TITLE]" | tr '[:upper:]' '[:lower:]' | sed 's/[^a-z0-9]/-/g' | sed 's/--*/-/g' | sed 's/^-//;s/-$//')
DATE=$(date +%Y-%m-%d)
FILEPATH="${DIR}/${DATE}-${SLUG}.md"

cat > "$FILEPATH" << 'EOF'
---
title: [TITLE]
date: [ISO date]
tags: [list]
source: [session context]
pushed: false
---

[MARKDOWN BODY]
EOF
```

Tell the user: "GitHub MCP wasn't available. Saved to [filepath]. Push manually or retry later."

## Batch mode

When the user says "extract my learnings", "checkpoint", or "capture knowledge":

1. Scan the current conversation context for learning moments
2. Identify candidates: explanations, root causes, architectural decisions, concept breakdowns, comparison analyses, design decisions, workflow discoveries
3. **MANDATORY: Present the full list with content layout preview before pushing anything.** Format:

```
Found [N] learning moments to capture:

1. "[title]" (type: [Comparison/Q&A/Decision Record/etc.])
   Topic: [folder] | Tags: [tag1, tag2]
   Layout:
     ## Overview (what's being compared, 2 sentences)
     ## Comparison table (4 criteria x 3 options)
     ## Verdict (opinionated recommendation)
   
2. "[title]" (type: [type])
   Topic: [folder] | Tags: [tag1, tag2]
   Layout:
     ## Context (the problem, 1 paragraph)
     ## The insight (core learning, with code example)
     ## When this matters (practical trigger)

3. "[title]" (type: [type])
   Topic: [folder] | Tags: [tag1, tag2]
   Layout:
     [TIL -- single block, ~200 words, no sections needed]

Push all / Pick specific numbers / Adjust layout / Skip?
```

The layout preview shows the section headings and a brief note of what each section will contain. This lets the user judge whether the structure fits the content BEFORE the note is written and pushed. The user can request layout changes ("make #2 a comparison instead of Q&A", "add a 'common mistakes' section to #1") before confirmation.

4. Wait for user confirmation. User can:
   - "Push all" -- push everything as previewed
   - "Push 1, 3, 5" -- push specific items by number
   - "Skip 2" -- push everything except item 2
   - Rename titles, change topics, adjust types, or restructure layouts before pushing
5. Push each confirmed note sequentially via `push_note`
6. After all pushes complete, show a summary with all GitHub links

**This preview step is NOT optional, even for single notes.** The user must see the content layout and confirm before any push_note call. The only exception: if the user says "push this exact thing" and points to a specific message, treat that as pre-confirmed for that single note.

## Claude Code integration

For Claude Code, this skill's logic is split into:
- `/learned` command: cherry-pick the last response and push immediately via GitHub MCP
- `/push-learned` command: batch push all files from `.learned/` directory
- CLAUDE.md auto-capture rules: silently save each learning to `.learned/` during coding (one file per capture, named `YYYY-MM-DD-slug.md`)

These slash commands should be installed at `~/.claude/commands/learned.md` and `~/.claude/commands/push-learned.md`.

## Important rules

1. **Never auto-push without user confirmation.** Always preview what will be captured.
2. **Quality gate -- even on explicit triggers.** If the content is too thin, purely operational, or too context-dependent to stand alone as a reference, tell the user it's not worth capturing and explain why. A noisy repo is worse than a sparse one. This applies to explicit "capture this" requests too -- push back if the note wouldn't help future-you.
3. **Strip all conversational fluff.** Notes should be standalone references.
4. **One note per concept.** Don't bundle unrelated learnings into one note.
5. **Images go to R2, markdown goes to GitHub.** The note content references R2 URLs for any images. Never try to push binary files via `push_note`.
6. **Tags complement the topic folder.** The topic folder is the primary organization. Tags in frontmatter provide cross-cutting categorization in Obsidian (e.g. a note in `youtube/` might also be tagged `nodejs` and `proxy`).