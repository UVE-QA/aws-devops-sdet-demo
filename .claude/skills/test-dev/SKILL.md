---
name: test-dev
description: >
  Use when writing, fixing, or adapting the test suites under tests/: "fix the
  tests", "the smoke test is failing", "adapt the suite", "update the
  assertions", "tests broke after the schema change", "add a regression test",
  "write a playwright test", "почини тесты", "адаптируй сьют", "обнови
  ассерты", "тест упал после изменения". Covers Playwright smoke/regression and
  the DB-assertion tests, and keeping them in sync with the app contract
  (endpoints, schema, seed) after app-dev changes something.
  Do NOT use for: changing app code, models, migrations or seed (see app-dev),
  or just executing existing tests during local runs (see local-dev). This
  skill is about authoring/changing tests, not merely running them.
---

# Test Dev (authoring and adapting tests)

Tests break because the application changed. This skill keeps `tests/` in sync
with the app contract. It pairs with `app-dev`: app-dev changes the contract
and hands off here; this skill makes the suite match the new reality.

## What lives here

```text
tests/api/                          HTTP contract tests (pytest + httpx).
                                    DESTRUCTIVE. stage and local only.
tests/playwright/tests/smoke/       READ-ONLY. project "smoke".
                                    The only suite prod runs.
tests/playwright/tests/regression/  DESTRUCTIVE. project "regression".
                                    stage and local only.
tests/db/assert_seed.py             seed assertion, local gate
app/scripts/assert_seed.py          the same, shipped in the image for ECS
app/scripts/assert_ui_write.py      asserts the row the UI wrote reached RDS
```

**Where a spec lives decides where it runs (ADR-0025).** The Playwright projects
select by directory, so a new spec goes under `smoke/` only if it is genuinely
read-only — no create, no update, no delete, not even a cleanup. Anything else
goes under `regression/`.

A spec in neither directory belongs to no project, runs in no suite and is
reported by nothing. `make test-spec-coverage` fails on exactly that, and it is
not optional: run it after adding or moving any spec file.

## The contract to track

When adapting tests, align them to the current app contract:

- endpoints and response shapes (`/api/*`, `/health`, `/api/db-check`)
- DB schema (tables/columns, especially `demo_items`)
- seed data the assertions depend on (e.g. `seed-item-001`)
- BASE_URL (localhost:8000 locally, ALB URL on AWS)

## Typical flow

1. Identify what in the contract changed (read the app-dev diff / the failing
   assertion). Don't guess — `git diff app/` shows the cause.
2. Update or add the spec/assertion to match the new shape.
3. Run against the local stack (via `local-dev`):
   ```bash
   make test-spec-coverage   # after adding or moving any spec
   make test-api
   make test-smoke
   make test-regression      # includes the UI-write DB assertion
   make test-db
   ```
4. Keep smoke fast, read-only and deterministic. Broader and destructive
   coverage goes to regression.
5. If a test needs a name that another process will look up — the UI-write
   assertion is the existing example — pass it explicitly and give it NO
   default. A default lets the assertion pass while checking something nobody
   created.

## Quality guidance

- Assertions should be objective and clearly named so a failure says what
  broke. Avoid flaky waits — wait on conditions, not fixed sleeps.
- A test that only passes because it no longer checks anything is worse than a
  red test. Keep assertions meaningful when you adapt them.

## Done means green

The task is done when the adapted suite passes against the changed app and the
assertions still verify the intended behavior, not when they were loosened to
pass. If the app contract itself looks wrong, kick back to `app-dev`.
