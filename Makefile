# Ubuntu-compatible developer commands for the v0 local stack.
# All container commands run on the Lightsail devbox via docker compose.

.PHONY: local-up local-down migrate seed test-smoke test-regression test-api \
        test-unit test-db test-ui-db test-spec-coverage docker-build tf-fmt \
        tf-validate docs-check secret-scan iac-scan image-scan action-pins \
        self-service-package self-service-cors-check site-page site-page-check \
        site-data site-data-check timeline-check node-states-check \
        suite-inventory suite-inventory-check results-check live-state-check \
        publish-prefixes-check

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
# The second probe (Phase 16a): created under another name and RENAMED through
# the edit form, so the assertion can require updated_at > created_at.
UI_EDIT_PROBE_NAME ?= ui-edit-probe-$(shell date +%s)

# Read-only Playwright suite. The ONLY suite prod runs (ADR-0025).
# Installs node deps + chromium on first run.
test-smoke:
	cd tests/playwright && npm install && npx playwright install --with-deps chromium \
	  && BASE_URL=$(BASE_URL) npx playwright test --project=smoke

# Destructive Playwright suite, plus the database assertion that proves the
# browser's write reached PostgreSQL. Never run against prod.
test-regression:
	cd tests/playwright && npm install && npx playwright install --with-deps chromium \
	  && BASE_URL=$(BASE_URL) UI_PROBE_NAME=$(UI_PROBE_NAME) UI_EDIT_PROBE_NAME=$(UI_EDIT_PROBE_NAME) \
	     npx playwright test --project=regression
	$(MAKE) test-ui-db UI_PROBE_NAME=$(UI_PROBE_NAME) UI_EDIT_PROBE_NAME=$(UI_EDIT_PROBE_NAME)

# Assert that the row the UI created exists in the database. Reuses the app
# image, which already contains the script and the driver.
test-ui-db:
	docker compose run --rm -e UI_PROBE_NAME=$(UI_PROBE_NAME) \
	  -e UI_EDIT_PROBE_NAME=$(UI_EDIT_PROBE_NAME) app python scripts/assert_ui_write.py

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
# Set API_JUNIT to a path and pytest also writes a junit report there, which is
# what scripts/fold-results.py reads (ADR-0042 D5). Empty by default: a local
# run should not scatter report files, and a workflow asks for one explicitly.
API_JUNIT ?=
test-api:
	@python3 -m venv $(API_VENV) 2>/dev/null || { \
	  echo "could not create a virtualenv - install python3-venv (apt install python3-venv)"; exit 1; }
	@$(API_VENV)/bin/pip install -q --upgrade pip
	$(API_VENV)/bin/pip install -q -r tests/api/requirements.txt
	BASE_URL=$(BASE_URL) $(API_VENV)/bin/pytest tests/api -q $(if $(API_JUNIT),--junitxml=$(API_JUNIT))

# In-process tests: things no HTTP client can observe from outside. Today that
# is the SHAPE of the JSON access line the 5xx alarm reads (ADR-0032), and the
# REFUSALS the public launch endpoint makes when its control store fails
# (ADR-0035) — an endpoint refusing correctly and one refusing because its store
# is broken look identical from outside, and only one of them is a guardrail.
# No network, no database, no running stack — so this is the one suite that can
# run before `make local-up`.
#
# Two source roots on PYTHONPATH, because the two subjects live in two places:
# the application in app/, the launch refusals in infra/self-service/src/, which
# is deliberately the same directory Terraform packages for the Lambda.
UNIT_VENV := .venv-unit
test-unit:
	@python3 -m venv $(UNIT_VENV) 2>/dev/null || { \
	  echo "could not create a virtualenv - install python3-venv (apt install python3-venv)"; exit 1; }
	@$(UNIT_VENV)/bin/pip install -q --upgrade pip
	$(UNIT_VENV)/bin/pip install -q -r tests/unit/requirements.txt
	PYTHONPATH=app:infra/self-service/src $(UNIT_VENV)/bin/pytest tests/unit -q

