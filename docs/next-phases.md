# Next Phases — MVP-first plan

Replaces the unordered wish-list in `project-prompt.md` §14 with an ordered plan.

Two tracks:

```text
MVP track     Phases 9-13   the shortest path to a complete, shareable cycle
Polish track  Phases 14+    everything that makes it deeper, not possible
```

Shaped by **ADR-0017** (same account for prod, hybrid availability, HTTPS on an
owned domain, phased external access).

## Where the project actually stands

```text
Phase 0-7            done
Phase 8 (lifecycle)  done  — deploy → demo → destroy green end-to-end via Actions
Phase 8 (features)   NOT STARTED
Phase 9              done (2026-07-26) — prod, promotion by digest, HTTPS
Phase 10             local + CI green (2026-07-26), AWS run owed — see below
Phase 11.0           done (2026-07-26) — repository is public
```

Both environments are fully destroyed in AWS. Billing is the state bucket, the
shared registry and one hosted zone — cents. The OIDC provider and both deploy
roles exist (IAM, free), as does the wildcard certificate (free).

What the project can now do, proven end to end through Actions with no manual
AWS operation: deploy stage, gate on tests, pause for a human, promote the
tested image BY DIGEST to a prod environment reachable at
`https://app.demo.uveapp.net`, and destroy both.

What it still lacks: a public surface, and any test coverage beyond one smoke
test and a seed assertion. Those are Phases 10 and 11.

**Everything below this line is planned, not built.** No document in this repo
may describe any of it as implemented.

## The MVP finish line

Stated explicitly so "full cycle" cannot drift:

```text
one button  →  deploy stage  →  tests green  →  approval  →
prod live over HTTPS on the owned domain  →
dashboard showing the architecture, environment status, a link to prod and a
link to the test report  →  one button  →  everything destroyed,
dashboard still up
```

Anything not required by that sentence is polish and waits for Phase 14+.

## Invariants that apply to every phase

```text
- budget-safe by default: nothing new runs continuously without an explicit
  decision recorded in an ADR. Small fixed costs (~$0.50/month class) are fine.
- destroy must pass end-to-end at the END OF EVERY PHASE — not just at the end
  of the MVP. Skipping the teardown run between steps is exactly how this
  project accumulated latent teardown bugs before; each one cost more to find
  later than a destroy run costs now.
- any structural decision gets an ADR before it gets code. ADRs are the one
  artifact that cannot be reconstructed from the repository afterwards.
- an app contract change is not done until its tests are updated (app-dev → test-dev)
- no static AWS keys, ever
- a fix to a SHARED invariant is applied to EVERY environment directory in the
  same commit, not only to the one currently being exercised. The C2 refactor
  (ADR-0015) and the ecs/alb ordering fix (ADR-0016) were both applied to stage
  only; prod silently kept the broken shape for seven weeks.
- CI validates EVERY IaC directory. An unvalidated directory rots invisibly —
  `infra/envs/prod` could not have planned against the current modules and
  nothing reported it.
```

---

# MVP track

## Phase 9 (M1) — Prod environment, promotion, HTTPS  [DONE 2026-07-26]

Closed by `docs/sessions/2026-07-26-phase-9-1-prod-promotion-https.md`. HTTPS
landed on a delegated subdomain, `demo.uveapp.net`, per **ADR-0024** — the
parent zone turned out to live in the Organizations management account, which
makes delegation the only acceptable route rather than the convenient one. The
plan below is kept as written for the record.

**First, deliberately.** This is the only genuinely missing half of the cycle,
and it is the riskiest work in the plan. ADR-0015 and ADR-0016 both came from
bugs that surfaced on a path's **first real run**; a second deploy role and a
second environment are two such new paths. Do it while the context is fresh,
and do not compress it.

### 9.0 — Reconcile the existing prod scaffold FIRST

The starting point is not empty, and it is worse than empty: `infra/envs/prod`
was written in Phase 4 as a mirror of stage and was never updated by the C2
refactor. It looks finished and is not. Nothing else in this phase starts until
these are fixed:

```text
prod/main.tf still contains module "iam_github_oidc"
   → the exact construct ADR-0015 removed from stage because a destroy run
     under that role deletes its own permissions mid-run. Delete it from prod;
     both deploy roles belong in infra/bootstrap-oidc.

prod/main.tf passes db_secret_arn to that module
   → after C2 the module takes db_secret_arn_pattern. This directory cannot
     plan against the current modules at all, which proves CI's terraform
     validate does not cover it. Fix the validate scope as part of this step.

prod/main.tf has no depends_on = [module.alb] on the ecs module
   → commit 2c4162b was applied to stage only, so the ADR-0016 ENI/IGW
     teardown race is built into prod from birth.

prod declares its own ECR repository (…-app-prod)
   → conflicts with promotion-by-digest. Decide BEFORE writing promote-prod.yml:
     one shared ECR across environments (simplest, and what "never rebuild"
     implies) or an explicit cross-repository image copy step.

destroy.yml offers "prod" in its dropdown, nothing else supports it
   → today that choice is a trap, not a feature. Either wire it or remove it.
```

