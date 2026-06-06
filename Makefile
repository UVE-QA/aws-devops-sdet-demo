# Ubuntu-compatible developer commands for the v0 local stack.
# All container commands run on the Lightsail devbox via docker compose.

.PHONY: local-up local-down migrate seed test-smoke test-db docker-build tf-fmt tf-validate

# Bring up postgres + app (build app image if needed), detached.
local-up:
	docker compose up -d --build

# Stop and remove containers (keeps the pgdata volume).
local-down:
	docker compose down

# Run Alembic migrations to head, using the same app image (one-off container).
# WORKDIR is /app, so alembic finds alembic.ini and `src` is importable.
migrate:
	docker compose run --rm app alembic upgrade head

# Insert the idempotent seed row.
seed:
	docker compose run --rm app python scripts/seed.py

# Run Playwright smoke against the running app (BASE_URL default localhost:8000).
# Installs node deps + chromium on first run.
test-smoke:
	cd tests/playwright && npm install && npx playwright install --with-deps chromium && npx playwright test

# Run the standalone DB assertion against postgres, on the compose network.
# Reuses the app image (has sqlalchemy + psycopg2-binary) and mounts the test.
test-db:
	docker compose run --rm -v "$(PWD)/tests/db:/tests-db" app python /tests-db/assert_seed.py

# Build the app image only.
docker-build:
	docker compose build app

# Terraform formatting check across the whole tree.
tf-fmt:
	terraform fmt -recursive infra

# Terraform validate for stage without a backend (no AWS creds needed).
tf-validate:
	cd infra/envs/stage && terraform init -backend=false && terraform validate
