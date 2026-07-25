# Skills Structure — Reference

This describes the Claude Code skills layout for `aws-devops-sdet-demo`.
All files live in the repo so they sync across machines via git; Claude Code
loads `CLAUDE.md` every session and each skill on demand by its description.

## Layout

```
repo-root/
  CLAUDE.md                         always-read anchor / router
  .claude/skills/
    README.md                       skill registry (the map)
    session-protocol/SKILL.md       meta: session entry/exit, commit summary
    phase-gate/SKILL.md             meta: close a phase, advance only on confirm
    skill-maintenance/SKILL.md      meta: add/change skills, verify triggering
    local-dev/SKILL.md              infra: compose, migrate/seed, run tests
    tf-workflow/SKILL.md            infra: terraform command mechanics + state
    deploy-stage/SKILL.md           infra: full AWS deploy orchestration
    teardown/SKILL.md               infra: destroy + verify, repeatable cycle
    app-dev/SKILL.md                product: change app/, hand off to test-dev
    test-dev/SKILL.md               product: write/adapt tests to the contract
  docs/
    decisions/0000-template.md      ADR template ("why" decisions)
    sessions/INDEX.md               one row per session
```

## Design principles applied

- **Skills are operations (verbs), phases are state.** The phase cursor lives
  in `docs/phase-gates.md` + `CLAUDE.md`; skills say *how*, not *when in the
  plan*. This avoids overlapping per-phase skills that trigger poorly.
- **Description is the trigger.** Each description carries concrete trigger
  phrases (English + Russian) and an explicit "Do NOT use for" boundary naming
  the neighbor skill. This is what makes the right skill fire.
- **Anchor + on-demand.** `CLAUDE.md` is always read and routes to skills, so
  the process is reliable even if a skill under-triggers; skill bodies load
  only when needed, keeping token cost low.
- **No duplication.** ADRs hold "why", skills hold "how". Skills reference ADRs
  rather than restating them.
- **app-dev → test-dev handoff.** Any contract change (endpoints, schema,
  migrations, seed) must sync tests before a task is done.
- **Context in layers.** ADRs (always), phase cursor (where we are), session
  summaries (on demand). Transcripts and large logs are never committed.

## Scope note

This is the initial set (9 skills). It is deliberately not exhaustive — Phase 8
(e.g. prod deploy, regression suites) will likely add skills via the
`skill-maintenance` procedure, which checks trigger overlap before adding.

## How this plugs into the main prompt

The main phase-gated prompt should reference this structure: add `CLAUDE.md`,
`.claude/skills/`, `docs/decisions/`, `docs/sessions/` to the repo layout, and
add Acceptance items (CLAUDE.md present, skills present with bounded
descriptions, session summary committed at each gate). Skills are created as
part of Phase 1 (devbox preparation), before app work begins.