Done when: `terraform validate` passes for every directory under `infra/`, and
the prod config differs from stage only in name prefix, sizing and the
intentional prod-specific additions below.

### 9.1 — Build out prod

Per ADR-0017 D1: same AWS account, environment-level separation.

```text
infra/envs/prod            same modules, prefix <project>-prod-*,
                           state key prod/terraform.tfstate (already set)
bootstrap-oidc             a SECOND deploy role for prod; stage credentials
                           must not reach prod
GitHub Environment prod    with required reviewers — the approval gate,
                           free and built in
trust policy               add the environment:prod sub

promote-prod.yml
  - takes the image DIGEST from a green stage run; never rebuilds
  - waits for reviewer approval
  - terraform apply on prod
  - read-only smoke against prod

HTTPS (ADR-0017 D3)
  ACM certificate (us-west-2, regional) + Route53 record +
  443 listener on the ALB + HTTP→HTTPS redirect
  app.<domain> → prod ALB

destroy path for prod
  the same guarded workflow, including the targeted ALB destroy of ADR-0016
```

Explicitly NOT in this phase: automatic rollback (Phase 14).

Note per ADR-0017 D2a: prod is created and destroyed with every cycle, so **prod
keeps no data between cycles** and `app.<domain>` is a dead link most of the
time. RDS needs 5-10 minutes to create, which sets the cycle time at roughly 15
minutes to a live prod — never demo that wait live.

Done when: `stage → approve → prod → destroy both` runs through Actions with no
manual AWS operation, and `https://app.<domain>` returns 200 with a valid
certificate.
Cost: hosted zone ~$0.50/month. Prod is on-demand, so per-hour cost while up
matches stage.

## Phase 10 (M2) — Thin application slice  [CODE COMPLETE 2026-07-26, NOT CLOSED]

The code below is written, committed, validated against PostgreSQL on the devbox
and green in CI. **None of it has run against AWS**, so this phase is not done.
What the session produced, what it measured, and what it is still owed, is in
`docs/sessions/2026-07-26-phase-10-thin-application-slice.md`.

One thing the plan below did not anticipate, now recorded as **ADR-0025**: the
stage/prod split it describes in three lines did not exist in the workflows.
`promote-prod.yml` ran the whole `testDir` under a step named "read-only". The
split is now made by directory and enforced by a guard, rather than asserted in
a comment.


**Not the full domain build.** The cycle already works with today's trivial app —
but the dashboard would then link to a single smoke test, which proves nothing.
This phase exists to make "tests green" mean something, at minimum width.

```text
endpoints   POST /api/items      201 / 422 / 409 on duplicate name
            GET  /api/items      list
            DELETE /api/items/{id}   204 / 404
            Pydantic schemas, one Alembic migration extending demo_items,
            idempotent seed

ui          the same static HTML + fetch: table, create form, delete button.
            No React. It exists so Playwright has something real to drive.

tests       1 Playwright regression spec:  create → appears in list → delete
            1 DB assertion AFTER a UI action (UI → API → RDS, end to end)
            a handful of pytest/httpx contract cases including the negatives

split       stage: seeded, destructive regression is fine
            prod:  read-only smoke only
```

That last split is a real QA distinction and is rarely demonstrated in portfolio
projects — worth naming out loud at interview.

Full CRUD depth (PATCH, GET by id, pagination, the wider negative matrix) is
Phase 16.

Done when: the regression suite runs green in `ci.yml` against Compose, the
read-only smoke runs green against deployed prod, and the DB assertion proves a
UI action reached RDS.
Cost: **$0 extra** — runs inside the existing cycle.

## Phase 11 (M3) — Public dashboard

### 11.0 — Make the repository public FIRST  [DONE 2026-07-26, a1c4402]

**Executed early, during Phase 9.1.** Required reviewers — prod's approval gate —
are unavailable on a private repository outside Enterprise, so this step was
pulled forward rather than waiting for the dashboard. See ADR-0022 for the
sequencing and ADR-0023 for what the publication exposed and why it was
accepted. The history was NOT rewritten; the gitleaks run below is still owed.


The dashboard reads run history from the **public** GitHub API, which does not
work against a private repository without a token. This was an unstated
dependency when the phase was first written. A portfolio repository that cannot
be linked to is also a contradiction in itself: an interviewer needs the code.

Before building anything in this phase:

```text
- run gitleaks over the FULL history, not just HEAD. Phase 15 adds it to CI;
  this is the one case where it is needed earlier.
- decide CONSCIOUSLY about: the AWS account id 993912191738 (in backend.tf, in
  the state bucket name, throughout the docs), the devbox static IP, and the
  SSO start URL. None of these is a secret, but publishing them should be a
  decision rather than an accident.
- confirm .gitignore held across every commit: no .env, no *.tfstate,
  no *.tfvars anywhere in history.
```

Side effect worth having: once the repo is public, a chat session can clone it
over HTTPS and read the current docs itself. That removes the manual "upload
discussion-log.md to the Claude Project" ritual entirely, with no second working
copy on any laptop — the clone lives in the ephemeral session sandbox and dies
with it. Deliberately deferred to here rather than done now (2026-07-25).

### 11.1 — Build the dashboard

Per ADR-0017 D2 and D4 Wave A. The permanent public surface: the only thing that
stays online when every workload environment is destroyed.

```text
hosting     S3 (private) + CloudFront with Origin Access Control, on the owned
            domain. NOT GitHub Pages — see "why not Pages" below.

            MUST live in its own PERMANENT Terraform state level:
              infra/public-site/  →  key public-site/terraform.tfstate
            applied locally under demo-admin, never touched by any destroy
            workflow. If the dashboard lived in envs/*, the teardown would
            delete the very artifact that proves the teardown works.

            GOTCHA: an ACM certificate for CloudFront must be issued in
            us-east-1. The prod ALB certificate stays regional in us-west-2.
            Two certificates, two regions, one domain.

dns layout  <domain> / www.<domain>  →  dashboard via CloudFront  (always up)
            app.<domain>             →  prod ALB                  (on demand)

content     architecture diagram — what happens and in what order
            environment status, honestly showing "destroyed"
            link to prod (when up)
            link to the latest Playwright HTML report
            run history and the duration of the last cycle

            THE STAGES OF A RUN, WITH PER-STAGE STATUS — not just a final
            colour. Requested 2026-07-26 while watching `gh run watch` print
            exactly that in the terminal: what is planned, what is running,
            what is done. The visual form is open; the requirement is that a
            viewer can see WHERE a cycle is, not only whether it ended well.

plumbing    a publish workflow syncs the site + status.json + the Playwright
            HTML report to S3 and invalidates the CloudFront distribution,
            under a narrow role scoped to that bucket and distribution only.
            The dashboard reads the public GitHub API for run history.
```

Open question for an ADR in this phase — where per-stage status comes from:

```text
GitHub Actions API, read from the browser
  the repository is public, so no token and no backend of our own. Live by
  construction. Bounded by GitHub's unauthenticated rate limit and by whatever
  shape GitHub's API happens to have.

workflows write status into the S3 bucket
  independent of GitHub, and able to describe things Actions knows nothing
  about — the state of an environment in AWS, for instance. Costs a write step
  in every workflow and can go stale if a run dies before writing.
```

The detail that makes this phase necessary rather than decorative: **GitHub
Actions artifacts require a logged-in GitHub account to download.** Today the
Playwright report is only an artifact, so an external viewer cannot open it.
Publishing it is what turns test results into evidence.

Why not GitHub Pages: it is free and simpler, but hosting the showcase of an AWS
project outside AWS demonstrates none of the skills the project is about.
S3 + CloudFront + OAC + ACM + Route53 costs cents per month and is itself an
exhibit. The private-bucket-with-OAC pattern, rather than a public bucket, is a
deliberate talking point.

Done when: someone with no GitHub account and no AWS access can open one link
and understand the architecture, see the last cycle's test results, and see the
current state of each environment — **with stage and prod fully destroyed**.
That last condition is the real test of this phase.
Cost: cents per month. Verify the real figure later in `docs/cost-control.md`.

## Phase 12 (M4) — Minimum viable documentation

Cut to what the MVP actually needs. The rest moves to Phase 17.

```text
README.md               what it is, how to run it, what it proves
docs/architecture.md    the five Terraform state levels, the request path,
                        why no NAT, why the ALB is destroyed first.
                        Reuses the diagram drawn for the dashboard in Phase 11
                        — draw it once.
docs/demo-script.md     the exact 10-minute live walkthrough
```

Also mandatory here, because they are already stale and actively misleading:

```text
- project-prompt.md §7 (repo structure) and §10 (bootstrap ordering) still
  describe ONE bootstrap level. There are now five state levels.
- skills tf-workflow and teardown do not mention the multi-level bootstrap
  or the targeted apply/destroy passes.
```

Done when: a reader who has never seen the project can run it and explain it
from the repo alone.
Cost: **$0**.

## Phase 13 — MVP verification gate

Not paperwork. A single uninterrupted run from a completely empty account state
through to a completely empty account state, performed as if by a stranger:

