# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repo is

A Claude Code plugin containing shared skills for the Dwarves team (`dwarvesf/claude-skills`). Companion to [dwarvesf/claude-context](https://github.com/dwarvesf/claude-context) which handles config/identity. This repo handles behaviors (skills).

## Architecture

- **Plugin manifest**: `.claude-plugin/plugin.json` (name, version, description)
- **Skills**: each skill lives in `skills/<skill-name>/SKILL.md` with YAML frontmatter (`name`, `description`) and markdown instructions
- Claude Code reads skills from `~/.claude/skills/<name>/SKILL.md` and exposes them as `/<skill-name>` commands

Two install methods:
1. Plugin marketplace: `/plugin marketplace add dwarvesf/claude-skills`
2. Local dev: clone repo, set `SKILLS_DIR=~/claude-skills/skills` in `claude-context/.env`, run `sync-claude-context.sh` to symlink

## Adding a new skill

1. Create `skills/<skill-name>/SKILL.md`
2. Frontmatter must include `name` and `description` fields; `description` is critical as it tells Claude when to activate
3. Write instructions in markdown body
4. Update the skills table in `README.md`

## SKILL.md format

```yaml
---
name: skill-name
description: When and how this skill should trigger. Be specific about trigger and skip conditions.
---

# Skill Name

Instructions for Claude...
```

## Current skills

| Skill | Path |
|-------|------|
| `prompt-improver` | `skills/prompt-improver/SKILL.md` |
| `skill-export` | `skills/skill-export/SKILL.md` |
| `knowledge-capture` | `skills/knowledge-capture/SKILL.md` |
| `content-spec` | `skills/content-spec/SKILL.md` |
| `skill-sync` | `skills/skill-sync/SKILL.md` |
| `skill-import` | `skills/skill-import/SKILL.md` |

## No build/test/lint

This is a pure markdown/config repo. No build system, no tests, no linting. Changes are validated by reading SKILL.md files and verifying frontmatter structure.
