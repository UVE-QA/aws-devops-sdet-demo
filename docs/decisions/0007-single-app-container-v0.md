# ADR-0007: Single application container in v0

## Status
Accepted (Phase 0)

## Context
The project's value is the delivery construction (IaC, CI/CD, account
isolation, testing, lifecycle), not the application domain. Splitting frontend
and backend into separate services would add a second image, task definition,
target group, and deployment path — complexity that does not demonstrate
anything new for v0 and increases cost and teardown surface.

## Decision
v0 uses a single containerized app: FastAPI serves static HTML at `/` and the
JSON API (`/health`, `/api/health`, `/api/db-check`) from the same image. No
separate frontend/backend services, no React/Vite. The same image also runs
one-off migrate/seed/db-assert commands via run-task overrides.

## Consequences
- One image, one task definition, one service — simpler IaC and CI/CD.
- The single container constrains the health-check design: liveness checks must
  not touch the DB or ECS cannot reach steady state before migrations run (see
  ADR-0008).
- Richer domain logic, a real frontend, and service splitting are deferred to
  Phase 8.
