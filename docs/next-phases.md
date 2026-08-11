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
Phase 11.1a          written (2026-07-26) — ADR-0026, ADR-0027, scaffold only
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

## Phase 10 (M2) — Thin application slice  [DONE 2026-07-26]

The code was written and green locally in one session and validated against AWS
in the next. The closing cycle — deploy-stage, promotion behind required
reviewers, read-only smoke against deployed prod, destroy both — ran green
through Actions with no manual AWS operation, and the teardown was confirmed
against the AWS CLI. What each session produced and measured is in
`docs/sessions/2026-07-26-phase-10-thin-application-slice.md` and
`docs/sessions/2026-07-26-phase-10-aws-validation.md`.

The closing session found no structural problem and produced no ADR. It found
three documentation and tooling defects of the project's usual species — a trap
documented in one file and contradicted by eight, a verification that reads as
green when it loses its credentials, and a skill still describing the world
before ADR-0018 — plus one operational hazard: a client-side negative DNS cache
makes prod look dead for a while after it comes up, because the name is dead
most of the time by design.

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

### Backlog — approving a deployment from the dashboard

Asked for on 2026-07-26, while approving `destroy prod #12` in the GitHub UI.
Not scheduled; recorded with its price so the decision is made on the price and
not on how small the button looks.

11.1c ships the honest cheap half: while a run is `waiting`, the panel shows a
**Review deployment on GitHub →** link straight to that run. One click from here,
and GitHub asks who you are.

A button that actually approves is a different thing entirely:

```text
what it is       POST /actions/runs/<id>/pending_deployments, with a token that
                 can write to this repository. The approval is recorded as the
                 AUTHENTICATED USER, so it cannot be done by a shared machine
                 credential without lying about who approved.
why not in the   this page is a static file in a PUBLIC bucket. Any token it
page             carried would be published with it - repository write access for
                 everyone who opens demo.uveapp.net.
what it needs    a browser sign-in (GitHub OAuth/device flow) so the approval
                 belongs to a person, plus a backend to complete the exchange and
                 hold the client secret: API Gateway + Lambda + Secrets Manager,
                 i.e. a SIXTH permanent state level and a public entry point that
                 now has to be defended.
the real cost    not the money. The approval gate is worth showing precisely
                 because GitHub enforces it with its own protection rules. A
                 second road to that gate - even a legitimate one - becomes
                 another thing that has to be PROVEN not to bypass reviewers,
                 every time anything near it changes.
```

If it is ever built, it needs an ADR of its own, and the first thing that ADR has
to answer is what the demo gains that the deep link does not already give.

### 11.1 — Build the dashboard

Split into three steps, so that the one that costs money stands alone and can be
approved on its own:

```text
11.1a  ADR-0026, ADR-0027, infra/public-site scaffold, gitleaks debt   $0
11.1b  local apply, publish workflow, status.json                      cents/month, permanent
11.1c  dashboard content, then a full cycle with the dashboard live    inside the existing cycle
```

The open question below is **answered by ADR-0026**: both sources, split by what
each one can actually observe. The text is kept as it was written, because the
way the question was framed is what made the answer obvious.

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

## Phase 14 — Release resilience  [DONE 2026-07-28]

```text
automatic rollback to the previous task definition when the prod smoke fails
release versioning/tagging, image immutability by digest
```

Strong DevOps talking point, cheap once promotion exists.

Delivered with one correction to its own premise: "the previous task definition"
does not exist in an environment that is destroyed every cycle, so the rollback
target is a digest pointer at a permanent level instead (ADR-0029). Exercised by
promoting a knowingly broken image; see the Phase 14 section of
`docs/phase-gates.md`.

## Phase 15 — Supply-chain and IaC security gates

Split on 2026-07-28, because the two halves are different kinds of work: 15a is
deterministic wiring, 15b is triage. Mixing them hides the wiring inside the
triage.

```text
15a  DONE 2026-07-28
     gitleaks    secret scan on every push, full history, every ref
     Dependabot  five manifests: pip x3, npm, GitHub Actions

15b  DONE 2026-07-28
     Trivy       image scan in its own ci job, gated on findings that HAVE a
                 fix, reporting the ones that do not
     Checkov     46 skip decisions in .checkov.yaml, 4 findings fixed
     pinning     ANSWERED YES (ADR-0030): 32 references pinned by commit SHA,
                 with make action-pins keeping them that way. PR #3 closed as
                 superseded rather than merged.
```

Both halves convert "no static keys" from a claim into a demonstrated practice.
All free, entirely inside `ci.yml`, which stays AWS-free. Cost: **$0**.

15b did produce real findings, and the budget was right: 62 Checkov failures
and 26 HIGH/CRITICAL container vulnerabilities, of which the decisions took the
session and the wiring took an hour. The prediction named the findings almost
exactly — a base image with known CVEs, public subnets, unencrypted ALB logs.

The instruction 11.1a left for this phase — "assert on the AWS rule specifically
rather than on 'something was found'" — was tried in 15a and RETIRED: in
gitleaks 8.30 the AWS rule does not fire on an access key id at all.

## Phase 16 — Full test depth and application observability

Split on 2026-07-29, for the same reason 15 was: the two halves are different
kinds of work. 16a is the application contract and the tests that hold it; 16b
changes HCL.

```text
16a  DONE 2026-07-29 (ADR-0031)
     the rest of the read/update surface: GET by id, PATCH, pagination,
     the 404/422/409 matrix
     the Playwright regression suite over the edit control and the pager
     updated_at, so the database assertion after a UI edit proves an UPDATE

16b  DONE 2026-07-31 (ADR-0032)
     structured JSON logs with a request id
     a CloudWatch metric filter on 5xx plus one alarm
```

