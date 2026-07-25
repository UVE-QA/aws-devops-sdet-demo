# ADR-0017 — Prod environment model, public surface, and external access

- Status: Accepted
- Date: 2026-07-25
- Supersedes: nothing
- Related: ADR-0015 (OIDC in a separate bootstrap state), ADR-0016 (destroy the
  ALB before the network)

## Context

Phase 8's lifecycle half closed on 2026-07-25: `deploy → demo → destroy` runs
end-to-end through GitHub Actions with no manual AWS operations, for **stage
only**. `prod` has always been a placeholder — the choice exists in
`destroy.yml`, but there is no prod role, no `infra/envs/prod`, and no promotion
path.

Four questions had to be answered before any further planning was meaningful,
because each one changes the shape of the remaining work:

1. Where does prod live relative to AWS accounts?
2. Is prod always on, or brought up on demand?
3. Is there a public HTTPS URL?
4. Can a third party (a recruiter, an interviewer) run the cycle themselves?

The underlying tension is that this is a **portfolio project with a $20/month
budget alarm**, while a genuinely always-on prod (ALB + Fargate + RDS) costs
roughly $40–60/month in us-west-2. Exact figures belong in
`docs/cost-control.md`; the order of magnitude is enough to force the decision.

A second, softer tension: every additional layer of realism (separate account,
self-service launch, private subnets) pushes the finish line further out. The
project has already run for months. Shipping a complete, explainable v1 beats
an unfinished v2.

## Decision

### D1 — prod lives in the SAME AWS account as stage, separated by environment

`infra/envs/prod` reuses the existing modules with a `prod` name prefix and its
own state key `prod/terraform.tfstate`. No second member account, no second
permission set, no second SSO onboarding.

A separate prod member account is the stronger AWS Organizations story, but it
doubles the bootstrap work (second `bootstrap-oidc` apply, second state,
Identity Center changes) for an argument the project can already make verbally
from its existing account-isolation design.

Environment separation is still enforced where it is cheap to do so:

```text
- separate Terraform state key            (prod/terraform.tfstate)
- separate name prefix on every resource  (<project>-prod-*)
- separate deploy role                    (<project>-prod-github-deploy)
- separate GitHub Environment             (prod, with required reviewers)
- separate VPC                            (no shared network with stage)
```

The separate **prod deploy role** is deliberate: reusing the stage role would
mean one credential can reach both environments, which contradicts the security
story the project tells. Both roles are created at the `infra/bootstrap-oidc`
level, which Actions never destroys (ADR-0015).

### D2 — hybrid availability: static surface always on, AWS stack on demand

```text
always on   →  the public dashboard — S3 (private) + CloudFront with Origin
               Access Control, on the owned domain. Cents per month.
on demand   →  ALB + ECS + RDS for stage AND prod
```

The dashboard is hosted **in AWS, not on GitHub Pages**. Pages is free and
simpler, but hosting the showcase of an AWS project outside AWS demonstrates
nothing and reads poorly at interview; S3 + CloudFront + OAC + ACM + Route53 is
itself part of what the project exists to prove, at negligible cost.

This forces a **fourth Terraform state level**, `infra/public-site/` (key
`public-site/terraform.tfstate`), applied locally under `demo-admin` and never
touched by `destroy.yml` — the same survival rule as `bootstrap-oidc` in
ADR-0015. If the dashboard lived under `infra/envs/*`, a teardown would delete
the artifact whose whole purpose is to prove the teardown works.

Regional gotcha: an ACM certificate for CloudFront must be issued in
**us-east-1**. The prod ALB certificate stays in us-west-2. Two certificates,
two regions, one domain.

The dashboard is the permanent public artifact. It reports environment status
honestly — "environment is currently down, last successful cycle: <timestamp>" —
and links to the last published test report and demo recording, which remain
viewable when nothing is running.

This keeps the budget-safe lifecycle that is the project's headline achievement,
instead of contradicting it with an always-on prod. The trade-off is accepted
explicitly: a visitor arriving at an arbitrary moment sees evidence of a working
system, not a live one.

### D2a — prod is stateless between cycles; prod data does NOT persist

A consequence of D2 that must be stated rather than discovered: the prod RDS
instance is created and destroyed with every cycle. Each deploy starts from an
empty database, runs migrations, and re-seeds. Nothing carries over.

This is accepted for what this project is — a delivery-platform demonstration,
not a service with users. But it has to be said out loud, because the
configuration openly contradicts the name:

```text
skip_final_snapshot      = true
backup_retention_period  = 0
recovery_window_in_days  = 0   (the DB secret)
```

Those settings exist for cycle repeatability and are indefensible on a real
production database. The honest framing, and the one to use at interview, is
**"a production-shaped environment with a promotion gate"** — not "production".
Volunteering that distinction is a stronger signal than being caught by it.

