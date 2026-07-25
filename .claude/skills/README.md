# Skills Registry

The map of all skills in this repo. Read this when unsure which skill fits,
instead of guessing. Each skill is one operation; descriptions carry the
triggers and the "do not use for" boundaries.

Skills are loaded by Claude Code on demand based on their `description`. The
description is the trigger mechanism — keep it rich and bounded. To add or
change a skill, use the `skill-maintenance` skill.

## Categories

### Meta (how we work)

| Skill | Use it when | Do NOT use it for |
|---|---|---|
| `session-protocol` | starting/ending a session, pulling latest, committing the session summary | the actual phase work; closing a phase gate (→ phase-gate) |
| `phase-gate` | closing a phase, deciding to advance, handling a mid-phase error | routine session entry/exit; the technical work itself |
| `skill-maintenance` | adding/editing a skill, fixing triggering, resolving overlap | running the operational work the skills describe |

### Operational — infrastructure

| Skill | Use it when | Do NOT use it for |
|---|---|---|
| `local-dev` | compose up/down, migrate/seed, running existing smoke/db tests, the SSH tunnel | writing tests (→ test-dev); app changes (→ app-dev); AWS (→ deploy-stage) |
| `tf-workflow` | terraform fmt/validate/plan/apply mechanics, S3 state, auth | full deploy orchestration (→ deploy-stage); destroy (→ teardown) |
| `deploy-stage` | full AWS deploy: bootstrap, first local apply, OIDC, CI deploy, migrate/seed, post-deploy checks | low-level tf commands (→ tf-workflow); local compose (→ local-dev); destroy (→ teardown) |
| `teardown` | destroy/teardown, post-demo cleanup, stopping cost, verifying clean state | building infra (→ deploy-stage); routine plan/apply (→ tf-workflow); compose down (→ local-dev) |

### Operational — product

| Skill | Use it when | Do NOT use it for |
|---|---|---|
| `app-dev` | changing app/ (FastAPI, models, migrations, seed); hands off to test-dev on contract change | writing tests (→ test-dev); running the stack (→ local-dev); AWS (→ deploy-stage) |
| `test-dev` | writing/fixing/adapting Playwright and DB tests to match the app contract | changing app code/migrations/seed (→ app-dev); merely running existing tests (→ local-dev) |

## Key relationships

- `app-dev` → `test-dev`: any change to the contract (endpoints, schema,
  migrations, seed) must hand off to test-dev before the task is done.
- `deploy-stage` and `teardown` build on `tf-workflow` for the raw Terraform.
- `local-dev` runs existing tests; `test-dev` writes them. "Run the test" →
  local-dev; "fix/adapt the test" → test-dev.
- `phase-gate` and `session-protocol` checkpoint everything into git.

## Adding the next skill

When the project grows (e.g. Phase 8 adds prod), follow `skill-maintenance`:
list triggers, check overlap, write a bounded description, verify triggering
with the skill-creator evals, record an ADR, update this table, commit.
The comfortable ceiling is ~9 skills; beyond that, watch for overlap.