16b closed with a full cycle too, and produced the same species of finding as
16a: two of its four patches exist because a command disagreed with a document —
a metric that was billable from the first health check while the ADR said it did
not exist yet, and an alarm whose ALARM state lasted exactly sixty seconds and
notified nobody. Neither was reachable by review. What it deliberately did NOT
buy is an SNS topic at a permanent level, priced in ADR-0032.

16a closed with a full cycle. Three of its four patches exist because something
was run rather than reviewed: a test that skipped itself, a break test that
failed to break because the suite could only see rows it had created itself, and
two tests that passed on localhost and timed out through an ALB.

## Phase 17 — Prod data continuity (optional)

Only if the absence of persistent prod data (ADR-0017 D2a) ever becomes a real
objection:

```text
restore prod data from an S3 snapshot at deploy time   — cheap, an evening
Aurora Serverless v2 with scale-to-zero                — data survives idle,
                                                         storage-only cost
```

## Phase 18 — Remaining documentation  [DONE 2026-08-02]

```text
docs/cost-control.md              real per-cycle cost, the budget alarm,
                                  idempotency settings, "always destroy after a demo"
docs/interview-talking-points.md  per role: DevOps / Cloud / SDET / Security / FinOps
docs/lightsail-devbox.md          devbox setup, SSH, the browser-SSH gotchas,
                                  and its role in the architecture
```

Delivered as written above, no scope change. See `docs/phase-gates.md` Phase 18
and `docs/sessions/2026-08-02-phase-18-documentation.md`. No cycle run, the same
deliberate exception as Phase 12 — nothing here touches HCL, a workflow, or
application code.

## Phase 19 — Guarded self-service launch (external access, Wave B)

Per ADR-0017 D4. Last, deliberately: it is the only phase that hands a stranger
the ability to spend money.

Split into three on arrival, in the 19a/19b/19c shape Phase 11.1 used, because
the parts have different costs and only the last one can be trusted:
19a decides and scaffolds at $0, 19b applies and proves the refusals without a
cycle, 19c is the only part that spends.

**Decided ahead of 19a, in a session that built nothing: ADR-0034** (the
trigger path) and **ADR-0035** (the guardrails). Read those rather than this
summary — this section is the schedule; they are the reasoning. Deciding first
and separately is deliberate here: this is the one phase where the expensive
mistake is a design that cannot refuse, not an implementation that is wrong.

```text
trigger     dashboard button -> Lambda Function URL -> one-time nonce ->
            GitHub App installation token -> workflow_dispatch, stage only
guardrails  MANDATORY, and each one is a REFUSAL with a break test:
            - one run at a time, refused by the Lambda (Actions only queues)
            - a per-day cap that FAILS CLOSED when its store is unreadable
            - a hard TTL auto-destroy, in-band and out-of-band
            - a kill switch flipped by the budget alarm - a slow backstop,
              and honest about being one
            - an out-of-band watchdog, on EventBridge rather than on the
              devbox: see the amendment below
results     the run's report is published to the dashboard automatically,
            by the machinery that already publishes status.json (ADR-0026)
```

**Amendment to this plan, made in 19a and recorded as ADR-0035 §5.** This
section previously specified the watchdog as a cron on the Lightsail devbox. The
requirement — a failure domain separate from GitHub Actions — is right; the
mechanism is not. A cron has no human, and the devbox reaches AWS through IAM
Identity Center with a device code somebody types, so an unattended path from
that machine means a static credential on disk. The project's loudest invariant
is that none exists. Since the domain actually distrusted is Actions rather than
AWS, EventBridge Scheduler plus a Lambda buys the same independence and needs no
credential that outlives a request.

### 19a — scaffold  [$0, nothing applied]  **DONE 2026-08-02**

The decisions were already made (ADR-0034, ADR-0035). What was left was code
that nobody has run, and all of it now exists:

```text
infra/self-service/          the new permanent level, written not applied
.github/workflows/self-service.yml
the Lambda handlers, with the refusal logic in control.py and every refusal
  driven from tests/unit/ - the precedent is Phase 16b: a property no HTTP
  client can see belongs in-process
the dashboard button, behind a flag, pointing at nothing yet
```

Two things the plan did not name and the writing produced anyway:

```text
make self-service-package   the runtime ships no crypto, and an RS256 JWT is
                            how a GitHub App installation token is minted. The
                            target refuses rather than shipping an empty zip.
the Launch tag              scoping the watchdog by deadline ALONE would have
                            let it tear down the owner's own stage cycle, which
                            carries no deadline. Guardrails are on the public
                            path, not on the project - so the watchdog acts only
                            on resources tagged with a launch id, and its IAM
                            policy carries the same condition.
```

Closed when it was written, validated statically (`make tf-validate`,
`make test-unit`, `make iac-scan`, `make docs-check`) and nothing had been
applied.

### 19b — apply the level, and prove every refusal without a cycle

```text
apply infra/self-service under demo-admin
create the GitHub App by hand, install it, paste the key into Secrets Manager
  - out-of-git state, documented beside the NS record and the protection rules
break tests 1, 2 and 4: the lock, the cap (both ways, including the store
  being unreadable), and the kill switch
```

Four of the five refusals can be shown without ever creating an environment,
which is why they come before the cycle rather than during it. Closes when each
has been seen refusing, with the output kept.

### 19c — one live launch, and the TTL proven by killing it

```text
press the button as an anonymous visitor, from a machine that has never held
  a credential for this account
let the cycle run to completion; the dashboard reports it
then a SECOND launch, cancelled mid-deploy, to prove break test 3
then the blunt path of break test 5, against a real environment, with the
  AWS CLI as the witness
```

