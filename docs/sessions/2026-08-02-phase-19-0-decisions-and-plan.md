# 2026-08-02 — Phase 19.0: self-service launch, decisions and plan

Decisions only. No code, no HCL, no workflow, nothing applied, no AWS API
called. Phase 19 is the one phase where the expensive mistake is a design that
cannot refuse, so it is the one phase worth deciding separately from building.

## What was decided

```text
ADR-0034  the trigger path: a Lambda Function URL and a GitHub App, at a new
          permanent state level, dispatching a stage-only workflow
ADR-0035  five guardrails, each a REFUSAL with a break test, with real numbers;
          and the out-of-band watchdog moved off the Lightsail devbox
```

### ADR-0034 — the direction of trust reverses, and that has to be said out loud

Everywhere else in this project GitHub authenticates to AWS through OIDC, and no
static AWS key exists. A button on a public page reverses it: something in AWS
has to authenticate to GitHub, on behalf of a visitor with no account, and there
is no OIDC in that direction. A browser cannot hold the credential and a static
site cannot refuse anything.

So the question was never whether a long-lived GitHub credential enters the
project. It does, here. The decision is which one and for how long a token
minted from it is valid: a **GitHub App**, its private key in Secrets Manager,
minting installation tokens that expire in an hour and carry one permission.
A fine-grained PAT was rejected — a user credential, attributed to a person,
expiring on a calendar, revoked everywhere at once.

The consequence is a qualifier the project now has to carry:

```text
no static AWS keys anywhere, and exactly one static GitHub credential,
in Secrets Manager in the demo account, readable by one Lambda role.
```

It is a better talking point with the qualifier than without it.

### The sixth arrival at ADR-0027's rule

The lock, the day counter and the kill switch are state ABOUT a cycle. A control
that lives inside the environment it controls is destroyed by the thing it is
controlling — the same sentence as the registry (0018), the hosted zone (0024),
the dashboard (0027), the release pointer (0029) and the notification channel
(0032), reached this time from a spend control.

### Two things stated so they cannot be quietly assumed later

**The public path cannot reach prod, by IAM rather than by an input.** The
launch workflow resolves the stage deploy role only and declares no prod
environment, so no value of any input produces a prod credential.

**The nonce is a speed bump and is labelled as one.** Whoever can read the page
can get one. The design goal is not "only the right people can press it" but
**"it does not matter who presses it"** — which is why the cost bound has to
hold under an adversary, and why a CAPTCHA was rejected: if the bound needs it,
the bound is wrong.

### ADR-0035 — numbers, not adjectives

```text
TTL              90 minutes
per-day cap      3 launches
worst case       ~$0.30/day, under $10/month sustained
measured basis   $0.09 (16a) and $0.17 (16b), already on record
```

Five guardrails, five break tests, all of them closing criteria for 19b and 19c:
the lock (the Lambda refuses, because Actions only queues — `cancel-in-progress`
would cancel a run mid-deploy and leave an environment nothing is left to
destroy), the cap **failing closed** (an unreadable counter is not zero launches
today — the same sentence as the expired SSO token that printed nine empty lines
that looked exactly like a clean account), the TTL in-band and out, the kill
switch (honest about being a slow backstop: Budgets lags hours and stops the
NEXT run, not the one that spent the money), and the watchdog.

## The one finding: the plan contradicted an invariant

`docs/next-phases.md` specified the out-of-band watchdog as a cron on the
Lightsail devbox. The requirement is right — a failure domain separate from
GitHub Actions, so that a workflow dying before its destroy step still stops the
money. The mechanism is not.

A cron has no human. The devbox reaches this account through IAM Identity Center
with `aws sso login --use-device-code`, a device code somebody types. There is
no unattended path from that machine into this account that is not a static
credential on disk — an access key, or an IAM Roles Anywhere certificate, which
is the same category with more steps.

And the increment it buys is small, because the domain actually distrusted is
**GitHub Actions, not AWS**. A watchdog independent of Actions does not have to
be independent of AWS, and one that were could not act anyway: if the region's
control plane is unavailable, nothing deletes anything from anywhere.

So the watchdog becomes EventBridge Scheduler plus a Lambda at the permanent
level. Recorded as ADR-0035 §5, and `docs/next-phases.md` amended rather than
left disagreeing with the ADR.

Two rules were written into it while it was being decided, both of them the
project's own, arrived at again from a new direction:

- **a missing deadline is not permission to run forever.** If a deploy dies
  before tagging, resources exist with no TTL tag; untagged workload resources
  under the environment prefix are expired after a grace period, not exempt.
  The absence is itself a symptom of the failure the watchdog exists for.
- **the blunt path is the one that must be broken on purpose.** Deleting the
  service, ALB and RDS directly will never run in a normal cycle, which makes
  it exactly the gate that has only ever been seen green.

## What was NOT done, deliberately

No scaffold. The session's scope was decisions and the plan, and 19a is now
"scaffold" rather than "decisions and scaffold" because the decisions are made.
Nothing was applied, no AWS API was called, and no GitHub App exists yet.

## Documents this session edited

`docs/decisions/0034-the-self-service-trigger-path.md` and
`docs/decisions/0035-launch-guardrails-and-where-the-watchdog-lives.md` (new),
`docs/next-phases.md` (Phase 19 split into 19a/19b/19c and the watchdog
amended), `docs/phase-gates.md` (status row and a completion section),
`docs/discussion-log.md` (Current state), this summary and
`docs/sessions/INDEX.md`. `docs/session-primer.md` was NOT touched, so the
transfer-buffer copy on the MacBook does not need refreshing.

## Cost

**$0.** Nothing was applied to AWS and no environment existed at any point.
