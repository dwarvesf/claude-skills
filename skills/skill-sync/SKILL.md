---
name: skill-sync
description: Syncs skills from Claude.ai to the dwarvesf/claude-skills GitHub repo via MCP. Use when the user says "sync skills", "push skills to repo", "/skill-sync", or wants to automatically push skills from /mnt/skills/user/ to GitHub without manual zip/unzip. Requires the Github MCP Worker to be connected.
updated: 2026-03-28T06:37:00Z
---

# Skill Sync

Automatically push skills from Claude.ai to the `dwarvesf/claude-skills` GitHub repo using the `push_skill` MCP tool. No zip files, no manual git commands. Includes conflict detection via version headers and diff checks.

## Prerequisites

- Github MCP Worker must be connected (provides `push_skill` tool)
- Skills live in `/mnt/skills/user/<skill-name>/SKILL.md` on Claude.ai
- For diff check: GitHub API access (via `WebFetch` to raw.githubusercontent.com)

## Version header

Every skill pushed through this pipeline must have an `updated` field in its YAML frontmatter:

```yaml
---
name: skill-name
description: What this skill does.
updated: 2026-03-28T14:30:00Z
---
```

- Set `updated` to the current UTC datetime (ISO 8601: `YYYY-MM-DDTHH:MM:SSZ`) on every push.
- If the skill doesn't have an `updated` field yet, add it.
- This field is used for conflict detection (see Step 2).

## Trigger

User says: "sync skills", "push skills to repo", "push skill X", "/skill-sync"

**Skip conditions**: If the user wants a zip download instead, use `skill-export`.

## Workflow

### Step 1: Identify skills to sync

If the user specifies a skill name, use that. Otherwise:

```bash
ls /mnt/skills/user/
```

Let the user pick one, several, or "all".

### Step 2: Diff check (conflict detection)

Before pushing, fetch the current version from GitHub and compare.

**How to fetch the repo version:**

Option A (preferred, if `read_skill` MCP tool exists):
```
read_skill(name: "skill-name")
```

Option B (fallback, via GitHub raw URL):
```
WebFetch: https://raw.githubusercontent.com/dwarvesf/claude-skills/master/skills/<skill-name>/SKILL.md
```

**Compare the local and repo versions:**

1. **No repo version exists** (404) -> New skill. Proceed to classification.
2. **Repo version matches local** -> Already in sync. Skip unless user forces.
3. **Versions differ** -> Show a diff summary:

```
## Conflict: content-spec

Repo version:  updated 2026-03-25T09:15:00Z
Local version: updated 2026-03-28T14:30:00Z (newer)

Changes:
- Added Step 4 (review checklist)
- Modified trigger conditions
- Removed legacy format section

Action: [push local] [keep repo] [show full diff]
```

**Conflict resolution rules:**
- If local `updated` is newer than repo `updated`: recommend pushing local (local is newer)
- If repo `updated` is newer than local `updated`: warn that repo has newer changes, recommend reviewing before overwriting
- If neither has `updated` field: show full diff, ask user to decide
- If content differs but timestamps are the same: show diff, ask user (concurrent edits from different sources)

**User can always force push** by saying "push anyway" or "overwrite".

### Step 3: Security classification

For each skill, read its content and scan for sensitive data.

**Check for:**
1. **Notion database IDs**: UUIDs matching `[0-9a-f]{8}-?[0-9a-f]{4}-?[0-9a-f]{4}-?[0-9a-f]{4}-?[0-9a-f]{12}`
2. **Collection URIs**: `collection://` prefixed strings
3. **API keys or tokens**: patterns like `sk-`, `xoxb-`, bearer tokens, `key-`
4. **Company-specific identifiers**: Airwallex account refs, bank account numbers, internal URLs (e.g. `*.d.foundation`, `*.dwarvesf.com`)
5. **Hardcoded names**: Specific employee names, client names, contractor names
6. **Space IDs or account IDs**: Capacities spaceId, Slack workspace IDs

**Classify each skill:**
- **SAFE**: No sensitive data. Push directly.
- **SENSITIVE**: Contains hardcoded IDs or company data. Needs refactoring.
- **BORDERLINE**: Contains company name references but no IDs or secrets. Flag for review.

