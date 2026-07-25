---
name: app-dev
description: >
  Use when changing the demo application code under app/: "add an endpoint",
  "new field on the model", "change the schema", "add a migration", "update
  the seed data", "modify the API response", "добавь эндпоинт", "новое поле в
  модель", "поправь схему", "добавь миграцию", "измени API". Covers FastAPI
  routes, SQLAlchemy models, Alembic migrations, and the seed script, plus the
  rule that any change to the app/test contract (endpoints, DB schema,
  migrations, seed) must hand off to test-dev before the task is considered done.
  Do NOT use for: writing or fixing tests (see test-dev), just running the
  stack (see local-dev), or anything about AWS deployment (see deploy-stage).
---

# App Dev (changing the demo application)

The app is intentionally one container: FastAPI serving static HTML + API,
talking to PostgreSQL. Keep v0 simple — no React/Vite, no multi-service split.
The reason this skill exists separately from tests is that app changes are the
*cause* of test breakage, so app work must explicitly trigger test work.

## What lives here

- `app/` — FastAPI routes, SQLAlchemy models, app wiring
- Alembic migrations (new revisions)
- the seed script

## Health-endpoint invariant (do not break)

`/health` and `/api/health` must NOT touch the database — they are liveness
checks and must return OK before migrations run or RDS is reachable.
`/api/db-check` is the only endpoint that opens a DB connection. Breaking this
deadlocks ECS (service never goes healthy, so migrate task never runs).

## Typical change flow

1. Make the change in `app/`.
2. If the DB schema changed, create an Alembic revision and verify
   `alembic upgrade head` locally (via `local-dev`).
3. Update the seed script if new data shape is needed.
4. Verify locally: `curl localhost:8000/api/db-check` reports connected.

## Contract check — MANDATORY before finishing

After any app change, ask: did I touch the contract the tests depend on?
The contract is:

- endpoints and their response shapes (`/api/*`, `/health`, `/api/db-check`)
- DB schema (tables/columns, especially `demo_items`)
- Alembic migrations (a new revision)
- seed data (e.g. `seed-item-001`, which DB assertions rely on)
- BASE_URL / access contract

If ANY of these changed, the task is not done until tests are synced — hand
off to `test-dev`. A silent schema/endpoint change with stale tests is exactly
the failure this split is designed to prevent. Do not close the task with the
suite red or untouched when the contract moved.
