# aws-devops-sdet-demo

A deploy → test → approve → promote → destroy pipeline on AWS, which reports on
itself and then deletes almost all of itself.

**Live dashboard: https://demo.uveapp.net** — it stays online when every
workload environment is gone, which is most of the time and is the point of it.

One FastAPI container behind an ALB on ECS Fargate, with PostgreSQL on RDS,
built and deployed entirely by GitHub Actions using short-lived OIDC
credentials. There are no static AWS keys anywhere in this repository or in its
GitHub configuration.

That claim gained a qualifier in Phase 19a and is more interesting with it. The
self-service level (**ADR-0034**, applied in Phase 19b and pressed by an
anonymous visitor in 19c) reverses the one direction of trust: everywhere else
GitHub authenticates to AWS over OIDC, and there AWS must authenticate to
GitHub, where no OIDC exists. So the honest sentence is *no static AWS keys
anywhere, and exactly one static GitHub credential, in Secrets Manager, readable
by one Lambda role.*

```text
build image → apply stage → migrate + seed → API, smoke and regression suites →
a human approves → the tested DIGEST is promoted to prod at
https://app.demo.uveapp.net → destroy both, verified against the AWS CLI
```

Every step of that sentence runs through Actions with **no manual AWS
operation**. That is the claim the project exists to make, and it has been
observed end to end rather than assembled from parts that each worked once.

## What it is meant to show

```text
DevOps          Terraform modules and seven root state levels, OIDC-only CI/CD,
                promotion by digest, a guarded teardown that verifies itself
Cloud           a dedicated AWS Organizations member account, IAM Identity
                Center for humans, VPC/ALB/ECS/RDS, CloudWatch, Budgets
QA / SDET       suites split by DIRECTORY so the destructive ones cannot reach
                prod, an assertion that a browser action reached RDS, a guard
                that fails when a spec belongs to no suite
Security        no static AWS keys (see the qualifier above), prod's deploy
                role trusts no branch, a database
                that is not publicly accessible, a private site bucket behind
                CloudFront with Origin Access Control
FinOps          no NAT, no EKS, nothing always-on except cents of permanent
                surface; a destroy workflow that is part of every cycle
```

## The application

Deliberately small. It exists so the delivery pipeline has something real to
carry and the test suites have something real to drive.

```text
GET    /health           liveness, no database
GET    /api/health       readiness
GET    /api/db-check     connects to PostgreSQL and says so
POST   /api/items        201, 409 on a duplicate name, 422 on bad input
GET    /api/items        one page: {items, count, total, limit, offset}
                         limit 1..100 (default 20), offset >= 0, 422 outside
GET    /api/items/{id}   200, 404 when absent
PATCH  /api/items/{id}   200, 404, 409 on a taken name, 422 on an empty patch
DELETE /api/items/{id}   204, 404 when absent
GET    /                 a static page that drives the API from the browser
```

## Run it locally

Needs Docker with the Compose plugin, plus `node` and `python3` for the suites.
PostgreSQL is **not** published to the host; only the app port is.

```bash
make local-up                       # postgres + app, builds the image
curl -s http://localhost:8000/health
curl -s http://localhost:8000/api/db-check
make migrate && make seed           # Alembic to head, then an idempotent seed
make test-unit                      # in-process: the shape of the JSON log line
make test-db                        # the seed row is really in the database
make test-api                       # 52 HTTP contract cases (pytest + httpx)
make test-smoke                     # read-only Playwright
make test-regression                # destructive, then asserts the UI write in RDS
make local-down
```

`make test-regression` is the interesting one: it creates a row **through the
browser**, then a separate process looks that exact row up in PostgreSQL. Both
halves are given the same probe name at parse time, so they cannot drift apart.

Every one of these commands also runs in `ci.yml`, on the same Compose stack,
with no AWS credentials present anywhere in that workflow.

`ci.yml` also runs these checks on the same push, none of which touch AWS. The
list carries no total: "five checks" stood above five lines here while three
others had already been added to `ci.yml`, which is the same defect as the count
that read "three levels" above a list of four.

```text
make secret-scan      gitleaks over the full history, every ref
make iac-scan         Checkov over infra/, decisions recorded in .checkov.yaml
make image-scan       Trivy over the image this commit builds, allowlist in
                      .trivyignore
make action-pins      every third-party action is pinned to a commit SHA
make docs-check       the living documents describe things that exist
make site-data-check  the map's data still matches infra/, and every resource
                      block belongs to a display group
make site-page-check  the committed page is what its template builds
make timeline-check   an apply that was killed folds into an INCOMPLETE
                      timeline, never a plausible complete one
```

Each one refuses rather than passing when it cannot actually scan — a missing
scanner, a shallow clone or an empty directory all produce the clean-looking
nothing this project has been caught by before.

