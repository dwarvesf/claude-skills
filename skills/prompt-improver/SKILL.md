---
name: prompt-improver
description: Sharpens and improves prompts before executing. Triggers on any non-trivial prompt where better phrasing would produce deeper, more specific answers. Use when the user submits a vague, broad, or under-specified prompt. Skip for straightforward operational tasks (file edits, git commands, direct instructions).
---

# Prompt Improver

Before executing a prompt, improve it first. The goal is to help the user learn better prompting by showing what a stronger version looks like.

## When to activate

- The prompt is open-ended, vague, or could benefit from more structure
- The prompt asks a broad question without specifying constraints or context
- The prompt would produce a significantly better answer if reworded

## When to skip

- The user said "just do it", "skip", or "defaults fine"
- The task is a direct operational command (file edit, git, run tests, etc.)
- The outcome is fixed regardless of phrasing (e.g., "delete line 5", "rename X to Y")
- The prompt is already specific and well-structured

## Workflow

### Step 1: Analyze the prompt
Identify what's missing or could be sharper:
- Is the scope clear?
- Are constraints specified?
- Is the desired output format defined?
- Are there implicit assumptions that should be explicit?

### Step 2: Show the improved version
Present the improved prompt in a quoted block. Keep changes minimal and purposeful. Do not over-engineer simple questions.

Format:
> **Improved prompt:** [the improved version]

Add a brief note (1-2 sentences) on what changed and why.

### Step 3: Execute the improved prompt
Proceed with the improved version unless the user pushes back.

## Examples

**Before:** "explain this code"
**After:** "Explain what this function does, its inputs/outputs, and any non-obvious design decisions. Focus on the parts that aren't self-documenting."
**Why:** Specifies what aspects to cover and where to focus depth.

**Before:** "how should I structure this?"
**After:** "What are 2-3 reasonable ways to structure this feature? For each, note the tradeoff and when you'd pick it. Recommend one for our current codebase."
**Why:** Asks for comparison with tradeoffs instead of a single answer.
