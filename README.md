# aws-platform-demo

A deploy → test → promote → destroy pipeline on AWS, which reports on
itself and then deletes almost all of itself. Started as a one-container
DevOps/SDET demo under the name `aws-devops-sdet-demo`; the AWS names
underneath keep that name (ADR-0102).

**Live dashboard: https://demo.uveapp.net** — it stays online when every
workload environment is gone, which is most of the time and is the point of it.

Three containers on ECS Fargate - `web`, the interface, and `api`, the domain,
behind one ALB; `worker`, consuming the api's events from SQS - with PostgreSQL
on RDS,
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
the tested DIGEST is promoted to prod at https://app.demo.uveapp.net →
destroy both, verified against the AWS CLI
```

Every step of that sentence runs through Actions with **no manual AWS
operation**. That is the claim the project exists to make, and it has been
observed end to end rather than assembled from parts that each worked once.

**`a human approves` used to stand between the suites and the promotion, and it
is gone (ADR-0068).** The button on the dashboard now runs that whole sentence
unattended — three times a day, one environment at a time, holding prod up for
five visible minutes before destroying it. What survives is the gate that
matters most: a digest is promoted only if its stage suites went green. What
does not survive is the person, on the owner's own promotions as well as on a
stranger's. The trade is argued in ADR-0068 rather than glossed here.

## What it is meant to show

```text
DevOps          Terraform modules and nine root state levels, OIDC-only CI/CD,
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
FinOps          no NAT, EKS only in the lab and destroyed with it, nothing
                always-on except cents of permanent
                surface; a destroy workflow that is part of every cycle
```

## Why it is built this way

Every line is a decision record in `docs/decisions/`, with the argument or
the incident behind it; the ones learned the hard way say so.

**The flow**
- build three images → stage → tests (contract, smoke, regression, a database
  assertion) → the same digests to prod → prod smoke → a five-minute hold →
  destroy everything, prod included
- a Kubernetes lab beside stage, the same digests, destroyed with it (ADR-0097)
- immutable registry; a release is the set of digests that passed the prod
  smoke; rollback targets a pointer in SSM that outlives the environment
  (ADR-0029)
- the release tag is put on the commit through the API - no token here holds
  `workflows: write` (ADR-0066)
- three environments created and destroyed per cycle; six permanent levels
  no workflow can destroy

**Identity - no static keys**
- humans: IAM Identity Center only, sessions expire (ADR-0002)
- CI: GitHub OIDC, one role per environment, the provider at its own permanent
  level (ADR-0003, ADR-0015)
- prod's role trusts no branch - only the `prod` environment's subject
  (ADR-0021); the page-publish role trusts environment subjects only, learned
  from one `AssumeRoleWithWebIdentity` refusal
- one task role per service, with rights on its own direction of its own queue;
  the database secret readable by the execution role alone; the same rights as
  IRSA on the cluster, where the chart refuses an empty role ARN (ADR-0097)
- not done, and said so: both services connect to PostgreSQL as one user
  (ADR-0098 D2)

**Secrets - none in the repository, none in a workflow**
- the database password: Terraform → Secrets Manager → the container, by ARN;
  on the cluster a Kubernetes Secret filled from Secrets Manager (ADR-0005)
- the button is a GitHub App; its private key is in Secrets Manager, readable
  by two Lambdas (ADR-0034)
- the runner's token is the only credential that talks to GitHub; it also
  writes the run history into the page's bucket, so a visitor's browser never
  calls GitHub (ADR-0100)
- gitleaks over the full history on every push

**The public path - anyone may press the button, nobody can hurt anything**
- a Lambda behind a Function URL with a DynamoDB control store: one cycle at a
  time, three a day, a 90-minute deadline written into every resource's tags;
  five refusals, each with a break test that proves it fires (ADR-0035)
- the lock is released by the last job after every destroy; a failed destroy
  keeps it (ADR-0036)
- a watchdog outside the devbox tears down by tag whatever outlives its
  deadline; it once took a live stage because a default made the owner's
  cycle look public - the default is empty now and the record keeps the
  timeline
- resources a cycle created and Terraform did not are adopted into state
  before the teardown, not left for the bill (ADR-0038, ADR-0041)

**The page says only what it observed**
- every state is read back out of AWS after the run, never inferred from a
  green check (ADR-0054); the released line is reported while a branch is
  being proven (ADR-0093)
- the cost of a cycle is folded from the real teardown and refuses a pair it
  cannot vouch for (ADR-0046)
- the estate diagram is generated from the modules' inputs and `helm template`,
  every edge citing the file and line it was read from (ADR-0099); the services
  are declared once, and seven hand-written copies are held to that file by a
  gate (ADR-0101)
- one list of gates serves CI and the end of a session, and discovers a gate
  that went missing - it has caught this repository's own holes twice

**Supply chain and cost**
- third-party actions pinned by commit SHA, with a check that keeps them so
  (ADR-0030); Trivy on the images, Checkov on the IaC, Dependabot on five
  manifests
- base images from AWS's mirror of the official ones, after one reset
  connection to Docker Hub ended a public launch in two seconds
- no NAT gateway; spot nodes in the lab; a budget with an alarm; everything
  destroyed, and the price of a cycle on the page

**Deliberately not here**
- Argo CD or Flux; a WAF or CloudFront in front of the application;
  per-service database users, yet - each with its reason at the end of
  `docs/next-phases.md`

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
```