The blunt path is the one that never runs in a normal cycle, and therefore the
one this project has learned to distrust. Closes when the account is verified
empty from the devbox, with a positive control in the same command, and the
measured cost is recorded.

### 19d — the state a cancelled run leaves, cleaned up by the system

19c did everything above and did not close, because cancelling a run left
something no single component could see: an environment alive, its lock deleted
by a `release-lock` that never asked how destroy went, and a Terraform state
lock nobody would ever release. Recovery took a human with an AWS credential.

```text
the watchdog keeps its OWN record, so it cannot forget a dispatch when the
  lock goes missing - which is the case it exists for (ADR-0036 D1)
release-lock releases only what destroy actually finished (D2)
a state lock left by a finished runner is broken by the system, and refused
  in every ambiguous case (D3)
then the batched "the endpoint says something untrue" fixes: the kill switch's
  message and its exemption for GET, the run_url that is read and never
  written, and the two limits the dashboard hardcodes
```

Closes when a cancelled run is cleaned up with nobody in the loop, and the
account is verified empty afterwards with a positive control in the same
command. That is also the remaining criterion of 19c, which closes with it.

---

### 19e — the break test  **DONE 2026-08-06**

A launch cancelled mid-apply on purpose, through the public endpoint. Confirmed
ADR-0036 D1/D2/D3 on live evidence: the lock was kept, the stale state lock was
broken by the preflight in 6s, and the watchdog wrote its own record and removed
the billable resources with no human. Disproved the wider claim: the remainder
took four manual AWS calls. Root cause and decisions in ADR-0037.

### 19f — teardown gates that see the remainder  **DONE 2026-08-07**

D2, D3 and D4 shipped and all three confirmed by a cancelled launch. The claim
they were written for was disproved in the same run: the remainder still took
three manual AWS calls. What changed is that the teardown now reports it.

### 19g — teardown that finishes on its own  **DONE 2026-08-08**

The gap 19f made exact. A cancelled apply creates resources that never enter
state, so Terraform can neither delete them nor delete what depends on them —
the RDS instance is unmanaged, the subnet group that holds it is managed, and
the destroy dies on the pair. The watchdog's blunt path removes the billable
orphans, which is exactly what unblocks Terraform, but it does so only AFTER the
dispatched destroy has already failed, and nothing dispatches another.

Three candidate shapes, to be decided rather than assumed:

```text
re-dispatch    the watchdog dispatches destroy once more after the blunt path.
               Smallest change; does nothing for orphans the blunt path does not
               touch, and the security groups and cluster it left are exactly
               those
widen          the blunt path deletes the non-billable kinds too. Turns a
               spend control into a general deleter, and its IAM condition is
               currently the thing that keeps it away from the owner's
               environment
import         orphans are imported into state before the destroy, so Terraform
               owns them and can remove them in dependency order. The only
               option that ends with state and AWS agreeing, and the only one
               that needs a mapping from ARN to resource address
```

**Decided: import** (ADR-0038). Read against the code, the other two cannot meet
the criterion alone. `re-dispatch` re-runs a destroy that still does not manage
the cluster and the security groups, because those are free and the blunt path
only deletes what bills. `widen` puts Terraform's dependency graph inside a
Lambda and spends the IAM narrowness that makes the blunt path safe. Adoption
works one layer earlier: the teardown fails because it does not own three
resources, and a teardown that can adopt them succeeds on the FIRST destroy.

The ordering then dissolves instead of being patched. The watchdog already
dispatches destroy once; that dispatch has always been the retry, and it was
ineffective only because the destroy it dispatched could not adopt.

Two cancelled launches on 2026-08-07 proved every component and did not close
the phase. Adoption found and imported the RDS instance whose absence from state
has failed every teardown since 2026-08-05, and two defects surfaced behind it —
four `case` arms in the 19f sweep that had never been reached, and a null
endpoint address on an instance adopted while still `creating`. Both fixed, both
with the account verified empty afterwards.

What remained was ONE uninterrupted run: cancel a launch and watch the IN-BAND
destroy adopt and finish within minutes, with no watchdog, no blunt path and
nobody dispatching anything. On 2026-08-07 both destroys that finished were
dispatched by hand to skip a 90-minute wait, so that sentence was a prediction
rather than evidence.

**It happened on 2026-08-08, first launch of the day, in one run.** Cancelled at
00:44:15 with the fullest orphan set any cancel here has produced — ALB active,
cluster up, three security groups, RDS `creating`. The destroy job started
itself nine seconds later, the sweep returned `orphans`, adoption took 4 of 4
and named the fifth UNADOPTABLE, and the destroy was green at 00:49:09 — 4m45s,
zero manual AWS calls. `release-lock` then released, which by ADR-0036 D2 it
does only on `destroy=success`, so a second job independently agrees. The
account was verified empty afterwards from outside the run, with a positive
control in the same command.

**Phase 19 is complete, and the button stays live.** The endpoint had been
described as parked in two documents while the control store held no kill-switch
item at all; the state those documents should have described is the one Phase 19
was built to make safe, and it is now the recorded one.

## Phase 20 — The cycle, visible without a log

Decided 2026-08-08 in **ADR-0039**. The dashboard reports STATE — which
environments exist, which run is where. It does not show what the project DOES,
and the one section that tries is hand-written prose. The same session found that
section telling every visitor there were five permanent state levels while
standing on the sixth, so the phase has two jobs: build the picture, and build it
out of something that cannot drift.

The criterion, stated so it cannot spread:

```text
A visitor who has never seen this project, and has no access to GitHub Actions,
can see on demo.uveapp.net: which AWS services a cycle creates and destroys and
in what order, how long each took and what it cost, and which tests ran and what
they assert. Without opening a single log.
```

The map is on the page ALWAYS (ADR-0039 D4). Idle it shows the last measured
cycle, dated. Running, the current phase pulses. It is not a panel that appears
when something happens.

