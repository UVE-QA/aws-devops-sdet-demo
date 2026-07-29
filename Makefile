# Ubuntu-compatible developer commands for the v0 local stack.
# All container commands run on the Lightsail devbox via docker compose.

.PHONY: local-up local-down migrate seed test-smoke test-regression test-api \
        test-db test-ui-db test-spec-coverage docker-build tf-fmt tf-validate \
        docs-check secret-scan iac-scan image-scan

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

# Secret scan over the FULL history, EVERY ref. One definition, two hosts: CI
# installs a pinned, checksum-verified gitleaks and then calls this target, so
# what runs in Actions is what runs on the devbox.
#
# Two refusals rather than one scan:
#
#   gitleaks missing    a scanner that is not installed reports nothing, and
#                       nothing is what a clean repository also reports.
#   shallow clone       the same shape. `actions/checkout` defaults to depth 1;
#                       a scan of one commit is green on a history full of keys.
#
# --log-opts="--all" because the default scans HEAD's branch only, and the
# 2026-07-26 sweep that this replaces covered every ref.
# --redact because the gate must not publish, in the logs of a public
# repository, the secret it just found.
GITLEAKS_REPORT ?= gitleaks-report.json
secret-scan:
	@command -v gitleaks >/dev/null 2>&1 || { echo "secret-scan: gitleaks is not on PATH. Refusing to pass without scanning anything."; exit 1; }
	@[ "$$(git rev-parse --is-shallow-repository)" = "false" ] || { echo "secret-scan: this clone is SHALLOW, so a scan proves nothing about the history. Refusing."; exit 1; }
	@echo "secret-scan: $$(gitleaks version), $$(git rev-list --all --count) commits across every ref"
	gitleaks git . --log-opts="--all" --redact --no-banner -v \
	  --report-format json --report-path $(GITLEAKS_REPORT)

# Static analysis of the Terraform tree. Same shape as secret-scan: one
# definition, two hosts, and refusals rather than a scan that proves nothing.
#
# Three refusals:
#
#   checkov missing     a scanner that is not installed reports no findings,
#                       and no findings is what a clean tree also reports.
#   config missing      .checkov.yaml carries BOTH the directory list and the
#                       46 skip decisions. Without it the command would scan
#                       the wrong thing and call it a pass.
#   zero checks         checkov exits 0 on a directory containing no Terraform.
#                       summarise-checkov.py refuses when nothing was evaluated,
#                       which is the specific way this gate would rot silently
#                       if infra/ were ever moved.
#
# The line it prints names the skip count, because a gate that does not say
# what it declined to check is a gate you cannot review.
CHECKOV_REPORT ?= checkov-report.json
iac-scan:
	@command -v checkov >/dev/null 2>&1 || { echo "iac-scan: checkov is not on PATH. Refusing to pass without scanning anything."; exit 1; }
	@[ -f .checkov.yaml ] || { echo "iac-scan: .checkov.yaml is missing, so both the directory list and the skip decisions are gone. Refusing."; exit 1; }
	@echo "iac-scan: checkov $$(checkov --version), $$(grep -c '^  - CKV' .checkov.yaml) checks skipped by decision"
	@checkov --config-file .checkov.yaml -o json > $(CHECKOV_REPORT); status=$$?; \
	  python3 scripts/summarise-checkov.py $(CHECKOV_REPORT) || exit 1; \
	  exit $$status

# Vulnerability scan of the image this project actually ships, not of a base
# image named in a Dockerfile. The image id comes from Compose, so the target
# scans whatever `make docker-build` just produced.
#
# The scan runs with --exit-code 0 and WITHOUT --ignore-unfixed on purpose: the
# uploaded report then contains every HIGH and CRITICAL, and the decision about
# which of them should stop a build is made in summarise-trivy.py, where it can
# be read. Gating only on findings that have a fix keeps the gate actionable;
# reporting the rest keeps "not gated" from turning into "not known".
#
# Three refusals, the same shape as the other two scanners:
#
#   trivy missing    a scanner that is not installed finds nothing.
#   no image         Compose names no image, or it was never built. Scanning
#                    nothing is not the same as finding nothing.
#   empty report     a report with no results at all is a refusal, not a pass.
TRIVY_REPORT ?= trivy-report.json
image-scan:
	@command -v trivy >/dev/null 2>&1 || { echo "image-scan: trivy is not on PATH. Refusing to pass without scanning anything."; exit 1; }
	@img=$$(docker compose config --images app 2>/dev/null | head -1); \
	  [ -n "$$img" ] || { echo "image-scan: docker compose names no image for the app service. Refusing."; exit 1; }; \
	  docker image inspect "$$img" >/dev/null 2>&1 || { echo "image-scan: $$img has not been built - run make docker-build first. Refusing to scan nothing."; exit 1; }; \
	  echo "image-scan: trivy $$(trivy --version | head -1 | awk '{print $$2}'), image $$img"; \
	  trivy image --scanners vuln --severity HIGH,CRITICAL --exit-code 0 \
	    --format json --output $(TRIVY_REPORT) "$$img"
	@python3 scripts/summarise-trivy.py $(TRIVY_REPORT)

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