`docs/demo-script.md` must carry two practical consequences:

```text
- RDS takes 5-10 minutes to create, so a full cycle to a live prod is ~15 minutes.
  Bring the environment up BEFORE an interview; never demo the wait live.
- app.<domain> is a dead link most of the time. The dashboard must report the
  environment as destroyed and must not offer a link that goes nowhere.
```

Rejected for now, revisit in the polish track (Phase 17) if continuity ever
matters: restoring prod data from an S3 snapshot at deploy time (cheap, an
evening's work) or Aurora Serverless v2 with scale-to-zero (data survives,
storage-only cost when idle, but it changes the RDS module and adds risk to the
earliest and riskiest phase).

### D3 — public HTTPS on an existing domain

An owned domain is available, so prod gets a Route53 record, an ACM certificate,
a 443 listener on the ALB, and an HTTP→HTTPS redirect. Cost: hosted zone ~$0.50
per month; certificates are free.

Name layout:

```text
<domain> / www.<domain>   →  dashboard via CloudFront   (always up)
app.<domain>              →  prod ALB                   (on demand)
```

Serving a demo over plain HTTP on an ALB DNS name triggers browser warnings and
undercuts the security narrative. This is the cheapest fix available.

### D4 — external access is phased; view-only first

```text
Wave A (do first)  →  anyone with the link can VIEW: dashboard, architecture,
                      published Playwright report, run history, demo recording.
                      No authentication, no ability to spend money.

Wave B (later)     →  authorised third party can TRIGGER a full cycle.
```

Wave B is deferred to Phase 19, after the rest of the project is complete. It requires a
token authorizer, a GitHub App, and — non-negotiably — cost guardrails:
single-run concurrency, a daily cap, a hard TTL auto-destroy regardless of
outcome, and a reaction to the budget alarm. It is a strong exhibit in its own
right (a self-service ephemeral environment with cost controls), but it is not
what makes the project demonstrable, and building it early risks an unbounded
finish line.

Note the practical detail that makes Wave A necessary at all: **GitHub Actions
artifacts require a logged-in GitHub account to download.** Today the Playwright
report is only an artifact, so an external viewer cannot open it. Publishing the
report to a static site is what turns test results into evidence.

## Consequences

Positive:

```text
- the finish line is bounded and reachable
- the budget-safe story stays intact and is not contradicted by an always-on prod
- prod adds a genuine promotion gate, a rollback path and HTTPS —
  the three things stage cannot demonstrate
- test results become viewable without a GitHub account
```

Negative / accepted:

```text
- the AWS Organizations multi-account argument stays verbal, not demonstrated
  by a second workload account
- a visitor may arrive while every environment is down
- prod and stage share an account, so a blast-radius question at interview
  must be answered honestly: separated by role, state, prefix and VPC —
  not by account boundary
- prod keeps no data between cycles (D2a), and its RDS settings would be
  indefensible on a real production database. Name the limitation first;
  do not wait to be asked.
- a second deploy role widens the IAM surface that has to stay correct
  (see ADR-0015/0016: every new role is a new chance to break teardown)
- the project moves from three Terraform state levels to FIVE:
  bootstrap (local) / bootstrap-oidc / public-site / envs/stage / envs/prod.
  Only the last two are ever destroyed. docs/architecture.md must be written
  against this shape, not the three-level shape of ADR-0015.
```

## Alternatives rejected

```text
Separate prod member account
  → strongest isolation story, rejected on schedule cost. Revisit only after
    everything in docs/next-phases.md is done.

Always-on prod
  → rejected: ~$40-60/month against a $20 budget alarm, and it would make the
    project's own cost-control claim false.

Fully ephemeral prod with no static surface
  → rejected: nothing to link to between runs, which defeats the purpose of a
    portfolio artifact.

GitHub Pages for the dashboard
  → rejected: free and simpler, but it hosts the showcase of an AWS project
    outside AWS and demonstrates none of the skills the project is about.
    S3 + CloudFront costs cents and is itself an exhibit.

Prod on the Lightsail devbox via Docker Compose
  → rejected: cheap, but it abandons the ECS/ALB/RDS delivery story that is the
    entire point of the project.

Immediate full self-service launch for third parties
  → deferred, not rejected. See D4 Wave B.
```

## Validation

This ADR is a planning decision; it has no direct validation commands. The
decisions it records are validated by the phases that implement them, defined in
`docs/next-phases.md`:

```text
D1  → Phase 9  (M1): prod applies and destroys cleanly, stage unaffected
D2  → Phase 11 (M3): dashboard reachable with every workload environment destroyed
D3  → Phase 9  (M1): https://app.<domain> returns 200 with a valid certificate
D4  → Phase 11 (M3) for Wave A / Phase 19 for Wave B
```

Phase 13 is the MVP verification gate that exercises D1-D3 together in one
uninterrupted empty-to-empty run.
