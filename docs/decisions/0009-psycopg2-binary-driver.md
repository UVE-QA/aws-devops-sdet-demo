# ADR-0009: Use psycopg2-binary, not psycopg2

## Status
Accepted (Phase 3)

## Context
The app connects to PostgreSQL via SQLAlchemy, which needs a driver. The plain
`psycopg2` package compiles from source and requires `libpq-dev` and `gcc` at
build time. On a slim Python base image (`python:3.12-slim`) those are absent,
so `psycopg2` fails the Docker build unless extra system packages are added,
bloating the image and slowing the build.

## Decision
Use `psycopg2-binary` in `app/requirements.txt`. It ships prebuilt wheels with
the PostgreSQL client bundled, so no compiler or `libpq-dev` is needed in the
image. The DATABASE_URL scheme stays `postgresql+psycopg2://...`.

## Consequences
- The Docker build succeeds on the slim base with no extra system packages.
- Smaller, faster image build.
- `psycopg2-binary` is suitable for this demo; the binary build's known caveats
  (not recommended for some high-scale production setups) are irrelevant at v0
  scale and can be revisited if the workload grows.