### 20a — the generated map, as a PILOT  [$0, nothing applied]

Build the smallest thing that shows the shape, look at it in a browser, then
correct. 20a is not the finished map and is not meant to be: the layout is the
only part of this phase that cannot be derived from the repository, so it has to
be seen before it can be decided. Everything below is the target; the pilot is
allowed to reach less of it, provided it reaches it honestly.

```text
generator     site/data/topology.json, built from infra/ AND tests/: the state
              levels, the resources each module declares, the suites that run
              after stage comes up, and the display node each one is assigned
              to. Suite nodes are part of the chain from the start, not a
              later addition (ADR-0039 D2b)
counts        the same file carries the COUNTS - levels, permanent levels,
              ADRs, suites - and prose renders them instead of spelling them
              out. Six of the stale places found on 2026-08-08 were numbers,
              not phrases, and a number goes stale without a word changing
              around it
layout        legibility floor first, serpentine packing second, one screen
              third and it is the one that gives way (ADR-0039 D5). NEVER
              shrink to fit. Resources are GROUPED into services, and the
              floor plus the coverage gate are what hold the size down
autoscroll    while a cycle runs the view may follow the active node, at phase
              granularity. Any manual scroll, drag or zoom stops it; after a
              quiet interval it returns to the active phase. A timeout is the
              whole mechanism - no resume control, no easing
mobile        the map REFLOWS to a single vertical column and scrolls - same
              nodes, same data, a second layout pass over the same JSON. Not
              the desktop layout squeezed, and not text instead of a map. The
              serpentine is desktop-only; one column has nothing to fold
gate          make site-data-check, wired into ci.yml. It checks COVERAGE, not
              depiction: every resource in infra/ belongs to exactly one display
              group, including the group meaning "deliberately not shown". An
              unassigned resource is red; a hidden one is green and recorded
page          the hand-written "What happens, in the order it happens" section
              is replaced by the map. The prose rendering stays, generated from
              the same JSON and never maintained separately (ADR-0039 D1): it
              is the route to exact per-resource detail from either layout,
              not the small-screen substitute for the map
icons         establish AWS's terms for the Architecture Icons set and record
              the answer in ADR-0039, or use project glyphs. Do not guess
break test    add a resource to a module without assigning it -> gate red.
              Delete the generated file -> gate red. Keep both outputs
```

**A node is a service, not a resource.** RDS is three Terraform resources, the
ALB is three, ECS is three; the map draws one node each, active while any member
is in flight, with the group's duration measured from its first `apply_start` to
its last `apply_complete`. That is an aggregate and it is exact — the per-resource
steps stay one click away in the text chronometry rather than being lost. Nothing
finer is available in any case: Terraform reports resources, never a service's
own `creating → available` progression.

What is genuinely approximate is only the visual scale, and it says so where it
renders. What is never allowed is a node containing a service the repository does
not have, or omitting one without the coverage gate having been told.

Closes the structural half of the 2026-08-08 finding: the architecture section
can no longer disagree with `infra/`, because it is built from it.

#### What the layout pilot settled (2026-08-08, in a chat sandbox)

The layout was built and LOOKED AT before the generator existed, which is the
whole point of 20a being a pilot: the generator is derivable from the repository
and the layout is not. `site/map-pilot.html`, rendered against a hand-built
`site/data/topology.json`, at 1440 / 1180 / 834 / 390.

The first attempt folded the chain node by node. It read well, and it said
something untrue:

```text
finding   within one apply Terraform creates a DAG, not a queue. An arrow from
          VPC to Secrets Manager to RDS is a claim about order that nothing in
          the repository makes - ADR-0026's rule, applied to a picture
fix       the unit that carries SEQUENCE is the PHASE; the unit inside it is a
          SET. Phases fold serpentine; nodes inside a phase get no arrows
side      the phases became legible AS phases, which the node-level fold had
          destroyed: one row read across three of them
```

Settled, and not to be reopened without new evidence:

```text
packing    serpentine at PHASE level; odd rows read right to left
floor      node width and every type size have a minimum. At 390 the fold
           degenerates to one column, so the mobile reflow came free - the same
           code, a second pass over one file, exactly as ADR-0039 D5 predicted
priority   desktop and laptop are the intended view, and the page SAYS so. The
           phone works and flattens the shape; that is stated rather than
           engineered around. Revisit after a real cycle, not before
icons      official AWS Architecture Icons, unmodified, inlined as ONE sprite
           (a few tens of KB, a quarter of that gzipped) so the page stays a
           single file with no
           request-time dependency. Anything that is not an AWS service keeps a
           project glyph. Terms and position: assets/aws-icons/NOTICE.md
absent     a node with no observation is the same icon in greyscale, never a
           second set of marks
```

Open on purpose, until a real cycle says something:

```text
autoscroll  needs a live run to judge. Nothing in a fixture can exercise it
phone       phases 2 and 6 unroll into long columns. Collapsing them by default
            is the obvious move, and it is not obviously the right one
labels      a node reading "Route 53 + ACM" carries one mark for two services
numbers     the fixture's measured values are placeholders and say so. 20b
            replaces them with Terraform's own event stream
```

#### What the generator settled (2026-08-08, same day)

Built, gated and break-tested. Two things it changed in the plan above:

```text
unit       every count says resource BLOCKS, not resources. Nine blocks carry
           count or for_each and stand for a number that depends on variables;
           each is acknowledged by name in the editorial file, and a tenth
           appearing without an entry is red. The fixture's "116 resources" was
           never the number of objects AWS creates
numbers    the generator writes NO observation at all - no duration, cost,
           identifier or result. Those are things a cycle says. The map renders
           unobserved until 20b and 20c, which is a visible regression in the
           exhibit and the honest one: the fixture's placeholders read as
           measurements
```

