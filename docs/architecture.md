# Architecture

## Overview

`claude-skills` is a plugin repo containing shared Claude Code skills for the Dwarves team. It's the companion to [dwarvesf/claude-context](https://github.com/dwarvesf/claude-context) (config/identity).

## How skills work

A skill is a folder with a `SKILL.md` file. Claude Code reads skills from `~/.claude/skills/<name>/SKILL.md` and makes them available as `/skill-name` commands.

### SKILL.md format

```yaml
---
name: skill-name
description: When and how this skill should trigger. This text appears
  in the skill list and helps Claude decide when to suggest the skill.
---

# Skill Name

Instructions for Claude in markdown...
```

The `description` field is critical: it tells Claude when to activate the skill. Be specific about trigger conditions and skip conditions.

## Plugin structure

This repo is packaged as a Claude Code plugin so it can be installed remotely via the marketplace.

```
claude-skills/
  .claude-plugin/
    plugin.json          # Plugin manifest (name, version, description)
  skills/
    prompt-improver/
      SKILL.md
    capture/
      SKILL.md
  docs/
  README.md
```

## Two install methods

### Method 1: Plugin marketplace (remote, no cloning)

```bash
/plugin marketplace add dwarvesf/claude-skills
/plugin install claude-skills@dwarvesf-claude-skills
```

Skills are downloaded and managed by Claude Code's plugin system.

### Method 2: SKILLS_DIR symlink (local dev/testing)

```bash
git clone git@github.com:dwarvesf/claude-skills.git ~/claude-skills
```

In `claude-context/.env`:
```bash
SKILLS_DIR=~/claude-skills/skills
```

Run `sync-claude-context.sh` to symlink skill folders into `~/.claude/skills/`.

**When to use which:**
- Plugin marketplace for most users (simple, one command)
- SKILLS_DIR for skill developers who want to edit and test locally

## Relationship to claude-context

```
claude-context (config/identity)     claude-skills (behaviors)
+---------------------------+        +------------------------+
| shared/voice-and-style.md |        | skills/prompt-improver |
| shared/claude-code-extras |        | skills/capture         |
| private/about-me.md       |        | ...                    |
+---------------------------+        +------------------------+
         |                                     |
         v                                     v
   ~/.claude/CLAUDE.md               ~/.claude/skills/
   (concatenated)                    (symlinked or plugin-managed)
```

Config tells Claude *who you are* and *how to write*. Skills tell Claude *what to do* in specific situations.

## Capturing from Claude.ai web

Claude.ai web has no export API for memory, project instructions, or skills. The `/capture` skill provides a manual-but-streamlined workflow:

1. Copy useful content from Claude.ai web
2. Invoke `/capture` in Claude Code
3. Classify as skill, config, or memory
4. The skill formats and saves it to the right place

For Claude.ai Chat/Web, skills can be:
- Pasted as project instructions in claude.ai
- Uploaded via Claude Desktop Settings (shared across Chat/Cowork/Code)
- Added as memory edits