# Build the Lambda deployment package for infra/self-service.
#
# The Python runtime provides boto3 and nothing else this needs; minting a
# GitHub App installation token means signing an RS256 JWT, so PyJWT and
# cryptography are vendored. --platform + --only-binary because the wheel has to
# match the Lambda runtime, not the machine that runs this - a devbox-built
# cryptography would import fine here and fail in AWS with a symbol error.
#
# Two refusals, the same shape as the scanners:
#
#   pip missing      an empty package deploys happily and fails at the first
#                    request, in a place nothing is watching.
#   nothing vendored a directory containing only the handlers is what a
#                    half-finished build looks like, and Terraform's size
#                    precondition would then be the only thing between it and
#                    a function that cannot sign a JWT.
SELF_SERVICE_SRC := infra/self-service/src
SELF_SERVICE_BUILD := infra/self-service/build/package
self-service-package:
	@command -v pip3 >/dev/null 2>&1 || { echo "self-service-package: pip3 is not on PATH. Refusing to build an empty package."; exit 1; }
	rm -rf $(SELF_SERVICE_BUILD)
	mkdir -p $(SELF_SERVICE_BUILD)
	pip3 install -q -r $(SELF_SERVICE_SRC)/requirements.txt \
	  --platform manylinux2014_x86_64 --implementation cp --python-version 3.12 \
	  --only-binary=:all: --upgrade --target $(SELF_SERVICE_BUILD)
	cp $(SELF_SERVICE_SRC)/*.py $(SELF_SERVICE_BUILD)/
	@[ -d $(SELF_SERVICE_BUILD)/jwt ] || { echo "self-service-package: PyJWT is not in the package, so the function could not sign a JWT. Refusing."; exit 1; }
	@echo "self-service-package: $$(du -sh $(SELF_SERVICE_BUILD) | cut -f1) in $(SELF_SERVICE_BUILD)"

# Exactly ONE Access-Control-Allow-Origin header on a real cross-origin request.
#
# Both numbers are failures. TWO means the handler sets the header AND the
# Function URL's cors{} block sets it, which is invalid per the Fetch spec and
# is what broke the button on its first press in 19c - the function answered 200
# every time and the browser threw the response away. ZERO means the cors{} block
# is gone and the page cannot read the reply either.
#
# It has to be asked WITH an Origin header. Without one the Function URL's CORS
# layer stays out of it and only the handler answers, which is a request no
# browser makes and the one shape in which this defect is invisible - that is
# exactly how it was missed. Preflight is no good for this either: OPTIONS is
# answered by the Lambda service instead of the function, so the two never meet.
self-service-cors-check:
	@test -n "$(LAUNCH_URL)" || { echo "self-service-cors-check: set LAUNCH_URL (terraform -chdir=infra/self-service output -raw launch_url). Refusing to check nothing."; exit 1; }
	@test -n "$(ALLOWED_ORIGIN)" || { echo "self-service-cors-check: set ALLOWED_ORIGIN. Refusing to guess the origin the check depends on."; exit 1; }
	@n=$$(curl -sS -i -H "Origin: $(ALLOWED_ORIGIN)" "$(LAUNCH_URL)" | grep -ci '^access-control-allow-origin:' || true); 	 echo "access-control-allow-origin headers: $$n"; 	 [ "$$n" = "1" ] || { echo "self-service-cors-check: expected exactly 1, got $$n - a browser will refuse this response."; exit 1; }; 	 echo "self-service-cors-check: ok"

# Run the standalone seed DB assertion against postgres, on the compose network.
# Reuses the app image (has sqlalchemy + psycopg2-binary) and mounts the test.
test-db:
	docker compose run --rm -v "$(PWD)/tests/db:/tests-db" app python /tests-db/assert_seed.py

# Every make target, repo path, route and workflow named in the LIVING documents
# must exist. Historical documents are not checked: a session summary records
# what was true when it was written, and a rename must not turn it red.
docs-check:
	python3 scripts/check-docs-references.py

# site/index.html is a BUILD OUTPUT (20a). The source is
# assets/index.template.html, which lives outside site/ because publish-site
# syncs the whole of site/ to the public bucket. The build folds the AWS
# Architecture Icons into one inline sprite and injects it, so the published page
# stays a single file with no request-time dependency.
#
# site-page-check is the gate, and runs in ci.yml: the committed page must be
# byte-identical to a fresh build. Without it an edit to the OUTPUT survives
# until the next build silently reverts it. It refuses on a missing icon and on a
# template that has lost its marker - both exercised on purpose.
site-page:
	python3 scripts/build-site-page.py

site-page-check:
	python3 scripts/build-site-page.py --check

# The map's data, GENERATED from infra/ and tests/ rather than written (ADR-0039
# D1). site-data rewrites it; site-data-check is the gate, and runs in ci.yml.
#
# A COVERAGE gate, not a depiction one. It cannot tell whether the picture is a
# good picture. It can tell that every resource block under infra/ is assigned to
# exactly one display group - including the group that means "deliberately not
# shown", which is green and recorded rather than silently missing - that no
# assignment names a resource that has been deleted, that no group's resources
# live in a level the map never draws, and that the committed JSON is
# byte-identical to a fresh generation.
site-data:
	python3 scripts/generate-topology.py

site-data-check:
	python3 scripts/generate-topology.py --check

# The suites' inventory, COLLECTED from the suites by the tools that run them
# (ADR-0042 D1): pytest --collect-only, playwright --list, assert_seed.py --list.
# A file count is not an inventory and a sentence written beside a suite is the
# sixth stale place waiting to happen.
#
# Unlike site-data-check this needs the suites' own dependencies, so it belongs
# to ci.yml's `tests` job, after the targets that build them, and NOT beside the
# map's gate in `checks` (ADR-0042 D2). The venv paths are passed in from here,
# where `make test-unit` and `make test-api` already define them - the script
# refuses rather than guessing a location.
#
# Refusals exercised on purpose: a renamed test, the two copies of the db
# assertion disagreeing, a suite collecting zero, a pinned version the machine
# does not have, and a spec answering to a project from outside its directory.
INVENTORY_ENV := UNIT_PYTEST=$(UNIT_VENV)/bin/pytest API_PYTEST=$(API_VENV)/bin/pytest
suite-inventory:
	$(INVENTORY_ENV) python3 scripts/collect-suites.py

suite-inventory-check:
	$(INVENTORY_ENV) python3 scripts/collect-suites.py --check

# The fold from Terraform's own -json event stream to a timeline (ADR-0039 D2),
# checked against fixtures that are REAL terraform output - including one stream
# from a terraform process that was killed mid-apply, which is the case the whole
# thing exists for. Regenerate them with tests/fixtures/timeline/generate.sh;
# they cost nothing and touch no cloud, because every resource in them is the
# built-in terraform_data.
#
# The claim under gate: a run that dies mid-apply produces a timeline marked
# INCOMPLETE, never a plausible complete one. The complete and errored cases are
# checked just as exactly, because a fold that called everything incomplete would
# satisfy that sentence and be useless.
timeline-check:
	python3 scripts/check-timeline.py

# The join from a timeline onto the map's nodes (ADR-0039 D4), and the reason it
# is a script on the runner rather than a few lines on the page: written twice,
# in JavaScript there and in Python here, it would be one definition on two
# hosts - which has already cost this project a scan of the wrong image.
#
# The claim under gate: a resource a cycle created is drawn on the map, is
# recorded as deliberately not drawn, or is reported as UNKNOWN - never silently
# absent. Most cases fold a real terraform run from tests/fixtures/timeline/,
# including the one whose resources live inside MODULES, which is the shape every
# resource in infra/ actually has. One case is hand-written and says so:
# terraform_data finishes in zero seconds, so no real run can tell "the longest
# member" apart from "the first member".
node-states-check:
	python3 scripts/check-node-states.py

# The join from the test reporters' own output onto the map's suite nodes
# (ADR-0042 D5). Same shape as node-states-check and for the same reason: written
# twice, in JavaScript on the page and in Python here, it would be one definition
# on two hosts.
#
# The claim under gate: a run's report decides what a suite node says, and
# everything the report does not cover is NAMED - unobserved, not_run, unknown -
# rather than coloured. Most cases are real reporter output, including a
# Playwright JSON file cut in half, which is what a killed run leaves on disk.
# One is hand-written and says so: no green api report exists to record until a
# cycle produces one.
#
# Needs no test dependencies - it reads files - so unlike suite-inventory-check
# it runs beside the map's other gates.
results-check:
	python3 scripts/check-results.py

# The one piece of map logic that CANNOT move to Python, gated where it lives
# (ADR-0043 D3). The other two folds run on the runner and are checked there
# precisely so they are not written twice; this one reads the Actions API in the
# visitor's browser, and there is no run afterwards to fold. So the gate lifts
# the marked block OUT OF site/index.html and runs that, verbatim, against
# recorded observations - the code the visitor executes, not a copy of it.
#
# The claim under gate, in the three sentences 20c wrote down while watching a
# live cycle and had no way to check afterwards: a node with no step of its own
# is never reported as running on its own behalf; a phase whose steps are over in
# a run still going is FINISHED, which is not the same thing as never having run;
# and a suite answers for its own step, not for the phase it happens to be drawn
# in.
#
# It reads the BUILT page, so a template edited without rebuilding reddens it -
# the same property site-page-check exists for, arriving here for free.
live-state-check:
	node scripts/check-live-state.mjs

# Two scripts share the public bucket and are not peers: publish-status.sh
# WRITES what a run observed, publish-site.sh syncs site/ over the top of it with
# --delete. The exclusion list in the second is therefore a piece of the first,
# and keeping the two in step was a rule written in a comment.
#
# On 2026-08-08 the rule broke exactly as its own comment predicted: results/ was
# added to the writer and never to the exclusions, and the first push to main
# that touched site/ deleted every published test result. The bucket has no
# versioning. This reads the correspondence out of both files instead (ADR-0044).
publish-prefixes-check:
	python3 scripts/check-publish-prefixes.py

# The two ends of a session, as commands rather than as prose in four documents
# (ADR-0033). Local only: on a CI checkout the tree is always clean and HEAD
# always matches, so the interesting checks could not fail there.
session-open:
	./scripts/session-open.sh

session-close:
	./scripts/session-close.sh

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
# The image name is a LITERAL here and in docker-compose.yml, and the two are
# checked against each other. It used to be whatever `docker compose config
# --images app` answered, which is a different answer on different Compose
# versions: on a GitHub runner it ignored the service filter and the scan was
# handed postgres:16. That failed loudly only because postgres was not built in
# that job; where it is, a scan of the wrong image reads exactly like a clean
# one.
APP_IMAGE ?= aws-devops-sdet-demo-app:local
TRIVY_REPORT ?= trivy-report.json
image-scan:
	@command -v trivy >/dev/null 2>&1 || { echo "image-scan: trivy is not on PATH. Refusing to pass without scanning anything."; exit 1; }
	@grep -q "image: $(APP_IMAGE)" docker-compose.yml || { echo "image-scan: docker-compose.yml does not build $(APP_IMAGE). The two names have drifted, so this would scan an image nothing here produces. Refusing."; exit 1; }
	@docker image inspect "$(APP_IMAGE)" >/dev/null 2>&1 || { echo "image-scan: $(APP_IMAGE) has not been built - run make docker-build first. Refusing to scan nothing."; exit 1; }
	@echo "image-scan: trivy $$(trivy --version | head -1 | awk '{print $$2}'), image $(APP_IMAGE)"
	trivy image --scanners vuln --severity HIGH,CRITICAL --exit-code 0 \
	  --format json --output $(TRIVY_REPORT) "$(APP_IMAGE)"
	@python3 scripts/summarise-trivy.py $(TRIVY_REPORT)

# Every third-party action is pinned to a commit SHA, and stays that way.
# A tag is mutable and several jobs here hold id-token: write, so the code
# behind a tag sits inside the trust boundary the OIDC story rests on.
action-pins:
	python3 scripts/check-action-pins.py

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