The gate got five break tests rather than the two planned, plus one path that is
green and recorded: the group meaning deliberately not shown, holding
`aws_default_security_group`, which creates nothing.

Added on review, in the same session: a band ABOVE the cycle for the two things
that are not in `infra/` and therefore could not appear — the Lightsail devbox
and GitHub's repository and Actions — and the front page's prose moved under a
cut and GENERATED from `topology.json`, with `members` naming every resource
behind every node.

Open, and carried forward:

```text
github      GitHub's mark is NOT an open question the way AWS's was: its brand
            page names this case and permits it (assets/github-logo/NOTICE.md).
            The asset has to be DOWNLOADED, not drawn - a redrawn Octocat is a
            modified one - and the page needs a third icon case, being neither
            an AWS service nor a project glyph. Glyph `CI` until then
.node .head up to 22px wider than its own node, at every width - pre-dates the
            generator and was invisible to the pilot's document-level measure.
            A layout question, so it waits for the map to be on a screen again
```

#### What the page settled (2026-08-08, closing 20a)

The map and its cut are in `site/index.html`, and the seven hand-written chips
are gone. Two things the plan did not have:

```text
build      the page needs the sprite inline, so site/index.html is a BUILD
           OUTPUT now: assets/index.template.html is the source, `make
           site-page` builds it, `make site-page-check` requires the committed
           page to be byte-identical to a fresh build, and ci.yml runs it. A
           committed output invites being edited in place, and that edit lives
           only until the next build reverts it - quietly
pilot      retired, page and template and target. publish-site syncs with
           --delete so the published copy went with the commit. Keeping it
           would have left two renderings of one file maintained separately,
           which is the shape this phase exists to remove
```

Two layout defects, neither visible to the pilot's `scrollWidth ==
clientWidth`, because that measured the DOCUMENT: the serpentine packer charged
one gap per join where a row renders `phase | gap | arrow | gap | phase` (7px
over at 1180), and `.node .head` was up to 22px wider than its node. Both were
found by measuring a box against ITS OWN container rather than against the page.

Open, and carried past 20a:

```text
architecture.md   still draws the same thing by hand, in Mermaid. ADR-0039 D1
                  ended the prose rendering on the public page; the diagram in
                  the repository is a third rendering and nothing generates it.
                  Not in 20a's criteria, so not done here - but it is the same
                  defect waiting, and a reader of the repo meets it first
autoscroll        still needs a live run to judge. 20b
phone             phases 2 and 6 unroll into long columns; collapsing them by
                  default is still the obvious move and still not obviously right
```

### 20b — the timeline  [split: 20b.1 done at $0, 20b.2 needs one cycle]

Everything decidable without a cycle went into **20b.1**, on the shape 19 used.
Done, and none of it has met AWS:

```text
-json         DONE. Eight terraform invocations across the four workflows, each
              captured by scripts/tf-stream.sh
fold          DONE. scripts/fold-timeline.py, into
              timeline/<env>/<run id>-<job>.json plus latest. The key carries
              the JOB because self-service launches and destroys in ONE run
publish       DONE. scripts/publish-status.sh, under the narrow publish role,
              exactly as it already publishes the Playwright report. No IAM
              change: that role already covers the bucket
readable log  DONE. Per-resource table, every diagnostic in full, errors
              printed outside the collapsed group
cache         DONE. max-age=60 on the timeline objects, no invalidation per
              write
break test    DONE, on fixtures. Seven ways red, both controls green, and one
              of the fixtures is a terraform process that was really killed
```

**20b.2 — the live half** [one cycle, about $0.03]

Writing the CONSUMER of 20b.1's timeline moved most of this off the billable
half, and produced two decisions the plan did not have (**ADR-0040**). Written
and gated at $0:

```text
join          DONE. scripts/node-states.py turns a timeline into node states, on
              the runner. Not on the page: the rule would then be JavaScript
              there and Python in its own gate - one definition, two hosts
at rest       DONE, in shape. latest.json is NOT the at-rest source; a cancelled
              run overwrites it and would erase a good measurement. The numbers
              come from nodes-apply.json / nodes-destroy.json, published only
              when a cycle completes, and the page SAYS when the last run did
              not finish
page          DONE. Nodes carry duration and the provider's own identifier;
              phases pulse from the Actions API, read once by the dashboard
              script and handed to the map rather than fetched twice
coverage      DONE. make node-states-check: every resource a cycle touches is on
              a node, recorded as deliberately not drawn, or named UNKNOWN
modules       ANSWERED OFFLINE. tests/fixtures/timeline/cases/apply-module is a
              real terraform run with resources inside modules - three address
              shapes, including count on the module itself. The expectation is
              written from the documentation, and generate.sh on the devbox
              turns it into a measurement or a red gate before any cycle runs
```

What still needs the cycle, and nothing else does:

```text
publish       a real timeline object in the bucket, from an apply and from a
              destroy, with the node states beside them
page          the same map drawn from figures AWS produced rather than from
              fixtures - including whether an identifier is legible at the size
              its node gives it
break test    the live one: a cancelled RUN must publish INCOMPLETE, and the
              page must say so rather than drawing it. The fixtures prove the
              fold, not the workflow's `if: always()`
open          per-resource live pulsing, if phase-level proves too coarse. Two
              priced options in ADR-0039 D4; neither is taken by default
