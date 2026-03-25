---
name: content-spec
description: "Enforce a requirement/specification phase before any substantial content work begins. Use this skill whenever the user asks Claude to write, expand, revise, translate, or build content that will be 500+ words, or any task involving document generation (docx, pdf, pptx), multi-section drafting, content expansion/revision passes, or translation work. Also trigger when the user says 'write a chapter', 'expand this section', 'revise the draft', 'translate this', 'build the doc', or any similar content production request. Claude MUST draft a Content Spec and get approval BEFORE executing. This skill also manages a Requirements Ledger that accumulates decisions across iterations. Trigger this skill even if the task seems straightforward, because the spec catches failure modes that only become visible after wasted work."
---

# Content Spec Tool

A requirement/specification phase for content development. Ensures Claude and the user are working from the same spec before any substantial work begins.

## Why this exists

Content work fails in predictable ways: voice drift after 2,000 words, "expansion" that actually shrinks content, structure that diverges from the plan, optimistic self-reporting instead of actual verification. These failures waste 30-60 minutes each and compound across iterations.

The fix is simple: lock the requirements before starting, check against them when done. This skill enforces that discipline.

## When to use (and when NOT to)

The trigger is **iteration risk**, not word count. A task has iteration risk when a failed output wastes significant time and the fix requires understanding what went wrong, not just redoing it.

**USE the spec for:**
- Multi-session content projects (books, documentation series, course materials)
- Expansion or revision passes on existing drafts
- New chapters, sections, or long-form articles within an established project
- Translation work with voice/style requirements
- Document builds (docx, pdf, pptx from source content)
- Any task where voice, structure, or accumulated requirements must be maintained
- Any task the user explicitly asks to spec out

**SKIP the spec for:**
- Single questions, even if the answer is long
- Explanations, tutorials, or concept breakdowns
- Brainstorming and ideation (this is UPSTREAM of the spec)
- Quick emails, messages, or short writing tasks
- One-off code scripts or bug fixes
- Research and analysis responses
- Single-paragraph edits or format tweaks
- Casual conversation about project direction
- Any task where "just redo it" costs less than 10 minutes

**The test:** If the user's request could be handled well as a single-turn response with no prior context needed, skip the spec. If the request depends on accumulated decisions, voice standards, structural plans, or prior iteration history, use the spec.

When in doubt, ask: "This seems like it might benefit from a quick spec. Want me to draft one, or should I just go ahead?"

## The Content Spec

Claude drafts this. The user approves, modifies, or rejects before work begins. It fits in one message.

### Template

```
TASK: [One sentence. What are we doing?]

INPUTS: [What existing material does this depend on? File names, context sources, pasted content.]

VOICE: [Which voice/tone applies? Reference a style guide if one exists, or describe in 1-2 sentences.]

CONSTRAINTS: [3-7 non-negotiable rules for THIS specific task. Not generic advice. Reference ledger entries by ID where applicable.]

DELIVERABLE: [Exact output format, length target, structure expectations.]

FAILURE MODES: [2-4 specific things that have gone wrong before on similar tasks. Use IDs from the Failure Mode Library if available, or describe task-specific risks.]

ACCEPTANCE CHECK: [2-4 measurable or verifiable criteria. How do we know it is done? Include applicable quality gates and audience tests from the ledger.]
```

### Ambiguity check

After drafting the spec, Claude self-evaluates each field:

```
AMBIGUITY CHECK:
- TASK: specific and verifiable? [yes/no]
- VOICE: concrete enough to test against? [yes/no]
- CONSTRAINTS: each one actionable, not vague? [yes/no]
- DELIVERABLE: format, length, structure all specified? [yes/no]
- ACCEPTANCE CHECK: each criterion measurable or evaluable? [yes/no]
```

If any field scores "no," Claude flags it: "I flagged [field] as ambiguous because [reason]. Want to tighten it, or is this good enough for the task?"

The goal is not perfection. Some tasks genuinely have ambiguous elements that resolve during execution. The check ensures the ambiguity is visible and deliberate, not accidental.

### Field guidance

**TASK** should be specific enough that someone could verify completion. "Write Chapter 5" is too vague. "Draft Chapter 5 covering X, Y, Z at ~3,500 words" is verifiable.

**INPUTS** prevents the "I assumed you meant..." problem. If Claude is working from pasted content, a file, a previous conversation, or a style guide, list it. Missing inputs surface before execution, not during.

