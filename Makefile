# Ubuntu-compatible developer commands for the v0 local stack.
# All container commands run on the Lightsail devbox via docker compose.

.PHONY: local-up local-down migrate seed test-smoke test-regression test-api \
        test-db test-ui-db test-spec-coverage docker-build tf-fmt tf-validate \
        docs-check

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

# Where the HTTP-level suites point. Overridden with the ALB URL (stage) or the
# public HTTPS name (prod) when they run against AWS.
BASE_URL ?= http://localhost:8000

# The name the UI regression writes and the database assertion then looks up.
# Expanded ONCE, at parse time, so both halves of `test-regression` see the same
# value — the whole point of the probe is that two processes agree on it.
UI_PROBE_NAME ?= ui-probe-$(shell date +%s)

# Read-only Playwright suite. The ONLY suite prod runs (ADR-0025).
# Installs node deps + chromium on first run.
test-smoke:
	cd tests/playwright && npm install && npx playwright install --with-deps chromium \
	  && BASE_URL=$(BASE_URL) npx playwright test --project=smoke

# Destructive Playwright suite, plus the database assertion that proves the
# browser's write reached PostgreSQL. Never run against prod.
test-regression:
	cd tests/playwright && npm install && npx playwright install --with-deps chromium \
	  && BASE_URL=$(BASE_URL) UI_PROBE_NAME=$(UI_PROBE_NAME) npx playwright test --project=regression
	$(MAKE) test-ui-db UI_PROBE_NAME=$(UI_PROBE_NAME)

# Assert that the row the UI created exists in the database. Reuses the app
# image, which already contains the script and the driver.
test-ui-db:
	docker compose run --rm -e UI_PROBE_NAME=$(UI_PROBE_NAME) app python scripts/assert_ui_write.py

# Every spec file must belong to a project, or it runs in no suite at all.
test-spec-coverage:
	cd tests/playwright && npm install && ./scripts/assert-spec-coverage.sh

# HTTP contract tests (pytest + httpx) against a RUNNING app. Destructive:
# they create and delete items, so stage and local only, never prod.
#
# A virtualenv rather than a bare `pip install`: Ubuntu 24.04 marks the system
# interpreter externally-managed (PEP 668) and refuses to install into it, and
# pytest has no business in the application image.
API_VENV := .venv-api
test-api:
	@python3 -m venv $(API_VENV) 2>/dev/null || { \
	  echo "could not create a virtualenv - install python3-venv (apt install python3-venv)"; exit 1; }
	@$(API_VENV)/bin/pip install -q --upgrade pip
	$(API_VENV)/bin/pip install -q -r tests/api/requirements.txt
	BASE_URL=$(BASE_URL) $(API_VENV)/bin/pytest tests/api -q

# Run the standalone seed DB assertion against postgres, on the compose network.
# Reuses the app image (has sqlalchemy + psycopg2-binary) and mounts the test.
test-db:
	docker compose run --rm -v "$(PWD)/tests/db:/tests-db" app python /tests-db/assert_seed.py

# Every make target, repo path, route and workflow named in the LIVING documents
# must exist. Historical documents are not checked: a session summary records
# what was true when it was written, and a rename must not turn it red.
docs-check:
	python3 scripts/check-docs-references.py

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
