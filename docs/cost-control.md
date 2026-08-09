# Cost control

What this project actually costs, and the settings that keep it that way. Written
from measured runs recorded in `docs/phase-gates.md` and the Terraform defaults in
`infra/`, not from a price list assumed rather than checked — the project's own
rule (`docs/session-primer.md`, "a claim about state is not state") applies to
money the same as to infrastructure.

## The two kinds of cost

```text
permanent   infra/bootstrap, infra/bootstrap-oidc, infra/shared-ecr, infra/dns,
            infra/public-site — applied once, never touched by `destroy.yml`,
            billed every month whether or not a cycle is running
per-cycle   infra/envs/stage, infra/envs/prod — ALB + ECS Fargate + RDS,
            destroyed at the end of every cycle, billed only while up
```

Only the last two are ever destroyed (`docs/architecture.md`). Getting this
split wrong in either direction is expensive in a different way: something
per-cycle that should be permanent gets deleted along with the evidence that
teardown works (this is why the container registry moved up a level — ADR-0018);
something permanent that should be per-cycle bills every month for nothing.

## Permanent levels — what's actually running all the time

```text
infra/bootstrap        S3 state bucket, versioned, no lifecycle expiry.
                       Storage only, a handful of small state files. Cents.
infra/bootstrap-oidc   an IAM OIDC provider + two IAM roles (stage, prod
                       deploy). IAM resources are free.
infra/shared-ecr       one ECR repository. Billed on stored image size;
                       one FastAPI image, well under the free tier in
                       practice.
infra/dns              a Route 53 hosted zone (~$0.50/month flat, AWS's
                       standard per-zone charge) + an ACM certificate
                       (DNS-validated, free).
infra/public-site      S3 (private, versioned) + CloudFront with Origin
                       Access Control + a second ACM certificate in
                       us-east-1. Billed on requests and data transfer;
                       a personal-traffic dashboard is cents/month.
```

Order of magnitude for everything in this list together: **under $1/month**,
dominated by the $0.50 hosted zone. Nothing here scales with demo activity.

AWS Budgets itself (`infra/modules/budgets`) is free and applies to every
environment — see "The budget alarm" below.

## Per-cycle levels — what's billed only while a cycle is up

Defaults, from `infra/envs/stage/variables.tf` (prod matches unless noted). The
variable defaults and not the `terraform.tfvars.example` beside them: no
`.tfvars` file is committed and no workflow passes a sizing `-var`, so the
defaults ARE the effective configuration — which is why `scripts/sizing.py` reads
them, and refuses if a `.tfvars` ever appears:

```text
ECS Fargate    task_cpu = 256, task_memory = 512, desired_count = 1
RDS            db.t4g.micro, PostgreSQL 16, single instance — no Multi-AZ
               (a Checkov skip in .checkov.yaml, decision not oversight:
               Multi-AZ is "money the demo refuses")
ALB            one, public subnets, no WAF (same category of skip)
CloudWatch     log_retention_days = 7
NAT Gateway    none — ADR-0006. The app task gets a public IP instead and
               reaches ECR/Secrets/CloudWatch over the Internet Gateway,
               with ingress locked to the ALB security group. This is the
               single largest saving in the whole design: a NAT Gateway is
               ~$0.045/hour PLUS per-GB data processing, running the whole
               time an environment is up, whether or not it's used.
```

RDS is the slow part of every cycle — 5 to 10 minutes to create, which sets
the floor for how fast `deploy-stage` can reach a live environment
(`docs/next-phases.md`). It does not need to finish before ALB/ECS work
starts, but nothing is reachable until it does.

### What a cycle has actually cost, measured

Not estimated — read from the list-price arithmetic in the session summaries
that closed each phase, using the smallest shapes above:

```text
Phase 16a (2026-07-29)   stage ~1h15m, prod ~23m   ≈ $0.09
Phase 16b (2026-07-31)   stage ~2h (2 applies),
                         prod ~40m                 ≈ $0.17
```

