---
name: skill-import
description: Imports skills from the dwarvesf/claude-skills GitHub repo into Claude.ai. Use when the user says "import skill", "fetch skill from repo", "update skill from GitHub", "pull latest skill", "/skill-import", or wants to bring a skill from the GitHub repo into their Claude.ai /mnt/skills/user/ directory. This is the reverse of skill-sync (which pushes Claude.ai → GitHub).
updated: 2026-03-28T10:00:00Z
---

# Skill Import

Import skills from the `dwarvesf/claude-skills` GitHub repo into Claude.ai's `/mnt/skills/user/` directory. This is the reverse of `skill-sync` (which pushes from Claude.ai to GitHub).

## Prerequisites

- Running on Claude.ai (needs write access to `/mnt/skills/user/`)
- GitHub repo must be accessible (public repo or authenticated access)
- For MCP method: Github MCP Worker must be connected

## Trigger

User says: "import skill", "fetch skill", "pull skill from repo", "update skill from GitHub", "get latest skills", "/skill-import"

**Skip conditions:**
- If the user wants to push *to* GitHub, use `skill-sync` instead
- If the user wants a zip download, use `skill-export` instead
- If running in Claude Code (not Claude.ai), this skill doesn't apply. Just `git pull`.

## Workflow

### Step 1: Identify skills to import

If the user specifies a skill name, use that. Otherwise, fetch the repo's skill index:

**Option A (preferred, if `read_skill` MCP tool exists):**
```
list_notes() or read the repo README
```

**Option B (fallback, via GitHub raw URL):**
```
WebFetch: https://raw.githubusercontent.com/dwarvesf/claude-skills/master/README.md
```

Parse the skills table from README.md to show available skills:

```
## Available skills in repo

| Skill | Description |
|-------|-------------|
| prompt-improver | Sharpens prompts before executing |
| content-spec | Enforce spec phase before content work |
| knowledge-capture | Capture learning moments to Capacities |
| skill-sync | Push skills from Claude.ai to GitHub |
| skill-export | Export skills to repo-ready format |
| skill-import | Import skills from GitHub to Claude.ai |

Import which? [name / several / all]
```

### Step 2: Fetch skill content from GitHub

For each skill to import, fetch the SKILL.md content:

**Option A (preferred, if `read_skill` MCP tool exists):**
```
read_note(topic: "skills/<skill-name>", title: "SKILL")
```

**Option B (fallback, via GitHub raw URL):**
```
WebFetch: https://raw.githubusercontent.com/dwarvesf/claude-skills/master/skills/<skill-name>/SKILL.md
```

Also check for supporting files by fetching the directory listing or known paths:
- `skills/<skill-name>/references/`
- `skills/<skill-name>/scripts/`
- `skills/<skill-name>/templates/`

### Step 3: Diff check (conflict detection)

Before overwriting, check if a local version already exists.

**Read local version:**
```bash
cat /mnt/skills/user/<skill-name>/SKILL.md
```

**Compare:**

1. **No local version exists** → New skill. Proceed to install.
2. **Local matches repo** → Already in sync. Skip unless user forces.
3. **Versions differ** → Show a diff summary:

```
## Conflict: knowledge-capture

Local version:  updated 2026-03-25T09:15:00Z
Repo version:   updated 2026-03-28T14:30:00Z (newer)

Changes from repo:
- Added visual pipeline section
- Updated push destination format
- Fixed Capacities type mapping

Action: [import repo version] [keep local] [show full diff]
```

**Conflict resolution rules:**
- If repo `updated` is newer than local `updated`: recommend importing (repo is newer)
- If local `updated` is newer than repo `updated`: warn that local has newer changes, recommend pushing to repo first via `skill-sync`
- If neither has `updated` field: show full diff, ask user to decide
- If content differs but timestamps are the same: show diff, ask user (concurrent edits)

**User can always force import** by saying "import anyway" or "overwrite local".

### Step 4: Install to Claude.ai

For each approved skill:

```bash
# Create skill directory if it doesn't exist
mkdir -p /mnt/skills/user/<skill-name>

# Write the SKILL.md
cat > /mnt/skills/user/<skill-name>/SKILL.md << 'SKILLEOF'
<full SKILL.md content from repo>
SKILLEOF
```

For supporting files (references, scripts, templates):
```bash
mkdir -p /mnt/skills/user/<skill-name>/references
# Write each supporting file
```

### Step 5: Report results

After all imports complete:

```
## Import Results

Imported:
- knowledge-capture (updated: 2026-03-28T14:30:00Z)
- content-spec (updated: 2026-03-28T10:00:00Z)

Skipped:
- prompt-improver (already in sync)
- skill-sync (local is newer, push to repo first)

Not in repo:
- my-custom-skill (local only)

Skills are now available. Start a new conversation to pick up changes.
```

### Step 6: Remind about conversation reload

Skills in `/mnt/skills/user/` are loaded at conversation start. After importing:

```
NOTE: Imported skills will be available in your next conversation.
Start a new chat to use the updated skills.
```

## Batch import

When the user says "import all" or "fetch all skills":

1. Fetch the skill list from the repo README
2. For each skill, fetch content from GitHub
3. Diff check each against local versions
4. Show combined report:

```
## Import Report

| Skill | Local Status | Repo Version | Action |
|-------|-------------|--------------|--------|
| knowledge-capture | Outdated (local 03-25) | 03-28 (newer) | Import |
| content-spec | Missing | 03-28 | Import (new) |
| prompt-improver | In sync | 03-28 | Skip |
| skill-sync | Local newer (03-29) | 03-28 | Skip (push first) |

Ready to import: knowledge-capture, content-spec
```

5. Import all approved skills after user confirms
6. Report results

## Important rules

1. **Always diff check before overwriting.** Never silently replace a local version that might have unpushed changes.
2. **Warn when local is newer.** If the local version is newer than repo, the user should `skill-sync` first to avoid losing work.
3. **Show the import report before writing.** User must confirm what will be installed.
4. **This skill only runs on Claude.ai.** In Claude Code, skills live in the git repo directly; just `git pull`.
5. **Respect the `updated` field.** Use it as the source of truth for version comparison.
6. **One skill at a time for writes.** Don't batch file writes; if one fails, the rest should still succeed.
7. **Always remind about conversation reload.** Skills are loaded at conversation start, not mid-conversation.
