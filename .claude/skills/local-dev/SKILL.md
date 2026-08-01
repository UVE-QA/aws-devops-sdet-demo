---
name: local-dev
description: >
  Use when running the app locally on the Lightsail devbox via Docker Compose:
  "spin up the stack", "docker compose up", "run it locally", "start postgres",
  "run migrate and seed", "run the smoke test", "check db-check", "open the app
  through the tunnel", "подними локально", "запусти стек", "прогони smoke".
  Covers bringing the compose stack up/down, running migrate + seed, executing
  the EXISTING Playwright smoke and DB-assertion suites, hitting /health and
  /api/db-check, and the SSH tunnel to reach the app from a laptop.
  Do NOT use for: writing or changing tests (see test-dev), changing app code
  or migrations (see app-dev), or anything deployed on AWS (see deploy-stage).
---

# Local Dev (Docker Compose on the devbox)

Local development means the compose stack running on the Lightsail devbox.
The app is one container (FastAPI serving static HTML + API) plus postgres.
There is one working copy, on the devbox; laptops connect via Remote SSH.

## Preconditions

- On the devbox, in the repo root, branch as expected.
- Docker + Docker Compose available.
- `.env` present locally (copied from `.env.example`, never committed).

## Bring the stack up and verify

```bash
docker compose up -d
docker compose ps
curl -s localhost:8000/health        # OK without DB (liveness)
curl -s localhost:8000/api/health    # OK without DB
```

## Migrate, seed, then verify DB path

Order matters: the app must be up first (liveness has no DB dependency),
then migrate, then seed, then the DB endpoint goes green.

```bash
make migrate            # alembic upgrade head -> creates demo_items
make seed               # inserts seed-item-001
curl -s localhost:8000/api/db-check   # now reports connected
```

## Run the existing suites

```bash
make test-unit          # in-process: the shape of the JSON log line. Needs
                        # no stack, so it can run before make local-up
make test-spec-coverage # every spec belongs to a Playwright project
make test-api           # HTTP contract tests (pytest+httpx), DESTRUCTIVE
make test-smoke         # Playwright read-only suite against BASE_URL
make test-regression    # Playwright destructive suite + the UI-write DB assertion
make test-db            # DB assertion: seed-item-001 exists
```

## Reach the app from a laptop

```bash
ssh -L 8000:localhost:8000 ubuntu@<LIGHTSAIL_STATIC_IP>
# then open http://localhost:8000 on the laptop
```

Do not expose port 8000 or 5432 publicly. Use the tunnel.

## Tear the stack down

```bash
docker compose down            # add -v only if you want to drop the DB volume
```

If a test fails because the app behavior changed, that is a contract change —
hand off to `app-dev` / `test-dev`; do not paper over it here.