Both are full stage+prod cycles including RDS. A short single-environment
smoke run costs less; a cycle left up overnight by mistake is the failure
mode the budget alarm exists to catch, not something this project has ever
done on purpose. ADR-0017 puts an always-on prod (ALB + Fargate + RDS, no
teardown) at roughly $40-60/month at these same shapes — the reason prod is
on-demand rather than always up.

**These are list-price approximations, not an invoice.** If a precise figure
is ever needed, re-derive it from AWS Cost Explorer for the account, tagged by
`Project = aws-devops-sdet-demo` — do not extrapolate further from the two data
points above without checking.

### Since Phase 20d the arithmetic is a command, not a paragraph

The two figures above were worked out by hand in a session and written down. That
is the shape this project keeps removing: a number beside the thing it describes,
correct on the day, silent afterwards. `scripts/fold-cost.py` computes the same
kind of figure from the cycle's own timelines and a captured rate table
(**ADR-0045**):

```text
make rates        capture a dated table from the AWS Price List Query API into
                  site/data/rates.json. Needs pricing:GetProducts, a free read
make rates-check  every kind infra/ declares is priced, free, or named as not
                  metered - never zero by silence
make cost-check   the fold itself, against fixtures. No AWS, no credential
```

Three things it does that the hand arithmetic did not:

```text
lifetime    the meter runs from create-complete to delete-start, across the
            APPLY and DESTROY runs. Terraform's own elapsed_seconds is how long
            it took to build the thing, which for the ALB of 2026-08-08 was a
            ninth of how long that thing existed
a band      create START to delete FINISH is the other end. RDS in that cycle
            was between 852 and 1381 seconds of meter, and a single number would
            have hidden 62% of uncertainty behind two decimal places
minimums    a database deleted two minutes after it came up still bills ten. The
            one direction a duration-only estimate can never go
```

It is an ESTIMATE and says so in every rendering. No billing API is called
anywhere in this project; AWS Budgets watches the actual spend from the other
side, which is the guard that matters (see below). ADR-0039's promise to
reconcile once against a real bill is retired in ADR-0045 D6 rather than left
standing as pending work.

### The first cycle it priced on its own (2026-08-09, Phase 20h)

Wired into the teardown in Phase 20f, and run live for the first time here. Not
worked out by hand afterwards — printed by `destroy stage #41` as the
environment came down:

```text
cycle CLOSED  2026-08-09T05:13:18Z -> 2026-08-09T05:43:24Z  (1806s)
ESTIMATE      $0.0178 .. $0.0235          stage only, prod not deployed
  ALB     1557-1766s   $0.0097 .. $0.0110
  RDS      812-1339s   $0.0043 .. $0.0071
  ECS     1100-1545s   $0.0038 .. $0.0053
32 created: 3 priced, 25 free, 4 not metered, 0 UNPRICED
```

Two things worth keeping from it. The ALB is the largest share of a short
cycle — it meters from the moment it is created and the database takes minutes
to become useful, so the cheapest saving in a demo is a shorter cycle rather
than a smaller shape. And `0 UNPRICED` is the number to watch when `infra/`
grows: it says every created resource landed in a class, rather than a new kind
being silently free.

## The budget alarm

`infra/modules/budgets` (ADR-0011) is applied at every environment level that
calls it — currently stage and prod, both `budget_enabled = true` by default.

```text
limit                 $20/month  (monthly_budget_limit, per environment)
ACTUAL notification   fires at 50% of limit   (budget_actual_threshold)
FORECASTED            fires at 100% of limit  (budget_forecast_threshold)
recipient              TF_VAR_BUDGET_EMAIL — a GitHub environment SECRET in
                      both stage and prod (moved off a variable in Phase 15,
                      docs/security-posture.md — a GitHub variable is not
                      masked and the address had been printed in run logs)
```

