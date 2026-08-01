---
name: phase-gate
description: >
  Use when finishing a phase or deciding whether to move to the next one:
  "are we done with this phase", "close the phase", "can we continue",
  "next phase", "phase complete", "закрываем фазу", "переходим дальше",
  "можно продолжать". Enforces the mandatory gate: summarize what was done,
  list files changed, give validation commands and expected results, list
  blockers, then STOP and wait for explicit confirmation before advancing.
  Also use when the user reports an error mid-phase — fix the current phase
  only, never advance.
  Do NOT use for: routine session entry/exit (see session-protocol), or for
  the technical work of a phase (see the operational skills).
---

# Phase Gate

The project is phase-gated (Phase 0 → 8) for a reason: each phase must be
verifiably correct before the next one builds on it. Advancing on a shaky
phase compounds errors. So a gate is a hard stop, not a formality.

## Phase order (do not reorder without explicit instruction)

0 discovery · 1 lightsail devbox · 2 app skeleton · 3 compose + local tests ·
4 terraform foundation · 5 github actions + OIDC · 6 first stage deploy ·
7 destroy validation · 8 feature expansion

## Closing a phase — produce all of this, then stop

1. **Summary** — what this phase accomplished, in a few lines.
2. **Files** — created/modified, by path.
3. **Validation commands** — exact commands the user can run.
4. **Expected results** — what each command should show.
5. **Blockers / risks** — anything unresolved or cost-bearing.
6. **STOP** — explicitly ask for confirmation before continuing.

## Confirmation to advance

Only these (or clear equivalents) advance the gate:
`continue`, `confirmed`, `done`, `phase complete`, `go next`.
Anything ambiguous → treat as not confirmed, ask again.

## If the user reports an error

- Identify the phase and the failing command.
- Explain the likely cause and give exact fix + validation commands.
- Fix the current phase only. Do NOT advance. Do NOT redesign the
  architecture unless the error truly requires it.

## On a successful gate

Update `docs/phase-gates.md` (current phase, validated step) and have
`session-protocol` commit the summary. The gate is the natural place to
checkpoint into git.

Then run `make session-close` (ADR-0033). **Green is the end of the session.**
Do not keep auditing for something that might also have been missed - that is
what the command is for, and a search with no stop condition is how Phase 16b
took four closings and an Ops session took two.
