---
name: skill-export
description: Exports Claude.ai skills to repo-ready format for GitHub. Use when the user says "export skill", "push skill to repo", "package skill for GitHub", "extract skill", "sync skill to repo", or wants to move a skill from Claude.ai to their claude-skills or claude-context repository. Also trigger when the user finishes drafting a new skill and wants it formatted for their repo structure. Handles both extracting existing skills from /mnt/skills/user/ and formatting newly-drafted skills for commit.
---

# Skill Export

You help export Claude.ai skills into a repo-ready format for the user's GitHub skill repository.

## Two modes

### Mode 1: Export existing skill
The user wants to extract a skill that already lives in `/mnt/skills/user/` and package it for their GitHub repo.

### Mode 2: Repo-first output
The user just finished drafting or iterating on a skill in this conversation and wants it formatted as a repo-ready file they can commit.

## Workflow

### Step 1: Identify the skill

**Mode 1 (export existing):**
- Read the skill from `/mnt/skills/user/<skill-name>/SKILL.md`
- Also check for supporting directories: `references/`, `scripts/`, `templates/`
- If the user doesn't specify which skill, list available skills:
  ```
  ls /mnt/skills/user/
  ```
- Let the user pick one or say "all"

**Mode 2 (repo-first):**
- The skill content is already in the current conversation
- Gather it from the most recent draft

### Step 2: Security classification

Scan the skill content for sensitive data. Check for:

1. **Notion database IDs**: UUIDs matching `[0-9a-f]{8}-?[0-9a-f]{4}-?[0-9a-f]{4}-?[0-9a-f]{4}-?[0-9a-f]{12}`
2. **Collection URIs**: `collection://` prefixed strings
3. **API keys or tokens**: patterns like `sk-`, `xoxb-`, bearer tokens
4. **Company-specific identifiers**: Airwallex account refs, bank account numbers, internal URLs
5. **Hardcoded names**: Specific employee names, client names, contractor names

Classify as:
- **SAFE**: No sensitive data found. Ready for the team repo as-is.
- **SENSITIVE**: Contains hardcoded IDs or company data. Needs refactoring before sharing.
- **BORDERLINE**: Contains company name references but no IDs or secrets. Flag for user review.

Report the classification to the user with specifics:
```
Classification: SENSITIVE
Found:
- 15 Notion database IDs
- 9 collection:// URIs
- References to "Airwallex", "d.foundation"

Recommendation: Refactor to read IDs from context file before adding to team repo.
```

### Step 3: Refactor if needed

If the skill is SENSITIVE and the user wants it in the team repo:

1. Replace every hardcoded Notion database ID with a context file reference:
   ```
   BEFORE:
   - Page ID: `9d468753ebb44977a8dc156428398a6b`

   AFTER:
   - Read the Contractors Page ID from the user's context file (notion-reference.md)
   ```

2. Replace company-specific payment channels, rate structures, or org details with generic descriptions

3. Keep all workflow logic, step sequences, output formats, and business rules intact. Only strip the data layer.

4. Add a "Prerequisites" section at the top of the refactored skill:
   ```
   ## Prerequisites
   This skill requires a `notion-reference.md` file in your working folder (Cowork)
   or referenced in your CLAUDE.md (Claude Code) with your Notion database IDs.
   ```

### Step 4: Package and output

**IMPORTANT: Always output a zip file with the correct repo folder structure inside.**

The zip must unpack directly into the repo root. Structure:

```
skills/<skill-name>/
  SKILL.md
  references/    (if applicable)
  scripts/       (if applicable)
```

To build the zip:

```bash
# Create the folder structure in a staging area
mkdir -p /home/claude/export-staging/skills/<skill-name>

# Write SKILL.md
# Copy references/ and scripts/ if they exist in the source

# Zip from the staging root so paths are relative to repo root
cd /home/claude/export-staging
zip -r /mnt/user-data/outputs/<skill-name>.zip skills/<skill-name>/
```

Then present the zip file to the user. This way the user can unzip directly into their repo:

```bash
cd ~/claude-skills
unzip <skill-name>.zip
git add skills/<skill-name>
git commit -m "add <skill-name> skill"
git push
```

**For batch export**, create one zip containing all skills:
```
skills/skill-a/SKILL.md
skills/skill-b/SKILL.md
skills/skill-c/SKILL.md
...
```

### Step 5: Provide commit instructions

After presenting the zip:
```
To add to your repo:
  cd ~/claude-skills
  unzip <skill-name>.zip
  git add skills/<skill-name>
  git commit -m "add <skill-name> skill"
  git push
```

## Batch export

If the user says "export all" or "export all safe skills":

1. Read all skills from `/mnt/skills/user/`
2. Classify each one
3. Package all SAFE skills into a single zip
4. List SENSITIVE skills with their findings
5. Ask if user wants to refactor any of them

## Important rules

1. **Never output sensitive data to files going to the team repo.** If classification is SENSITIVE and the user hasn't confirmed refactoring, refuse to output.
2. **Preserve the full skill logic.** Refactoring strips data, not functionality.
3. **Always show the classification before outputting.** The user must see what was found.
4. **If in doubt, classify as SENSITIVE.** False positives are safe. False negatives leak data.
5. **Always output as a zip with repo-correct paths.** Never output a loose SKILL.md file. The user should be able to unzip into their repo root and everything lands in the right place.