This is the safety net for the exact failure this project is structurally
prone to: an environment brought up, then forgotten. AWS Budgets itself is
free; the cost of running it is zero and the cost of not running it is
unbounded.

## Worst case now that the button IS public (Phase 19, LIVE)

Until Phase 19b nobody but the owner could start a run, so this document had
never needed a number for what a stranger could spend. **ADR-0035** decides one,
and it is a real number rather than an adjective:

```text
TTL per launch     90 minutes, enforced in-band by the workflow's own destroy
                   job and out-of-band by an EventBridge-scheduled Lambda
per-day cap        3 launches, counted by UTC date, and the counter FAILS
                   CLOSED - an unreadable count refuses rather than allows
worst case         ~$0.30/day, i.e. under $10/month if somebody presses it to
                   the limit every single day, against the $0.09 and $0.17
                   cycles measured above
reaches            stage only, by IAM rather than by an input
```

The permanent cost of the machinery itself is one Secrets Manager secret at
$0.40/month, a DynamoDB table holding four items, and three Lambdas invoked a
handful of times a day - cents, fixed, the same trade ADR-0027 made for the
dashboard.

All of this is running. The numbers above are what the level is designed to
bound; what has actually been observed since it went live is an order of
magnitude smaller, because no launch has yet survived anywhere near its TTL:

```text
19f  a cancelled launch, RDS up for 100 minutes    about $0.02
19g  the 2026-08-07 pair                           about $0.10
19g  cancelled 00:44:15, reclaimed by 00:49:09     about $0.03
```

19c, the first public launch, has no recorded figure — the phase closed without
one. That is a gap in the record rather than a zero, and it is why the rows above
start at 19f.

The distance between $0.30/day and $0.03 is the TTL never being reached: every
measured launch so far ended in minutes, by its own teardown, rather than in 90.
The worst case stays the number to quote, because it is the one that does not
depend on how the launches happened to go.

## Idempotency and the "always destroy" rule

```text
- every per-cycle resource is created by a deploy that can be re-run: image
  tags are gone (registry made immutable, Phase 14) in favour of digests,
  so re-running deploy-stage against an unchanged image REUSES it rather
  than colliding with its own tag.
- destroy.yml tears down the LOAD BALANCER in a targeted pass before the
  rest of the network (ADR-0016, narrowed by ADR-0037) - required for the
  teardown to complete at all, not an optimization. The target is
  `module.alb.aws_lb.this`, NOT `module.alb`: the module also holds the ALB
  security group, which AWS refuses to delete while the app SG still
  references it, and Terraform retries that for 15 minutes before failing.
- teardown is verified against the AWS CLI, not against Terraform state
  (docs/session-primer.md verification habits) - ecs, rds, alb, nat, eks
  all empty, ecr still returning the shared (permanent) registry as a
  positive control that the check itself is looking at something.
- the rule that follows from all of this: an environment is not left up
  between sessions or after a demo. Nothing in this project defends against
  "up and forgotten" except the humans running it and the budget alarm
  above. The one exception is the SELF-SERVICE path: a public launch carries
  a per-run TTL and an EventBridge/Lambda watchdog that dispatches destroy on
  its own record (Phase 19, ADR-0035/0036; proven by a live cancellation on
  2026-08-06). It reclaims the BILLABLE resources without a human, not
  necessarily the whole environment - see ADR-0037. An environment brought up
  by `deploy-stage` has no such backstop and is still the operator's to remove.
```

## What would change this document

```text
- Phase 17 (prod data continuity), if ever built: a restore-from-S3 step or
  Aurora Serverless v2 both add storage cost that survives teardown - the
  first genuinely new category since infra/dns.
- Phase 19 (self-service launch) is BUILT and live: the per-run TTL and the
  per-day cap bound this document's per-cycle numbers against a stranger
  triggering them, not just this project's own sessions. What would change the
  document now is the cap or the TTL moving, or a launch that actually runs to
  its TTL - none has yet.
```