```

### 20c — the suite nodes carry results  [$0 to write, one cycle to prove]

Not a panel beside the map. The suite nodes are already ON the map from 20a
(ADR-0039 D2b) — this is what fills them.

**Amended by ADR-0042 while the first half was being built.** Three things in
the sketch below did not survive contact with the repository. `tests/db` has no
collector to be generated from — it is a standalone script, so it was GIVEN
`--list` rather than described from outside. The inventory gate cannot sit beside
the map's own gate, because collecting needs the suites' dependencies and the
job that holds `site-data-check` installs none of them. And the db assertion
exists in two copies, of which the map observes the one baked into the image, not
the one `make test-db` runs.

```text
inventory     generated from the suites themselves - pytest --collect-only,
              playwright --list - not a list written beside them
results       per node, from the report already published to the bucket:
              passed/failed, duration, and what the suite asserts
identity      a node is a suite x ENVIRONMENT. Smoke runs twice a cycle, on
              stage before the approval and on prod after the promotion, and
              one node cannot hold two results
observer      a suite is observed by its report and, live, by the Actions step -
              never by Terraform's stream, which knows nothing about it
```

What a test checks is read from the test. A description maintained next to it is
the sixth stale place waiting to happen.

The thing worth SEEING here rather than reading: ADR-0025's directory binding,
drawn. Regression and the API contract cannot reach prod, and the map shows smoke
standing there alone.

### 20d — cost, computed from lifetimes  [DONE 2026-08-08, ADR-0045]

```text
rates         a dated table CAPTURED from the AWS Price List Query API into
              site/data/rates.json, each figure carrying its SKU and filters
computed      per-resource LIFETIMES x rates, as a BAND, per cycle - and by
              overlap where it accrued, which is mostly nowhere near a phase
reconcile     RETIRED, not deferred (ADR-0045 D6)
```

**Two of those three lines were wrong when this section was written, and the data
said so before any code was.** "Per-resource seconds from 20b" meant terraform's
`elapsed_seconds`, which is how long it took to BUILD a resource, not how long
the resource existed: 173 seconds against 1582 for the load balancer of
2026-08-08. And "per phase" is not a property a lifetime has — an ALB's half-hour
cannot belong to the two minutes that created it. Overlap attribution is what is
well defined, and its first finding is that five sixths of a cycle's money
accrues while no phase is running at all.

The reconciliation is retired rather than left pending. An estimate was what was
wanted; Cost Explorer costs another credential in the demo account and answers a
day late; AWS Budgets already watches the actual spend from the other side. A
promise a project has decided not to keep is worse than one it never made.

What this gives the document: the cycle of 2026-08-08 cost **$0.0183 .. $0.0238**,
and the figure is now a command rather than a paragraph.

### The teardown finding  [found 2026-08-08, CLOSED the same day]

Closed by **ADR-0041** in an Ops session, not by a phase: see
`docs/sessions/2026-08-08-ops-the-gate-that-sees-a-free-leftover.md`. The two IAM
roles are gone, the sweep has a second discovery channel that reads the
configuration for kinds the tagging API does not index, and adoption imports what
hangs off a role as well as the role.

The framing this document proposed did NOT survive contact, which is the part
worth keeping here. "Which free resources may be left behind at all" needs an
exception list — deregistered task-definition revisions are free and are left for
ever, deliberately. The class is a resource whose DETERMINISTIC NAME the next
apply will need, and `EntityAlreadyExists` is its symptom.

### A `session-close` check for chat session links  [$0, deferred deliberately]

Six commits carry a `Claude-Session: https://claude.ai/code/…` trailer and the
repository is public. `.claude/settings.json` now sets
`attribution.sessionUrl: false`, which is the mechanism; what is missing is the
gate that would have caught it.

```text
where     `make session-close`, which already refuses on an unpushed HEAD - it
          can see the commits that are about to be shared and nothing else can
evidence  it has to redden on a planted trailer, like every gate here
first     the setting itself is UNPROVEN: the key is undocumented, and this
          session's commits arrived by `git am`, where the trailer never appears.
          The first commit from a Claude Code session on the devbox settles it,
          and there is no point gating something whose fix has not been seen to
          work
```

Deferred on the project's own rule rather than on effort: a new gate needs its
own break test, and something a command cannot check is a reason to add a check
in a LATER session, not to extend the one that found it.

### The `ExpiresAt` predicate as a second gate  [$0, from ADR-0041 D6]

Both orphan roles carried `ExpiresAt=2026-08-05T07:10:39Z` and stood for three
days. The TTL is written onto the resource and nothing reads it after the fact.

```text
predicate   nothing whose own tag says it has expired may still exist. It does
            not care whether the resource is billable or what kind it is, which
            is what makes it stronger than either gate that exists
already     `deadline_passed` in infra/self-service/src/sweep.py implements
            exactly this, applied to a three-kind observation (ECS service, ALB,
            RDS). The predicate is in the repository; its reach is not
caveat      an owner-run cycle leaves ExpiresAt EMPTY by design (ADR-0035), so
            this covers self-service launches only. That is a real limit, not a
            reason to skip it - every orphan so far came from a launch
where NOT   the watchdog. Its job is to stop the meter inside a TTL and a free
            leftover does not tick (ADR-0041 D6)
```

### 20f — the cost fold runs in the cycle  [$0 to write, no cycle ordered]

20d built the computation and left it unwired, and ADR-0045 said so in its own
consequences: *the fold is not wired into any workflow yet — it runs by hand
against two published timelines*. So a cycle still cannot say what it cost
without somebody running a command afterwards, which is the shape this project
spends its sessions removing.

The teardown is where it belongs, because a lifetime is only closed once the
resource is gone. `destroy.yml` already folds a timeline, joins it onto the map's
nodes, and publishes under a role that is NOT the deploy role — so nothing here
spends ADR-0026's separation. `scripts/fold-cost.py` stands beside
`scripts/node-states.py`, on the same `if: always()`.

