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

- `tests/` — Playwright smoke and (later) regression specs
- DB-assertion tests (e.g. checking `seed-item-001` exists)

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
   make test-smoke
   make test-db
   ```
4. Keep smoke fast and deterministic; put broader coverage in regression
   (regression is a later phase, not v0).

## Quality guidance

- Assertions should be objective and clearly named so a failure says what
  broke. Avoid flaky waits — wait on conditions, not fixed sleeps.
- A test that only passes because it no longer checks anything is worse than a
  red test. Keep assertions meaningful when you adapt them.

## Done means green

The task is done when the adapted suite passes against the changed app and the
assertions still verify the intended behavior, not when they were loosened to
pass. If the app contract itself looks wrong, kick back to `app-dev`.
