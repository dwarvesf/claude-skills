# Roadmap

## Done

- [x] Plugin manifest (`.claude-plugin/plugin.json`)
- [x] prompt-improver skill (extracted from claude-context)
- [x] Pushed to dwarvesf/claude-skills
- [x] Architecture docs

## Next

- [ ] **capture skill**: Format and save content from Claude.ai web sessions into the right repo (skill -> claude-skills, config -> claude-context, memory -> auto-memory)
- [ ] **Test plugin marketplace install**: Verify `/plugin marketplace add dwarvesf/claude-skills` works end-to-end
- [ ] **vibe-learn**: Migrate from local `~/.claude/skills/vibe-learn/` into this repo
- [ ] **CLIMB framework**: Extract from claude-context's `claude-code-extras.md` as a standalone skill for math/quant finance study sessions

## Capture skill design

```
Step 1: User pastes content from web session
Step 2: Classify (skill / config / memory)
Step 3: Ask for a name and one-line description
Step 4: Format into the right structure:
        - Skill -> skills/<name>/SKILL.md in this repo
        - Config -> append to claude-context/shared/*.md
        - Memory -> save to ~/.claude/projects/.../memory/
Step 5: If skill or config, suggest git commit
```

## Adding a new skill

1. Create `skills/<skill-name>/SKILL.md`
2. Add YAML frontmatter with `name` and `description`
3. Write the skill instructions in markdown
4. Update README.md skills table
5. Commit and push
6. Users get it on next `/plugin install` or `git pull` + sync
