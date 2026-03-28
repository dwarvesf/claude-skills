# Handoff: Skill Sync Pipeline

## What we're building

Automated sync of skills from Claude.ai to the `dwarvesf/claude-skills` repo via the GitHub MCP Worker.

## Current state

### Done
- `push_skill` tool added to the GitHub MCP Worker and deployed
- Handoff spec was drafted (not committed, lost when session ended)

### Needs verification (do this first)
- **Verify `push_skill` MCP tool is accessible.** Search for it in deferred tools. If it shows up, test it with a dummy skill push.
- If it doesn't show up, check: tool naming in the Worker, MCP connection refresh, deployment logs.

## Architecture

```
Claude.ai                          GitHub                         Local
─────────                          ──────                         ─────
User: /skill-sync
  │
  ├─ Read /mnt/skills/user/
  ├─ Security classify each skill
  ├─ For each SAFE skill:
  │    push_skill(name, content) ──► Commit to
  │         via MCP Worker            dwarvesf/claude-skills ──► git pull
  │                                   skills/<name>/SKILL.md
  └─ Report results
```

## Next steps (in order)

### Step 1: Verify `push_skill` works
- Search for the tool in MCP tools list
- Test: push a dummy skill, verify it lands at `skills/test-dummy/SKILL.md` in the repo
- Clean up the test file after

### Step 2: Build `skill-sync` skill for Claude.ai
Create `skills/skill-sync/SKILL.md` that runs on Claude.ai:

**Trigger**: user says "sync skills", "push skills to repo", "/skill-sync"

**Workflow**:
1. List skills in `/mnt/skills/user/`
2. For each skill, run security classification (reuse logic from `skill-export`):
   - Check for Notion IDs, API keys, company data, hardcoded names
   - Classify as SAFE / SENSITIVE / BORDERLINE
3. Show classification report to user
4. For each SAFE skill (or user-approved after refactoring):
   - Call `push_skill(name=<skill-name>, content=<SKILL.md content>)`
5. Report: what was pushed, what was skipped, commit URLs

**Security classification rules** (from `skill-export`):
- Notion database IDs (UUID pattern)
- `collection://` URIs
- API keys (`sk-`, `xoxb-`, bearer tokens)
- Company-specific identifiers (Airwallex refs, bank numbers, internal URLs)
- Hardcoded employee/client/contractor names

### Step 3: Test end-to-end
1. On Claude.ai, run `/skill-sync` on a real skill
2. Verify commit in GitHub
3. `git pull` locally and confirm file structure

### Phase 2 (later)
- `list_skills` MCP tool to read current repo skills (for diff/sync)
- `delete_skill` MCP tool for cleanup
- Conflict detection (local changes vs Claude.ai version)
- Batch sync with dry-run mode

## Tool schema reference (expected)

```json
{
  "name": "push_skill",
  "parameters": {
    "name": { "type": "string", "description": "Skill name, kebab-case" },
    "content": { "type": "string", "description": "Full SKILL.md content" },
    "message": { "type": "string", "description": "Optional commit message" }
  },
  "required": ["name", "content"]
}
```

## Files in this repo

| File | Purpose |
|------|---------|
| `skills/skill-export/SKILL.md` | Existing skill for manual export (zip download). Security classification logic lives here. |
| `skills/skill-sync/SKILL.md` | To be created (Step 2). Automated push via MCP. |
| `docs/handoff-skill-sync.md` | This file. |
