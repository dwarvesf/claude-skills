# claude-skills

Shared Claude Code skills for the Dwarves team. Packaged as a plugin for remote install, also works with local symlinks.

## Install

### Option 1: Plugin marketplace (recommended)

```bash
/plugin marketplace add dwarvesf/claude-skills
/plugin install claude-skills@dwarvesf-claude-skills
```

### Option 2: Local clone with claude-context sync

```bash
git clone git@github.com:dwarvesf/claude-skills.git ~/claude-skills
```

Then in your `claude-context/.env`:
```bash
SKILLS_DIR=~/claude-skills/skills
```

Run `./sync-claude-context.sh` to symlink skills into `~/.claude/skills/`.

## Skills

| Skill | Trigger | Description |
|-------|---------|-------------|
| `prompt-improver` | `/prompt-improver` | Sharpens vague prompts before executing. Shows improved version so you learn better prompting. |
| `skill-export` | `/skill-export` | Exports Claude.ai skills to repo-ready format with security classification and zip packaging. |
| `knowledge-capture` | `/knowledge-capture` | Captures learning moments from Claude sessions and pushes them to Capacities. |
| `content-spec` | `/content-spec` | Enforces a requirement/specification phase before substantial content work (500+ words, docs, translations). |
| `skill-sync` | `/skill-sync` | Syncs skills from Claude.ai to GitHub repo via MCP Worker. Security classifies before pushing. |
| `skill-import` | `/skill-import` | Imports skills from GitHub repo into Claude.ai. Reverse of skill-sync with diff check and conflict detection. |

## Adding a new skill

1. Create `skills/<skill-name>/SKILL.md`
2. Add YAML frontmatter with `name` and `description`
3. Write the skill instructions in markdown
4. Update the table above
5. Commit and push

Skill format:
```yaml
---
name: skill-name
description: When and how this skill should trigger.
---

# Skill Name

Instructions for Claude...
```

## Architecture

This repo is the skills companion to [dwarvesf/claude-context](https://github.com/dwarvesf/claude-context) (config/identity). See that repo for the full sync architecture.