**The work is the pairing rule, not the wiring.** The fold takes two timelines
and today believes whatever it is handed. Nothing checks that the destroy tears
down what the apply built, and a mismatched pair does not fail: `span()` clamps a
negative lifetime to zero, so the answer comes back small, plausible and wrong.
That is the failure mode 20d's own break log had to re-aim a test at once
already — a defect that crashes is cheap, and one that answers is not.

```text
the anchor    timeline/<env>/latest.json is overwritten by ANY run, including
              this teardown, so it cannot be the anchor - a second destroy would
              pair itself with the first. What is wanted is the environment's
              last COMPLETE apply, published on the rule nodes-apply.json
              already follows: one more object beside it, not a new mechanism
the refusals  same environment; the apply complete rather than incomplete; the
              teardown starting no earlier than the apply finished; and the two
              resource sets intersecting at all. The last is deliberately WEAK -
              ADR-0038 adopts orphans before a teardown, so some deleted
              resource the apply never created is legitimate, and a refusal on
              any orphan at all would fire on a working cycle
```

Note the fourth. `orphan_deletes` is already computed and already in the output;
nothing refuses on it. The detector exists — that is the whole distance between
20d and this phase.

The break test is not optional here and ADR-0045 named it in advance: a stage
apply against a prod teardown, a teardown older than its apply, and a pair with
nothing in common — each with a green control either side.

The page gets ONE line — *last cycle: $low .. $high, computed estimate, dated* —
and no more. WHERE that number belongs is 20e's question; that it is reachable at
all is this one's.

### 20e — the dashboard is composed, not scrolled  [discovery DONE 2026-08-09]

**ADR-0047.** The discovery step ran and the requirement it found is not the one
this section carried. "Wayfinding" was close and wrong in the way that costs a
phase: a section index would have made a long strip traversable, which is not
the same as not being a long strip. The requirement, in the words it was given
in on 2026-08-09:

```text
it should look like a DASHBOARD, not a long list of resources
the main thing is visual: where things are, how they connect, WHICH TOOLS are
  used, in what order
composed in blocks
all the extra detail below the first screen, under cuts
```

The desktop monitor is the primary target, stated in the same breath. The phone
is last in the queue.

What discovery measured, at four viewports, with three remote sources
unreachable — so the figures understate the live page:

```text
1920x1080  3866px 3.6 screens    1440x900  3866px  4.3 screens
2560x1440  3866px 2.7 screens    390x844   8835px 10.5 screens

in <main>: 0 in-page anchors, 0 <nav>, 0 sticky or fixed elements
the per-cycle map is 46% of the page on a laptop, 53% on a phone
the repository link is in the footer, at 100% of scroll depth
```

The three findings recorded on 2026-08-08 all held. The prose under a node is
ADR-0043 D4's disclosure and is NOT hidden (ADR-0047 D3); the sequence stays
exact, so the packing may not reorder phases (ADR-0039 D5); and "compact" cannot
mean fewer bytes, since the body markup is 3.0% of the page.

Two findings the discovery added, both measured:

```text
five of the map's six states are carried by a 1px border and nothing else, and
three of them are under WCAG 1.4.11's 3:1 floor in the light theme. The pulse
fades a 1px ring to opacity 0, so it is legible for a fraction of each beat.
This is not a regression - it is a channel nobody had measured.

the tools are missing, not just their icons. Terraform, Docker, Playwright,
pytest and Alembic appear NOWHERE on the map; TEST does not distinguish
Playwright from pytest.
```

The sketch is `docs/sessions/2026-08-09-phase-20e-sketch.html`, built from the
real topology and suite data with placeholder run figures, and it says so on its
own face. It measures 1.1 screens at 1920x1080 and 1.0 at 2560x1440.

**All six of what was open is closed except the phone** — three by ADR-0048
(the Launch button is the environments panel's footer, the legend is a cut in
the map's header, a node's figures live on one state line), one by the gate
`make contrast-check`, and one by `layout.columns` coming out of the generator.

```text
- the phone, DEFERRED FAR on 2026-08-09 by the person who asked for the page -
  out of the near plan, not merely last in it. The desktop is finished first,
  then the project goes to live cycles.
```

Implemented on 2026-08-09 in two commits, with ADR-0049 recording the six things
building it settled that the sketch could not. 4781px → 1935px at 1920x1080,
measured with the same fixtures either side.

**The phone now has a baseline that can be re-measured, and the figures this
section used to carry were not constants.** `make measure-page` is committed
(`scripts/measure-page.mjs`, not a gate), the three remote sources are frozen in
`tests/fixtures/page-measure/`, and what it found is in
`docs/sessions/2026-08-09-phase-20e-the-figures-get-an-instrument.md`. The
numbers live there and in `docs/phase-gates.md` rather than here, because a
figure written into the plan is a figure nobody re-measures:

```text
- the phone is 5.6-5.7 screens with the cuts CLOSED and 19.6-20.2 with them
  open, which had never been measured at all
- exactly one box overflows its parent at any viewport, the history table, and
  its width is driven by DATA rather than by layout: 84.6px over with no
  self-service launch in the history, 169.1px with one. "52px" was that same
  measure taken on a quiet week.
- and one that is not the phone: the text glyphs are wider than their badge on
  every viewport, including the primary target
```

## Phase 21 — Processes and state are two contours  [DONE 2026-08-10, $0]

**ADR-0054** and **ADR-0055**. A decisions session; no code, no cycle, nothing
applied.

The map draws a linear chain of phases and nests every AWS resource inside the
phase that creates it, while the panel above the map reports the same
environments as observed state. Two accounts of one thing, and where they
disagree the page had an arbiter written into a fixture name rather than into a
decision. ADR-0054 separates three contours — ESTATE (nouns, present tense,
answered by observation in AWS), CYCLE (verbs, past or in flight, answered by
the run layer) and ASSERTIONS (the suites, answered by the repository) — and
makes the binding between a step and a resource a reference instead of
containment.

