# ADR-0010: PostgreSQL 16 pinned across local and RDS

## Status
Accepted (Phase 0)

## Context
Local development runs PostgreSQL in Docker Compose; the AWS target uses RDS
PostgreSQL. If the major versions differ, behavior can diverge (SQL features,
defaults, extension availability), so a passing local test does not guarantee
the same result on RDS — undermining the point of local validation.

## Decision
Pin PostgreSQL major version 16 everywhere: the docker-compose image is
`postgres:16` and the RDS engine version is PostgreSQL 16. They must stay in
sync whenever the version is bumped.

## Consequences
- Local Docker Compose and RDS behave consistently; local tests are meaningful
  predictors of AWS behavior.
- A version bump is a deliberate change applied in both places at once
  (compose image + RDS engine_version), ideally recorded as a new ADR.
