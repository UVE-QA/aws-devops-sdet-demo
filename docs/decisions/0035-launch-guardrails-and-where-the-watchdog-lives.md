# ADR-0035: The launch guardrails are five refusals with five break tests, and the watchdog cannot live on the devbox

## Status
Accepted (Phase 19a, 2026-08-02). ADR-0017 D4 named four cost guardrails and
`docs/next-phases.md` Phase 19 named five. This decides what each one promises,
where its state lives, and how each is proven to be able to fire — and amends
the mechanism of the fifth.

## Context

ADR-0034 builds a path from a public page to a workflow that spends money, and
makes exactly one claim: everything on it can be refused at a single point. This
ADR is the refusals.

The bound they have to hold is a real number rather than an adjective. Two full
cycles have been measured and recorded:

```text
Phase 16a   $0.09
Phase 16b   $0.17   (stage up ~2h across two applies, plus prod ~40m)
```

A public launch is stage only and bounded by a TTL, so the exposure is
duration x rate per launch, and cap x launch per day:

```text
TTL              90 minutes
per-day cap      3 launches
worst case       ~$0.30/day, under $10/month if someone presses it to the
                 limit every day forever
```

Those two numbers are the decision. "Cost controls" without them is prose.

The failure this ADR is written against is not a guardrail that is missing. It
is a guardrail that is present, has never been seen doing anything, and turns
out not to work — which is this project's single most common defect and the
reason fifteen gates have been broken on purpose so far.

## Decision — five guardrails, five failure modes, five break tests

### 1. One run at a time: the Lambda REFUSES, because Actions only queues

GitHub's `concurrency:` does not refuse. It queues, or it cancels.
`cancel-in-progress: true` would cancel a run mid-deploy, which is exactly how
an environment is left half-created with nothing left to destroy it. `false`
queues — and a queue of fifty launches is fifty cycles, arriving later. Neither
is the requirement.

So the refusal lives in the Lambda, against a durable lock at the permanent
level, taken BEFORE the dispatch and released by the workflow's final job.
`concurrency: { group: self-service, cancel-in-progress: false }` stays as a
second layer, for the race between the check and the dispatch.

Worth noting while passing: **no workflow in this repository declares
`concurrency` today.** Two simultaneous `deploy-stage` runs would race on the
same Terraform state. That is a pre-existing gap this guardrail brushes against
and does not close.

The lock needs an owner and an expiry, or a run that dies wedges the button
forever. Its expiry IS the TTL: a lock older than the TTL is not a lock, and
guardrail 5 is what makes that safe to say.

```text
break test   two launches back to back. The second returns a refusal that names
             the run holding the lock, and NO second run is queued. Then kill
             the holder and confirm the lock is released rather than inherited.
```

### 2. A per-day cap, and it fails CLOSED

A counter at the permanent level, keyed by UTC date, incremented by a
conditional write rather than read-then-write. Over the cap the endpoint refuses
and says when the count resets.

The failure mode that matters is not the cap. It is the READ.

**If the counter cannot be read, the endpoint must refuse.** An error is not
"zero launches today" — the same sentence as the post-teardown check whose
expired SSO token printed nine empty lines that looked exactly like a clean
account, and as the metric filter that would have matched nothing forever. A
spend control that fails open is not a spend control.

```text
break test   pre-seed the counter at the cap and press: refused.
             Then remove the Lambda's permission on the store and press again:
             also refused, and for a reason that names the STORE rather than
             the cap, because those are two different states and a visitor
             being told the wrong one is how the next hour gets wasted.
```

### 3. A hard TTL, enforced in-band and out-of-band

In-band: the launch workflow's destroy job is `if: always()`, and the workflow's
`timeout-minutes` is strictly LESS than the TTL, so a hung run reaches its own
destroy before the deadline it is being held to.

That covers a run that FAILS. It does not cover a run that is force-cancelled, a
runner that dies, or GitHub being unavailable — which is the case the guardrail
exists for. `if: always()` is a promise made by the thing that might not be
there.

```text
break test   cancel a launch mid-deploy and confirm the destroy job still ran.
             Verify the account with the AWS CLI from the devbox, not with
             Terraform state - the rule this project already has after a
             teardown.
```

### 4. The budget alarm flips a kill switch, and it is a slow backstop

`infra/modules/budgets` only emails today. Reacting means refusing new launches:
a flag at the permanent level, read by the Lambda before anything else, flipped
by a Lambda subscribed to an SNS topic — not by email, because an email
subscription needs a confirmation click, and the channel has to outlive what it
reports on. ADR-0032 reached that same sentence about the 5xx alarm.

