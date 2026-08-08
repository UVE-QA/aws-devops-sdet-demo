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

### 20b — the timeline  [needs one cycle, about $0.03]

```text
-json         on apply and destroy in deploy-stage, promote-prod, destroy and
              self-service
fold          scripts/ turns the event stream into
              timeline/<env>/<run id>.json plus latest
publish       scripts/publish-status.sh, under the narrow publish role, exactly
              as it already publishes the Playwright report
readable log  a step that folds the JSON stream back into a legible apply
              summary. NOT optional - -json replaces the human-readable log in
              the Actions UI, and losing that to gain a picture is a bad trade
cache         short Cache-Control on the timeline object; no CloudFront
              invalidation per write
page          nodes light from the timeline; identifiers appear as the provider
              assigned them (ADR-0039 D2); the phase pulses live from the
              Actions API
break test    a run that dies mid-apply must publish a timeline marked
              INCOMPLETE, never a plausible complete one
open          per-resource live pulsing, if phase-level proves too coarse. Two
              priced options in ADR-0039 D4; neither is taken by default
```

### 20c — the suite nodes carry results  [$0 to write, one cycle to prove]

Not a panel beside the map. The suite nodes are already ON the map from 20a
(ADR-0039 D2b) — this is what fills them.

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

### 20d — cost, computed and reconciled  [depends on 20b]

```text
rates         a dated rate table in the repository, us-west-2
computed      per-resource seconds from 20b x rates, per phase and per cycle,
              labelled COMPUTED wherever it renders (ADR-0039 D3)
reconcile     once, against a real bill for one cycle, with the delta recorded
```

The reconciliation is the point, not the formality: "we computed $0.03 and the
bill said $0.04, and here is the difference" is a stronger FinOps answer than any
single figure. It also gives this document the per-launch numbers 19c never
recorded.

Order: 20a, 20b, 20c, 20d. 20d cannot start before 20b. Whole phase under $0.20
of real money.

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
