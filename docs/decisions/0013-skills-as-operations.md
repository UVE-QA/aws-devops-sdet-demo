# ADR-0013: Skills model — operations (verbs), not phases

## Status
Accepted (Phase 0)

## Context
The build is phase-gated (Phase 0-8). A naive design would create one skill per
phase, but phases are sequential states, not reusable actions — per-phase skills
overlap heavily and trigger poorly (which one fires during a mixed task?). The
work itself decomposes cleanly into recurring operations.

## Decision
Skills model operations (verbs); phases model state (tracked in
`docs/phase-gates.md` and `CLAUDE.md`, not in skills). Maintain ~9 skills,
grouped: meta (session-protocol, phase-gate, skill-maintenance), infra
(local-dev, tf-workflow, deploy-stage, teardown), product (app-dev, test-dev).
~9 is the comfortable ceiling.

## Decision details
- A skill's `description` is the trigger mechanism: rich trigger phrases (EN+RU)
  plus an explicit "Do NOT use for" boundary naming the neighbor skill.
- Boundaries that were easy to confuse: local-dev RUNS existing tests, test-dev
  WRITES/adapts them; app-dev syncs test-dev on any contract change.
- New skills go through skill-maintenance (overlap check, triggering eval with
  skill-creator, an ADR, registry update).

## Consequences
- Skills stay reusable across phases and trigger predictably.
- Phase state and operation logic are decoupled: changing where we are in the
  plan does not require new skills.
- A `contract-sync` skill is deferred unless the app starts changing a lot
  (revisit in Phase 8).