Everything above is the `api` container. The page a browser opens at `/` is
the `web` container - nginx serving a static file whose JavaScript drives the
API on the same origin - and the load balancer is what puts the two behind one
name (ADR-0095). Behind both, a `worker` container consumes `item.created`
from an SQS queue and stamps `processed_at` on the row; a message it can never
process goes to a dead-letter queue with an alarm on it (ADR-0096).

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
make node-states-check
                      every resource a cycle touches lands on a node of the map,
                      is recorded as deliberately not drawn, or is named unknown
make results-check    a run's report decides what a suite node says, and what
                      the report does not cover is named rather than coloured
make live-state-check the page's own run-layer logic, lifted out of the BUILT
                      page and folded against recorded Actions observations: a
                      node with no step of its own never claims to be running,
                      and a phase that finished mid-run says so instead of
                      reading as one that never ran
make page-tense-check the same block, asked WHEN each figure is true: a duration
                      printed mid-run belongs to the cycle before it, and a node
                      no timeline can carry never says `not run yet`
make page-freshness-check
                      the built page driven in a browser: a tab left open must
                      converge on what a fresh load of the same sources shows.
                      Needs chromium, so it runs beside the suites rather than
                      with the gates above
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

## The nine state levels

Six permanent, three per-cycle. The split is the design, not an accident of
layout: **the exhibit cannot be destroyed by the thing it exhibits.**

```text
infra/bootstrap        S3 state bucket                            permanent
infra/bootstrap-oidc   OIDC provider + one deploy role per env    permanent
infra/shared-ecr       the registry prod promotes from            permanent
infra/dns              delegated zone + ALB certificate           permanent
infra/public-site      the dashboard: S3 + CloudFront + OAC       permanent
infra/self-service     the public launch button and its refusals  permanent
infra/envs/stage       VPC, ALB, ECS, RDS                         per cycle
infra/envs/prod        the same, from the digests stage tested     per cycle
infra/envs/lab         VPC, EKS, RDS - the same digests by Helm    per cycle
```

`infra/self-service` is applied and **the button is live**. Every refusal it
makes was broken on purpose first (**ADR-0035**) in Phase 19b, it was pressed by
an anonymous visitor in 19c, and since 19g a launch cancelled mid-apply reclaims
itself: the run's own teardown adopts what never entered Terraform state and
destroys it, with no human and no watchdog (**ADR-0038**). What bounds a stranger
is a 90-minute TTL per launch and three launches per UTC day, both enforced
server-side; since **ADR-0068** the public path runs the whole cycle, prod and
the lab included, and gives every environment back.

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