**Show the combined classification + diff report before pushing:**
```
## Sync Report

| Skill | Security | Repo Status | Action |
|-------|----------|-------------|--------|
| prompt-improver | SAFE | New (not in repo) | Push |
| content-spec | SAFE | Changed (local newer) | Push |
| notion-ops | SENSITIVE -> REFACTORED | Changed (repo newer) | Push (review below) |

Ready to push: prompt-improver, content-spec, notion-ops (refactored)
```

For any SENSITIVE skill that was auto-refactored, show a summary of changes below the table:
```
### notion-ops (auto-refactored)
Replaced:
- 15 Notion database IDs -> context file references
- 9 collection:// URIs -> context file references
- 2 hardcoded names -> role placeholders
Added: Prerequisites section (requires notion-reference.md)

[View full refactored version] or [skip this skill]
```

Wait for user confirmation before pushing.

### Step 4: Auto-refactor sensitive skills

For any skill classified as SENSITIVE, automatically refactor before showing the report:

1. Replace hardcoded Notion database IDs with context file references:
   ```
   BEFORE: Page ID: `9d468753ebb44977a8dc156428398a6b`
   AFTER: Read the Contractors Page ID from the user's context file
   ```
2. Replace `collection://` URIs with references to the user's context config
3. Replace API keys/tokens with environment variable references (`$ENV_VAR` or "configured in user's context file")
4. Replace company-specific payment channels, rate structures, org details with generic descriptions
5. Replace hardcoded employee/client/contractor names with role placeholders
6. Keep all workflow logic, step sequences, output formats, business rules intact
7. Add a Prerequisites section noting required context files

The refactored version is shown inline in the sync report (Step 3) so the user can review before confirming the push. No extra "refactor it" step needed.

**If auto-refactor misses something or breaks logic**, the user can say "edit the refactored version" before confirming.

### Step 5: Push via MCP

For each approved skill:

1. Ensure the `updated` field in frontmatter is set to today's date
2. Read the full SKILL.md content
3. Check for supporting files (references/, scripts/, templates/) in the skill folder
4. Call `push_skill`:
   - `name`: skill name in kebab-case
   - `content`: full SKILL.md content (with updated date)
   - `files`: array of extra files if the skill has supporting assets
   - `message`: "add <name> skill" for new, "update <name> skill" for existing

Example:
```
push_skill(
  name: "content-spec",
  content: "<full SKILL.md content with updated: 2026-03-28T14:30:00Z>",
  files: [
    { path: "templates/spec-template.md", content: "<template content>" }
  ],
  message: "update content-spec skill"
)
```

### Step 6: Report results

After all pushes complete, show:

```
## Sync Results

Pushed:
- content-spec -> skills/content-spec/SKILL.md (commit: abc1234)
- prompt-improver -> skills/prompt-improver/SKILL.md (commit: def5678)

Skipped:
- notion-ops (SENSITIVE, not refactored)

In sync (no changes):
- skill-export

Next: `git pull` in your local clone to get the changes.
```

## Batch sync

When the user says "sync all" or "push all skills":

1. List all skills in `/mnt/skills/user/`
2. Diff check each one against the repo
3. Classify each one for security
4. Show the full combined report (security + diff status)
5. Push all SAFE + newer-or-new skills (after user confirms)
6. Report results, list skipped and in-sync skills

## Important rules

1. **Never push sensitive data.** If classification is SENSITIVE and user hasn't approved a refactored version, refuse to push.
2. **Always show classification and diff before pushing.** User must see what was found.
3. **If in doubt, classify as SENSITIVE.** False positives are safe. False negatives leak data.
4. **Preserve full skill logic during refactoring.** Strip data, not functionality.
5. **One commit per skill.** Each push_skill call creates its own commit for clean history.
6. **Confirm before pushing.** Never auto-push without user seeing the report.
7. **Always set the `updated` date.** Every push must update the frontmatter date.
8. **Warn on repo-newer conflicts.** If the repo version is newer, the user must explicitly confirm overwrite.
