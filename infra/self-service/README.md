# infra/self-service

The button, and everything it uses to refuse. Permanent level (ADR-0027's rule,
sixth arrival), applied locally under `demo-admin`, never touched by
`destroy.yml`.

Read `docs/decisions/0034-the-self-service-trigger-path.md` and
`docs/decisions/0035-launch-guardrails-and-where-the-watchdog-lives.md` first.
They are the reasoning; this is the wiring.

```text
launch.tf      Function URL -> launch Lambda -> workflow_dispatch (stage only)
               plus the narrow callback role the workflow releases the lock with
watchdog.tf    EventBridge Scheduler -> watchdog Lambda (out-of-band TTL),
               and the SNS topic -> kill-switch Lambda the budget alarm flips
main.tf        the control store, the secret CONTAINER, the deployment package
src/           the handlers. The refusal logic is in control.py, which imports
               no AWS SDK, so tests/unit can exercise every refusal in-process
```

## Before the first apply

```bash
make self-service-package
```

PyJWT and cryptography are not in the Lambda Python runtime, and minting a
GitHub App installation token means signing an RS256 JWT. The apply has a
precondition on the package size: an empty archive is what a forgotten build
step looks like, and Lambda accepts one happily.

## The account quota this level cannot satisfy

`reserved_concurrent_executions` is `-1` on all three functions, and the
decided numbers (2, 1, 1) are commented in `terraform.tfvars.example`. AWS
refuses any reservation while the account's Lambda `Concurrent executions`
quota is 10, since the unreserved pool may not fall below 10. Found by applying
in 19b; amended in ADR-0034. The account ceiling is the bound meanwhile.

## Releasing a lock nothing is holding

A `startup_failure` strands the lock (ADR-0069). GitHub rejects an invalid
workflow file before any job exists, so `release-lock` — which is a job, running
`if: always()` — never runs. The Lambda did nothing wrong: the dispatch was
accepted and a run was created, so from the endpoint's side the launch happened.
The watchdog sees nothing to sweep, because it reclaims environments and that
run created none.

The lock then keeps the button shut until its own deadline, which is
`var.ttl_minutes` — **150 minutes** since ADR-0068 raised it, so this window got
an hour longer as a side effect of a change about something else.

Check first that nothing is actually running:

```bash
aws dynamodb get-item \
  --table-name aws-devops-sdet-demo-self-service-control \
  --key '{"pk":{"S":"lock"}}'
gh run list --workflow self-service.yml --limit 3
```

If the run named in `launch_id` has finished, the lock is stale:

```bash
aws dynamodb delete-item \
  --table-name aws-devops-sdet-demo-self-service-control \
  --key '{"pk":{"S":"lock"}}'
```

**The daily counter is NOT refunded and should not be.** `decide_launch()` says
why in its own docstring: a launch that got far enough to hold the lock has had
its turn, and a refund path is a second place for the cap to leak.

## Turning the kill switch OFF

There is no target, no handler and no other command: the way back is one
`delete-item`, and until Phase 19b it was written down nowhere. Engaging is
automated (the budget alarm publishes, a Lambda flips the flag); disengaging is
a decision, so it is manual - but manual and UNDOCUMENTED are different things,
and it was the second one.

```bash
aws dynamodb delete-item \
  --table-name aws-devops-sdet-demo-self-service-control \
  --key '{"pk":{"S":"killswitch"}}' \
  --profile demo-admin --region us-west-2
```

Read it before deleting it - the item carries the `reason` it was engaged with,
and that is the only place the honest cause is recorded:

```bash
aws dynamodb get-item \
  --table-name aws-devops-sdet-demo-self-service-control \
  --key '{"pk":{"S":"killswitch"}}' \
  --profile demo-admin --region us-west-2
```

## Throwing it BY HAND, so the refusal stays honest

Fixed in 19d: the refusal used to name the budget alarm whatever engaged the
switch, so an endpoint parked between phases told visitors something untrue. It
now reports the `source` the writer recorded, and a hand-written item has to say
so — otherwise it defaults to `manual`, which is also true, but less useful than
the reason.

```bash
aws dynamodb put-item \
  --table-name aws-devops-sdet-demo-self-service-control \
  --item '{"pk":{"S":"killswitch"},"engaged":{"BOOL":true},"engaged_at":{"N":"'"$(date +%s)"'"},"source":{"S":"manual"},"reason":{"S":"parked between phases; no budget event"}}' \
  --profile demo-admin --region us-west-2
```

The `reason` stays in the store and in the log on purpose: the budget path
writes an SNS message with the account's budget in it, and the refusal goes to
the public internet. The endpoint reports `source` and nothing else — the same
rule that moved the budget email out of a GitHub variable in Phase 15.

Also 19d: the switch now refuses `GET` as well as `POST`. It used to refuse only
`POST`, while this file said it "refuses every request", so a parked endpoint
went on issuing nonces and writing an item to the store for anyone who asked.
Of the two, this file was right.

## What is NOT in git, and never will be

Same category as the NS delegation in the parent zone and prod's protection
rules - real state Terraform cannot assert:

```text
the GitHub App itself, and its permission set (actions: write, one repo)
its installation on UVE-QA/aws-devops-sdet-demo
the private key, pasted by hand into the secret this level creates
```

If a launch ever returns 401, check those three before anything else.

## The control table's four kinds of item

```text
killswitch      the flag, plus the source and reason it was thrown with
lock            the launch in flight. Written by the launch Lambda, deleted by
                the workflow's release-lock job - but only when destroy
                SUCCEEDED (ADR-0036 D2)
count#<date>    the day counter, incremented conditionally
nonce#<value>   single use, with a DynamoDB ttl
watchdog        the watchdog's own record: when it last asked Actions to
                destroy, and which launch ids it asked about. Written and
                deleted by the watchdog alone (ADR-0036 D1)
```

`watchdog` is new in 19d, and it exists because the previous version of that
record was a field on `lock`. A cancelled run leaves the environment alive and
the lock deleted, so the watchdog forgot every dispatch it made and never
reached its own blunt path. Its memory was stored on a record owned by the thing
it exists to distrust.

## Status

**Applied 2026-08-05 (Phase 19b), and parked.** Everything here exists in the
account. The endpoint is public and configured, and it currently refuses every
request because the kill switch was engaged BY HAND at the end of that session -
an armed public button with nobody watching had no reason to stay armed. 19c
starts by clearing that item, with the command above.

Proven against the real table in 19b: the kill switch, the store-unavailable
refusal on both halves, the lock (naming its holder, with nothing queued), and
the daily cap (with the lock released afterwards). Proven by a live cycle in
19c: the TTL, both watchdog paths including the blunt one, and `locked` against
a real lock.

19d rewired what 19c's cancelled run exposed (ADR-0036). What that state needs
is a cancelled run that cleans itself up with nobody in the loop, and until that
has been seen, this level's newest three parts are written and not witnessed:
the watchdog's own record, the conditional lock release, and
`scripts/break-stale-state-lock.sh`.

This level needs provider `~> 6.0` and is the only one that does - see the
comment in `main.tf`.
