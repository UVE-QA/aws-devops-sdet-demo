# ADR-0012: Claude Code on the devbox (no Cowork)

## Status
Accepted (Phase 0)

## Context
The AI assistant tooling could run as Claude Code (CC, terminal/IDE-native) or
Cowork (the no-terminal desktop wrapper). They share one engine. This project
is terminal/IaC work, and the skills live in `.claude/skills/` (CC's native
format). Running both would split the source of truth for skills.

## Decision
Use Claude Code only, running ON the devbox (where the repo, Docker, Terraform,
and AWS CLI live). Access it two ways: VS Code Remote-SSH + CC extension
(preferred — inline diffs for IaC, integrated terminal) or bare SSH + `claude`
(fallback for weak links, small instances, phone, or pure agentic passes).

## Decision details
- Skills live in `.claude/skills/`; `CLAUDE.md` is the always-read anchor.
- VS Code Remote-SSH is currently deferred; work proceeds via Lightsail browser
  SSH for now.
- On a small Lightsail size (~2 GB), prefer bare SSH for heavy local runs
  (compose + Playwright) since VS Code Server competes for RAM/CPU.

## Consequences
- One engine, one skills source of truth, no Cowork split.
- The access method can change per situation without changing the project
  setup, because CC and its skills run identically in both modes.