**VOICE** catches tone drift before it starts. Even "professional but conversational, no jargon" is better than nothing. If the project has a style guide, reference it by name.

**CONSTRAINTS** should be task-specific, not a dump of every rule ever. 3-7 items. If a constraint applies to every task in the project, it belongs in the Requirements Ledger (see below), not repeated in every spec.

**DELIVERABLE** eliminates ambiguity about what "done" looks like. Format (markdown, docx, plain text), length (word count range, not "approximately"), and structure (how many sections, what headings).

**FAILURE MODES** is the most important field. This is where institutional memory lives. After a few iterations on any project, you will know what goes wrong. Name those things here so Claude watches for them during execution, not after.

**ACCEPTANCE CHECK** is what Claude runs before presenting the output. If any check fails, Claude flags it honestly rather than hoping the user won't notice.

## The Requirements Ledger

Requirements evolve during execution. The spec captures what you know at the start. The Ledger captures what you learn along the way.

### What it is

A running log of decisions, standards, and constraints that emerged during work and should persist across future sessions. One ledger per project or workstream.

### Entry types

The ledger supports five entry types. Each serves a different purpose. Use the TYPE field to distinguish them.

#### TYPE: decision

A concrete choice that was made. The most common entry type.

```
[RL-XX] [Date] TYPE: decision
DECISION: Use Cognitive Exploit Map framework for Layer 2 analysis of all major cases
RATIONALE: Three frameworks evaluated. Cognitive Exploit Map names specific cognitive biases, giving readers actionable vocabulary to interrupt manipulation. Most analytically rigorous option.
SCOPE: All 30 major case entries, Layer 2
STATUS: active
```

#### TYPE: quality-gate

A depth or quality standard the content must clear. These are judgment calls, not binary checks. The EVALUATE field tells Claude how to self-assess.

```
[RL-XX] [Date] TYPE: quality-gate
STANDARD: A financial crimes investigator would read this case entry and call it analysis, not summary
EVALUATE: Does the entry reveal structural connections the source material doesn't make explicit? Does it explain WHY the scheme works psychologically, not just WHAT happens? Could you hand this to a fraud examiner and they'd learn something they didn't know?
SCOPE: All 30 major case entries
STATUS: active
```

#### TYPE: audience-test

Defines a specific reader persona and what they must get from the content.

```
[RL-XX] [Date] TYPE: audience-test
AUDIENCE: Kurosagi manga reader who has spent 200+ hours with the series
MUST DELIVER: Structural insight the manga never provides. Cross-case patterns invisible in narrative but obvious in analysis.
MUST NOT: Summarize plots the reader already knows. Condescend.
SCOPE: Expert commentary layer in all major case entries
STATUS: active
```

#### TYPE: adaptive-constraint

A rule with conditions. Which option applies is selected per-task.

```
[RL-XX] [Date] TYPE: adaptive-constraint
RULE: Select analytical framework based on case characteristics
CONDITIONS:
  - IF character-driven → Criminal Profile framework
  - IF structurally complex → Kill Chain taxonomy
  - IF psychology-driven → Cognitive Exploit Map
  - IF multiple → primary + secondary noted
SCOPE: All 30 major case entries, framework selection
STATUS: active
```

When referenced in a spec, Claude states which branch and why.

#### TYPE: open-question

A brainstorming question not yet resolved. Superseded when answered.

```
[RL-XX] [Date] TYPE: open-question
QUESTION: Should kill chain phases be explicit or embedded in narrative?
CONTEXT: Explicit is more rigorous. Embedded reads better but insight may be missed.
SCOPE: Part I cross-case analysis
STATUS: open | superseded by RL-XX
```

### How the ledger grows

1. **Claude proposes** entries when a significant reusable decision emerges, a quality standard is articulated, a constraint is learned from failure, or a brainstorming question is worth preserving.

2. **User approves, modifies, or rejects** before it is logged.

3. **Claude writes it to the ledger file** using file tools (create_file, str_replace). Not to memory. Not just acknowledged in conversation. Actually written to the file so it persists.

### The brainstorm-to-requirement pipeline

1. Claude logs the question as TYPE: open-question (with user approval)
2. Work continues. The question gets explored through iteration.
3. When the answer becomes clear, Claude proposes a typed entry and marks the open-question as superseded.

### Ledger persistence: how and where to store