ADR-0055 retires the lettered sub-phase. From here phases are plain integers and
each carries the sentence that closes it.

**Closed by:** both ADRs accepted, the cursor and the plan carrying Phase 22 and
Phase 23 with their closing conditions. Met.

## Phase 22 — The model: three contours in the data  [$0, no page work]

The generator and the editorial file, with the page left alone as far as it can
be. ADR-0054 D8.

```text
assets/topology-groups.json   phases stop holding nodes and start holding
                              references; the estate becomes its own section
scripts/generate-topology.py  schema 2 -> 3; the assembly rewritten; the two
                              phase-shaped coverage refusals re-pointed from
                              group->phase-level to group->estate node.
                              A NEW refusal: a suite no node draws is a red
                              build - the clause ADR-0039 D2b claimed and never
                              enforced, which is why tests/unit is invisible
scripts/node-states.py        four indexers and the fixture stub
scripts/check-results.py      one comprehension and one frozen stub
scripts/check-live-state.mjs  runLayerStates and its cases; the via:"own" /
                              via:"phase" expectations are hand-written and are
                              re-derived by hand, not regenerated
```

Plus 20m's first finding, which belongs to no restructuring and is cheap: the
run history badge scores an in-flight run as a success because its numerator is
completed runs and its denominator is all of them. Fixed here, with a case.

**Closes when:** `make site-data-check` is green on a schema-3
`site/data/topology.json` in which no phase contains a resource node, every
reference resolves, all five suites are drawn, and the new
suite-drawn-by-nobody refusal has been broken on purpose once with its output
kept. The badge fix has a case that fails without it.

**Does not close when** the page renders. The page is Phase 24, and a session
that starts fixing the layout here is how Phase 20 happened.

## Phase 23 — One list of gates, two readers  [DONE 2026-08-11, $0]

The item Phase 22 handed forward, taken first because it is the one that keeps
reddening `main` while a session reports itself closed.

`scripts/session-close.sh` ran three cheap gates and `.github/workflows/ci.yml`
ran twelve, so `session-close: clean` and a red build were compatible states.
The list moved to `assets/gates.json`; both readers call `make gates`;
`make gates-check` discovers what belongs in the list out of the Makefile and
out of `ci.yml`, so the one thing a single list can do that two cannot — shrink
in silence — is refused rather than trusted. **ADR-0057**.

**Closed by:** the twelve cheap gates running from one list in both readers, the
refusals broken on purpose six ways with a control green either side, and the
20i/21 defect reproduced — an ADR added without regenerating — red in both
readers from the same list. Met. Break-test output in
`docs/sessions/2026-08-11-phase-23-one-list-break-test.log`.

## Phase 24 — The composition, redrawn for three contours

The layout, on the model Phase 22 put in the data. **ADR-0054 D1**'s last piece
with no pixels behind it.

```text
- the composition redrawn for three contours; ADR-0047 D1 and ADR-0052 D2/D3 go
  with it
- re-measured, not translated. Every figure in ADR-0050 and ADR-0052 is a
  measurement of the old object and is retired by ADR-0054
- the assertions contour DRAWN. Phase 22 closed on "all five suites drawn",
  read as present in the topology: `assertions.suites` holds all five and
  `tests/unit` carries its `not_in_cycle` reason, and nothing on the page
  renders any of it. Rendering it is a composition decision, which is why it
  waited for this phase rather than being smuggled into that one
- assets/contrast-contract.json: the probe chain is data, and it is edited
  rather than the script. A seventh node state makes the gate refuse, out loud,
  by design
```

**Closes when:** the page draws three contours; the assertions contour renders
all five suites with `tests/unit` visibly outside the cycle in its own words;
`contrast-check` reads its probe chain from `assets/contrast-contract.json` and
refuses by name on a state the chain does not cover; every figure quoted from
ADR-0050 and ADR-0052 has been re-measured on the new page with
`make measure-page` and written down; and `make gates`, `make page-tense-check`,
`make live-state-check`, `make site-page-check`, `make contrast-check` and
`make page-freshness-check` are green on it.

**Does not close when** it looks right. Every figure in this repository's layout
history came out of a harness thrown away with the session that wrote it, and
20a's own gate found a phase row 7px wider than its container while four
document-level measurements read green.

## Phase 25 — The gate for a cycle in flight

The thing the cursor has owed since 20m.

```text
- a fixture holding a cycle IN MID-FLIGHT with an otherwise-green history -
  which this repository does not have, and the one in-flight fixture that
  exists carries failures, so it never shows the green-while-unknown shape
- the gate that reads it, and its break test
```

Expect the gate to be the hard part. That was the cursor's own prediction after
20m and nothing since has argued with it.

**Closes when:** the new gate is green on the page, red on each of 20m's three
findings re-introduced one at a time, with a control green either side, and the
exit codes recorded to a file with the tree committed first. It is $0 until the
in-flight fixture needs a real cycle behind it, and that is a separate, billable
decision.

## Still open, and unchanged by any of the above

```text
the convergence delay      20m watched a run go green between two observations,
                           so the max-age=60 ceiling is bounded above by about
                           two minutes and has never been measured. Wants one
                           sample every few seconds across the moment a run
                           goes green - not a cycle of its own.
the map's dating sentence  cannot be settled until a cycle runs on a different
                           DAY from the one before it. As of 2026-08-10 the
                           newest cycle is 20m's, on 2026-08-09, so the next
                           cycle finally qualifies.
`not reached yet`          never appeared in 20m: it needs a node with no
                           record at all, and every node carried one from the
                           previous cycle.
```

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
