# ADR-0008: Health-check separation (liveness must not touch the DB)

## Status
Accepted (Phase 0)

## Context
With a single container (ADR-0007), the ALB target group and the container
healthcheck both gate whether the service reaches steady state. If a liveness
endpoint opened a DB connection, the service could never become healthy before
RDS is reachable and migrations have run — but the migration task cannot run
until the service is healthy. That is a deadlock.

## Decision
`/health` and `/api/health` are liveness checks and MUST NOT open a DB
connection; they return OK as soon as the web process is up. `/api/db-check` is
the ONLY endpoint that opens a DB connection. The ALB target group health check
and the container healthcheck both use `/health`.

## Consequences
- The service reaches steady state independently of RDS, so the migrate/seed
  run-task steps can execute against a healthy service.
- DB connectivity is verified explicitly and separately via `/api/db-check`
  (used by the Playwright smoke test and manual checks).
- This separation is a hard invariant: no future endpoint may add DB access to
  `/health` or `/api/health`.