**CRITICAL: The ledger is a FILE, not a memory edit.** Requirements are structured, scoped, and growing. Memory edits are short single-line notes with character limits. Never use memory_user_edits to store ledger entries. Always write to a file.

**The persistence mechanic:**

1. **First time:** When the first ledger entry is approved and no ledger file exists yet, ask the user where to create it.
2. **Every time after:** Write approved entries to the established ledger file using file tools. Claude must actually write to the file, not just acknowledge the entry.
3. **Reading back:** At the start of any new content task, read the ledger file to load active requirements before drafting the Content Spec.

**What goes in memory edits instead:** Only a pointer to the ledger file and the instruction to use this skill. The actual requirements stay in the file.

## The three mechanics

Everything in this skill serves three mechanics. If it doesn't serve one of these, it's overhead.

### Mechanic 1: Build up requirements

Requirements accumulate from the initial brief, the Content Spec, brainstorming sessions, and execution discoveries. All end up in the Requirements Ledger. The Content Spec is a per-task snapshot. The ledger is the persistent store.

### Mechanic 2: Update requirements mid-session

When work reveals something new: Claude proposes a ledger entry, user approves, it's logged immediately and incorporated into current work. This happens during execution, not after.

### Mechanic 3: Use persisted requirements as QA checklist

Before presenting output, Claude checks against TWO sources: the per-task Content Spec (ACCEPTANCE CHECK field) and all active ledger entries whose SCOPE covers this task.

## Workflow

```
1. User describes what needs to be done (brief)
2. Claude evaluates: does this need a spec? (see "When to use")
   - If no → just do the work, no spec overhead
   - If yes → continue to step 3
3. Claude loads the ledger, drafts a Content Spec, runs ambiguity check
4. User reviews: approves, modifies, or rejects
5. Claude executes against the approved spec
6. Mid-execution drift check at ~50% for long outputs
7. If a new requirement emerges → Mechanic 2 (propose, approve, log)
8. Before presenting output → Mechanic 3 (QA against spec + ledger)
9. If any check fails, Claude flags which ones and why before presenting
```

## Mid-execution drift check

For long outputs (2,000+ words or multi-section tasks), Claude pauses at roughly the halfway point:

1. Re-read the VOICE and CONSTRAINTS from the spec
2. Compare the last few paragraphs against the voice standard
3. Check: has the tone shifted? Has academic drift started? Has structure diverged?
4. If drift detected: flag it with a specific example ("The last two paragraphs shifted into textbook tone. Should I correct and continue?")
5. If no drift: continue without interrupting

This is lightweight. Not a formal report. A quick internal re-read that catches problems at the halfway mark instead of after 4,000 words of drifted content.

## Self-check protocol (Mechanic 3 in practice)

Before presenting final output:

1. Re-read the approved Content Spec
2. Identify all active ledger entries whose SCOPE covers this task
3. Check each ACCEPTANCE CHECK criterion. Actually verify, don't estimate.
4. Check each applicable ledger entry by type (decisions: followed? quality gates: met? audience tests: delivered? adaptive: right branch?)
5. For word counts: run an actual count
6. For structural checks: compare output headings to spec
7. For voice checks: re-read the first and last paragraph of each section
8. Report results honestly. State which checks passed and which failed.
9. Never say "expanded to ~X words" without having counted

## Failure Mode Library

Read `references/failure_modes.md` for the full library with detection methods.

Quick reference:

| ID | Name | One-line |
|----|------|----------|
| V1 | Academic drift | Tone shifts from conversational to textbook |
| V2 | Formatting violation | Banned formatting reappears |
| V3 | Tone collapse | Voice degrades over long output |
| V4 | Spotlight inversion | Wrong subject becomes protagonist |
| C1 | Expansion shrinkage | "Expansion" rewrites at same or shorter length |
| C2 | Source inversion | Supporting source takes lead, primary demoted |
| C3 | Cross-reference leak | Unauthorized references to external content |
| C4 | Outline drift | Structure diverges from plan without discussion |
| C5 | Depth without substance | Word count grows through filler, not new content |
| B1 | Format spec violation | Build ignores documented specs |
| B2 | Asset mismatch | Referenced assets missing or misconfigured |
| P1 | Optimistic summary | Reports success without verification |
| P2 | Plan skip | Jumps to execution without presenting plan |
| P3 | Silent scope change | Changes scope without flagging deviation |

## Examples

See `references/examples.md` for worked examples showing the full spec-to-delivery cycle.
