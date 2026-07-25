# Session 2026-06-06 — project scaffold (pre-devbox)

- Phase: 0
- Request: prepare a local project structure holding all artifacts and decision
  context, to be moved to the Lightsail devbox once it exists.
- Changed: created CLAUDE.md, .claude/skills/ (9 skills + registry),
  docs/ (project-prompt, phase-gates, discussion-log, skills-structure,
  decisions/0001 + template, sessions/INDEX + this file), README.md,
  .gitignore, .env.example.
- Commands run: none (scaffold only; no app/infra code yet).
- Result: Phase 0 scaffold ready. Skills, docs, and the corrected build prompt
  are in place. GitHub will become the source of truth after `git init` on the
  devbox.
- Blockers: none.
- Next step: complete and confirm Phase 0 discovery inventory
  (docs/project-prompt.md §3), then Phase 1 (Lightsail devbox).

## Update (same day) — tooling decisions

- Decided: Claude Code only, no Cowork (CC sufficient; avoids splitting SoT).
- Added project-prompt §4.4: CC runs on the devbox; VS Code Remote-SSH
  (preferred) vs bare SSH (fallback); instance-size trade-off for VS Code
  Server; VS Code settings model (repo .vscode/ + remote ~/.vscode-server vs
  per-laptop VS Code/Remote-SSH/SSH key).
- Recorded the same in discussion-log.md (Tooling decisions) and cleaned
  Codex/Cursor references in the prompt.