## Run it in AWS

Nothing here deploys on a push. All three AWS workflows are `workflow_dispatch`
only, because a push to `main` must not create billable infrastructure — it did
once, and that is why.

```text
deploy-stage     build, push, apply stage, migrate/seed, run every suite
promote-prod     resolve the digest a green stage run tested and apply prod.
                 It NEVER rebuilds. Pauses for a required reviewer.
destroy          environment: stage | prod, confirm: DESTROY.
                 Destroys the ALB first, then everything else, then verifies
                 that nothing billable is left.
publish-site     syncs the dashboard; touches no workload infrastructure
```

A cycle takes roughly 15 minutes to a live prod, most of it RDS.

On a **fresh account** the permanent levels are applied by hand first, under an
SSO session, in the order given in `docs/preflight-inventory.md`. On this
account they are all applied already, so a cycle starts straight at
`deploy-stage`.

## The eight state levels

Six permanent, two per-cycle. The split is the design, not an accident of
layout: **the exhibit cannot be destroyed by the thing it exhibits.**

```text
infra/bootstrap        S3 state bucket                            permanent
infra/bootstrap-oidc   OIDC provider + one deploy role per env    permanent
infra/shared-ecr       the registry prod promotes from            permanent
infra/dns              delegated zone + ALB certificate           permanent
infra/public-site      the dashboard: S3 + CloudFront + OAC       permanent
infra/self-service     the public launch button and its refusals  permanent
infra/envs/stage       VPC, ALB, ECS, RDS                         per cycle
infra/envs/prod        the same, behind an approval gate          per cycle
```

`infra/self-service` is applied and **the button is live**. Every refusal it
makes was broken on purpose first (**ADR-0035**) in Phase 19b, it was pressed by
an anonymous visitor in 19c, and since 19g a launch cancelled mid-apply reclaims
itself: the run's own teardown adopts what never entered Terraform state and
destroys it, with no human and no watchdog (**ADR-0038**). What bounds a stranger
is a 90-minute TTL per launch and three launches per UTC day, both enforced
server-side, and the reach is stage only, by IAM rather than by an input.

Anything that must survive a teardown lives above the environments — including
the container registry, whose image prod is running, and the dashboard, which is
the artifact that proves the teardown worked.

`docs/architecture.md` explains the request path, why there is no NAT Gateway,
and why the ALB has to be destroyed before the internet gateway.

## Tests

Where a spec lives decides where it runs (**ADR-0025**):

```text
tests/unit/                         in-process, no network       ci + local
tests/api/                          HTTP contract, DESTRUCTIVE   stage + local
tests/playwright/tests/smoke/       read-only     the ONLY suite prod runs
tests/playwright/tests/regression/  DESTRUCTIVE                  stage + local
tests/db/                           seed assertion, run as an ECS task in AWS
```

`tests/unit/` is the only suite that runs against imported code rather than
against a URL, and it exists for one reason: the 5xx alarm reads the
application's own log, so the SHAPE of that log is a contract. Whether `status`
is a number and whether an unhandled exception is logged at all are invisible
to every other suite here — and both have a failure mode where the alarm simply
never fires while looking correct (**ADR-0032**).

A spec outside those directories belongs to no Playwright project, would run in
no suite, and would be reported by nothing. `make test-spec-coverage` fails on
it — and was verified by being made to fail on purpose.

The published Playwright report is linked from the dashboard and opens **without
a GitHub account**, which an Actions artifact does not.

## Cost

Between cycles the account bills a state bucket, a small container registry, one
hosted zone and a CloudFront distribution serving one page — cents. A cycle adds
an ALB, an ECS service and an RDS instance for as long as it is up, which is
usually under an hour.

`app.demo.uveapp.net` is therefore a **dead name most of the time, by design**
(ADR-0017 D2a): prod is created and destroyed with every cycle and keeps no data
between them. `demo.uveapp.net` — the dashboard — is always up.

## Documentation

```text
docs/architecture.md        the levels, the request path, the trade-offs
docs/demo-script.md         a 10-minute walkthrough, traps included
docs/phase-gates.md         the cursor: what is done, what is next
docs/next-phases.md         the plan, MVP track and polish track
docs/decisions/             ADRs — the "why", and the one artifact that cannot
                            be reconstructed from the code afterwards
docs/security-posture.md    what a public repository does and does not expose
docs/preflight-inventory.md rebuilding from an empty account
docs/sessions/INDEX.md      one row per working session
```

## Status

The MVP cycle is complete and proven. What is deliberately not built, and why,
is listed at the end of `docs/next-phases.md` — being able to explain why
something was *not* built is part of the exhibit.

The phase cursor in `docs/phase-gates.md` is the only file that claims to know
where the project currently stands. Nothing else does, including this one.