Say what it cannot do. AWS Budgets evaluates a few times a day and lags by
hours. **It cannot stop the run that spent the money; it stops the next one.**
The fast control is the TTL. The budget alarm is the one that notices a slow
leak the TTL cannot see — a resource the destroy path does not know about, which
is precisely the kind of thing nobody predicts.

```text
break test   publish to the topic the message shape AWS Budgets actually
             sends, with one field changed, and confirm the flag flips and the
             next launch is refused. The same technique as 16b's injected log
             line, for the same reason: the shape has to be the real one, or
             the test is about the fixture.
```

### 5. The out-of-band watchdog moves off the devbox

`docs/next-phases.md` specifies a cron on the Lightsail devbox, for the separate
failure domain: if Actions itself is broken, or a workflow dies before its
destroy step, the money still stops. **The requirement is right. The mechanism
does not survive contact with this project's own rules.**

A cron has no human. The devbox reaches this account through IAM Identity
Center, with `aws sso login --use-device-code` and a device code somebody types.
There is no unattended path from that machine into this account that is not a
static credential on disk — an access key, or an IAM Roles Anywhere certificate,
which is the same category with more steps. The loudest invariant in the project
is that no static AWS key exists anywhere, and it is worth more than the
increment this placement buys.

And the increment is small, because the domain actually distrusted is **GitHub
Actions, not AWS.** A watchdog independent of Actions does not have to be
independent of AWS — and one that were could not act anyway: if the region's
control plane is unavailable, nothing deletes anything, from the devbox or from
anywhere else.

```text
EventBridge Scheduler -> Lambda, at the permanent level, on a fixed interval,
sharing nothing with the launch path except the account.
```

Out-of-band with respect to the thing that was distrusted, with no credential
that outlives a request.

#### What it keys off, and what a MISSING deadline means

Each environment carries its deadline where the watchdog can read it without
asking Actions anything: a tag on the resources it would have to delete.

If the deploy died before tagging, resources exist with no deadline. The rule is
the one this project keeps relearning: **a missing deadline is not permission to
run forever.** Untagged workload resources under the environment prefix are
treated as expired after a short grace period, not as exempt. Absence of
evidence is not absence — and here the absence is itself a symptom of the exact
failure the watchdog exists for.

#### Two paths, and the blunt one is the one that must be broken on purpose

The watchdog first dispatches `destroy.yml`, which leaves Terraform state
consistent. If the environment is still alive some minutes later — the case
where Actions is the broken thing — it deletes the billable resources directly:
the ECS service, then the ALB, then the RDS instance, in that order, for the
reason ADR-0016 already records about ENIs and the internet gateway. Terraform
state is then stale, and the recovery is written down in advance rather than
discovered under pressure: re-run destroy, which reconciles what is already
gone.

The blunt path will never run in a normal cycle. That makes it precisely the
gate this project has learned to distrust — one that has only ever been seen
green is indistinguishable from one that cannot fire. It is broken on purpose
in 19c, against a real environment, with the AWS CLI as the witness.

## What the guardrails deliberately do not do

```text
- they do not bound the cost of a single SUCCESSFUL cycle. That is the demo,
  and it is the thing already measured twice
- they do not apply to the owner's own workflow_dispatch runs. The cap is on
  the public path, not on the project
- they do not protect prod, because nothing on the public path can reach prod
  (ADR-0034). A guardrail defending something already unreachable would be a
  check that cannot fail
- not one of the five is proven by reading it
```

## Consequences

- `infra/self-service` grows a lock, a day counter, a kill-switch flag, an SNS
  topic, an EventBridge schedule and a second Lambda. All permanent, all cents.
- The environment modules gain a TTL tag. It goes to **stage and prod in the
  same commit**, per the shared-invariant rule, even though only stage is
  reachable from the button — prod kept a broken shape for seven weeks the last
  time a shared fix was applied to one environment only.
- `docs/next-phases.md` Phase 19 is amended: the watchdog is not a cron on the
  devbox. `docs/lightsail-devbox.md` describes what the devbox does, and this is
  now not one of those things.
- `docs/cost-control.md` gains the worst-case public exposure — a number it does
  not currently have, because until now nobody but the owner could start a run.
- Five break tests are closing criteria for 19b and 19c, not optional extras.
  The count of gates broken on purpose in this project goes from fifteen to
  twenty, or the button does not become public.
- A demo-script line worth having: the exhibit is not the button. It is the five
  refusals, and each of them can be shown firing.