```text
1. everything destroyed, dashboard confirms it
2. deploy stage via Actions → tests green
3. promote to prod → approval → prod live on https://app.<domain>
4. dashboard shows prod up, links to the fresh test report
5. destroy both → verification step passes
6. dashboard still up, honestly reporting "destroyed"
```

Anything found here gets fixed here. **The MVP is done when this run is clean.**

---

# Polish track

Ordered by value, not by dependency — these can be reordered freely once the MVP
is verified.

## Phase 14 — Release resilience

```text
automatic rollback to the previous task definition when the prod smoke fails
release versioning/tagging, image immutability by digest
```

Strong DevOps talking point, cheap once promotion exists.

## Phase 15 — Supply-chain and IaC security gates

```text
Trivy       container image scan, fail on HIGH/CRITICAL with an allowlist
Checkov     (or tfsec) Terraform scan
gitleaks    secret scan on every push
Dependabot  pip, npm, and GitHub Actions updates
```

Converts "no static keys" from a claim into a demonstrated practice. All free,
entirely inside `ci.yml`, which stays AWS-free. Cost: **$0**.

## Phase 16 — Full test depth and application observability

```text
the rest of the CRUD surface: PATCH, GET by id, pagination, 404/422/409 matrix
the full Playwright regression suite
structured JSON logs with a request id
a CloudWatch metric filter on 5xx plus one alarm
```

## Phase 17 — Prod data continuity (optional)

Only if the absence of persistent prod data (ADR-0017 D2a) ever becomes a real
objection:

```text
restore prod data from an S3 snapshot at deploy time   — cheap, an evening
Aurora Serverless v2 with scale-to-zero                — data survives idle,
                                                         storage-only cost
```

## Phase 18 — Remaining documentation

```text
docs/cost-control.md              real per-cycle cost, the budget alarm,
                                  idempotency settings, "always destroy after a demo"
docs/interview-talking-points.md  per role: DevOps / Cloud / SDET / Security / FinOps
docs/lightsail-devbox.md          devbox setup, SSH, the browser-SSH gotchas,
                                  and its role in the architecture
```

## Phase 19 — Guarded self-service launch (external access, Wave B)

Per ADR-0017 D4. Last, deliberately: it is the only phase that hands a stranger
the ability to spend money.

```text
trigger     dashboard button → Lambda Function URL → one-time expiring token →
            GitHub App → workflow_dispatch
guardrails  MANDATORY, not optional:
            - single-run concurrency group
            - a per-day run cap
            - a hard TTL auto-destroy after 60-90 minutes regardless of outcome
            - a reaction to the budget alarm
            - an OUT-OF-BAND watchdog: a cron on the Lightsail devbox that
              independently tears down anything running past its TTL. Its value
              is the separate failure domain — if Actions itself is broken or a
              workflow dies before its destroy step, the money still stops.
results     the run's report is published to the dashboard automatically
```

A self-service ephemeral environment with cost controls is essentially a
miniature internal developer platform — a strong exhibit in its own right.

---

## Deliberately out of scope

Not "someday" — considered and excluded, with reasons. Being able to explain why
something was *not* built is itself an interview asset.

```text
EKS / Helm / ArgoCD / Flux
  ECS Fargate already demonstrates container delivery. EKS adds a control-plane
  cost and a large surface for no additional narrative here.

React / Vite frontend
  The frontend exists to be tested, not to be a frontend portfolio piece.

Grafana / Prometheus / Loki on Lightsail
  CloudWatch covers observability at zero extra cost and no extra maintenance.

WAF, and CloudFront in front of the APPLICATION
  Cost and complexity with no story that HTTPS + security groups do not already
  tell. Not a contradiction with Phase 11: CloudFront serves the static
  dashboard, not the ALB.

Hosting the dashboard on the Lightsail devbox
  Zero marginal cost, but it couples the public face of the project to the
  machine used for development, needs ports opened against the current
  SSH-only posture, needs certbot renewals, tells an nginx-on-a-VM story in a
  managed-services project, and makes the devbox impossible to stop or delete.

Private ECS subnets + NAT Gateway
  ~$32/month for the NAT alone. The public-subnet-with-public-IP design is a
  deliberate, defensible trade-off (ADR-0016 records what it costs in teardown
  ordering). VPC endpoints are the cheaper variant if ever revisited.

Blue/green deploys and autoscaling
  Rolling deploys plus automatic rollback (Phase 14) already demonstrate safe
  release. Autoscaling on a demo with no traffic proves nothing.

A second workload member account for prod
  Rejected on schedule cost in ADR-0017 D1. The only item here genuinely worth
  revisiting once the polish track is done.

A scheduled nightly teardown as a general backstop
  Superseded by the per-run TTL and the out-of-band watchdog in Phase 19.
```
