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

# Root levels are DISCOVERED, not listed: any directory with .tf files outside
# infra/modules/. A new state level is therefore validated the moment it exists,
# which is the specific failure this replaces — infra/envs/prod was invalid for
# seven weeks while this target only entered infra/envs/stage.
#
# Modules are covered transitively: a broken module fails every level using it.
# They are excluded deliberately, because running `terraform init` inside a
# module directory litters it with a .terraform.lock.hcl that does not belong
# to a non-root configuration.
TF_ROOTS := $(shell find infra -name '*.tf' -not -path 'infra/modules/*' -printf '%h\n' | sort -u)

# TF_DATA_DIR is isolated per directory. Without it, `init -backend=false` reuses
# the cached S3 backend configuration left in .terraform/ by a real init and the
# check quietly starts requiring AWS credentials.
#
# The isolation is right; the FIRST version of it leaked. `mktemp -d` per level,
# never removed, left a full provider download (~700MB) per root level in /tmp on
# every run - about 4.5GB each time. On 2026-07-26 that filled a 58GB disk to
# 99% and stopped an unrelated `terraform init` with "no space left on device".
# One temporary root, removed by a trap, plus a shared plugin cache so the
# provider is fetched once per machine instead of once per level per run.
tf-validate:
	@[ -n "$(TF_ROOTS)" ] || { echo "tf-validate: no root levels discovered - the find expression above is broken. Refusing to pass without validating anything."; exit 1; }
	@fail=0; \
	tmp=$$(mktemp -d); trap 'rm -rf "$$tmp"' EXIT INT TERM; \
	export TF_PLUGIN_CACHE_DIR="$${TF_PLUGIN_CACHE_DIR:-$$HOME/.terraform.d/plugin-cache}"; \
	mkdir -p "$$TF_PLUGIN_CACHE_DIR"; \
	for d in $(TF_ROOTS); do \
	  printf '%-26s ' "$$d"; \
	  if out=$$(cd "$$d" && TF_DATA_DIR="$$tmp/$$(echo $$d | tr / _)" bash -c 'terraform init -backend=false && terraform validate' 2>&1); then \
	    echo OK; \
	  else \
	    echo FAIL; echo "$$out" | sed 's/^/    /'; fail=1; \
	  fi; \
	done; \
	[ "$$fail" -eq 0 ] || { echo; echo "tf-validate: at least one root level is invalid"; exit 1; }
