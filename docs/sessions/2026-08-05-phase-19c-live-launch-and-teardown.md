# 2026-08-05 — Phase 19c: the button pressed for real, and what a cancelled run leaves behind

The first anonymous press in this project's history reached a dispatch, and a
full cycle ran from a browser with no AWS credential anywhere in the path. Then
a deliberately cancelled second launch produced an orphaned environment that no
automatic path could clean up, and unpicking that took the rest of the session.

Phase 19c is NOT closed. The three things it set out to prove were proven; the
state it left behind is a structural defect that needs a decision, and that
decision is 19d.

## The button was never wired

19b applied `infra/self-service` and left `site/index.html` holding
`enabled: false, endpoint: ""`, with a comment saying `enabled` becomes true in
19b "when there is a URL to put here". It never did. The panel hides itself
while disabled - deliberately, so a visitor cannot mistake an inert control for
a broken one - so nothing looked wrong.

The button existed in AWS and nowhere a visitor could reach it.

## Finding 1 — the response carried two CORS headers, and only a browser could see it

The first press failed with

```text
Access-Control-Allow-Origin cannot contain more than one origin.
Fetch API cannot load https://<function-url>/ due to access control checks.
```

Both `launch_handler._response` and the Function URL's `cors{}` block were
setting `access-control-allow-origin`. The function answered 200 in 360 ms every
time; the browser threw the reply away. The caller saw "the endpoint could not be
reached", which named nothing.

**Why 21 in-process assertions and two curl probes all missed it.** The unit
suite asserts on `code` and `message` in the body and never on headers. The CORS
layer only adds its header when the request carries an `Origin`, so curl without
one shows a single correct header - and the probe run at the start of this
session had no `Origin`. Preflight is answered by the Lambda service instead of
the function, so `OPTIONS` cannot show the pair either, and that probe came back
a clean 200 as well.

Both probes were built so that they could not see the defect. The control has to
differ from the suspect in the one respect under suspicion, and here that was a
single request header.

`make self-service-cors-check` now asserts EXACTLY one header, and fails on zero
as loudly as on two - zero is what removing the `cors{}` block would produce, and
a unit test on the handler would have called that healthy. Seen red on the real
defect, then green after the fix; the red was measured without a pipe.

## Finding 2 — the lock release had never worked, and named one third of its problem

The first cycle deployed, smoke-tested and destroyed cleanly, then failed on
`release-lock`:

```text
Input required and not supplied: aws-region
```

All THREE variables that job reads were missing, not one. It died on the first
input the action validates, so fixing that alone would have bought the next
failure.

Two of them had been written down in `docs/preflight-inventory.md` since 19b,
correctly, as repository variables - and never created. The document was right
and the step was never done.

**The mechanism is the finding.** A missing `vars.X` expands to an empty string,
not an error. Nothing fails where the mistake is. `release-lock` is the only job
outside `environment: stage`; it reads from the `self-service` environment, which
GitHub creates by itself on the workflow's first run, empty. The other two jobs
could not have noticed. The three are now REPOSITORY variables for exactly that
reason, and the job checks all three up front and names every one absent.

**A green `release-lock` does not prove the lock was released.** The delete is
wrapped in an if/else whose else branch - "not ours, superseded, or already
released" - is a success. Correct for an idempotent job, and it means the table
is the evidence, not the colour.

## What the first cycle proved

```text
anonymous press -> dispatch    from a browser, no AWS credential in the path
                               run attributed to the GitHub App, not to a human
deploy -> smoke -> destroy     14m32s + 8m31s, destroy self-checking
dashboard reported it          stage went UNKNOWN and greyed its stale values
                               while the run was in flight (ADR-0026)
TTL 90 minutes                 read from the lock the code wrote, not from a doc
                               expires_at - acquired_at = 5400 exactly
ExpiresAt / Launch tags        on the resources themselves, so the deadline
                               survives the loss of both the lock and Actions
```

The `locked` refusal was also proven against a REAL lock for the first time,
from a POST while the cycle ran: `409`, naming the holder and its deadline.

**And it named `run_url: null`.** That field is read in one place and written
nowhere. It cannot be filled at lock time - the lock is taken before the
dispatch, and `workflow_dispatch` returns no run id - and letting the job write
it later would widen the callback role past delete-one-item. 19b proved that
refusal against a hand-seeded item that carried a field the real writer never
writes: a fixture richer than reality, proving a capability the system does not
have.

## Finding 3 — a cancelled run leaves an environment nothing can clean

Break test 3 cancelled the second launch 150 seconds into `Terraform apply`.

The part under test passed: **`always()` does run after cancellation.** Both
`destroy` and `release-lock` started on a cancelled run, and the lock was
released even there.

Everything else about it failed, in a chain:

```text
apply killed mid-flight   -> S3 state lock left behind
destroy (if: always())    -> "Error acquiring the state lock", environment lives
release-lock (always())   -> releases anyway; it does not ask how destroy went
watchdog path 1           -> dispatches destroy.yml, which dies on the same lock
watchdog path 2 (blunt)   -> the only path that bypasses Terraform...
                             ...and cannot engage, because the lock is gone
```

`dispatch_destroy` returns early when `lock is None`, so the attempt is never
recorded; `dispatched_at` then reads 0 forever and the grace period never starts.
**Observed, not deduced** - the watchdog log shows `dispatched_destroy` at
05:46:13 and again at 05:51:13, with no `waiting_for_destroy` between them. It
would have re-dispatched every five minutes indefinitely, each run dying on the
state lock, while an ALB and an RDS instance billed by the hour.

The comment calls the skipped write idempotent, which is true. What it does not
say is that the skip disables the blunt path in the one case the blunt path
exists for.

## Break test 5 — the blunt path, on a real environment

Forced by writing a lock with `destroy_dispatched_at` 16 minutes old: the honest
construction of "Actions was asked and the environment is still here", which is
the only way to reach path 2 without breaking GitHub for real.

```text
{"action": "blunt_teardown",
 "deleted": {"ecs": [".../stage-app"], "alb": [".../stage-alb/963acb..."],
             "rds": ["aws-devops-sdet-demo-stage-db"]}}
```

Witnessed by the AWS CLI rather than by the function's own answer, with a
positive control in the same command: ECS and ALB gone, RDS `deleting`, the three
self-service Lambdas still listed.

## Finding 4 — "re-run destroy" is not a recovery when the state is short of resources

The watchdog's docstring says the recovery after path 2 is written down in
advance: re-run destroy, which reconciles what is already gone. It was tried and
failed three times, for two different reasons, and the second one is permanent.

```text
destroy #23  Error acquiring the state lock        (the killed apply's lock)
destroy #24  DependencyViolation on the ALB SG     15m38s, the whole timeout
destroy #25  the same, again                       15m34s
```

`terraform force-unlock` cleared the first. The second was not transient:

```text
in state           module.alb.aws_security_group.alb   and 18 others
in AWS, NOT in state
                   aws-devops-sdet-demo-stage-app-sg   references the ALB SG
                   aws-devops-sdet-demo-stage-rds-sg
                   aws-devops-sdet-demo-stage-cluster
```

The cancelled apply created resources it never recorded. Terraform cannot destroy
what it does not know about, and one of those orphans held an ingress rule
referencing a security group Terraform DOES manage. Every re-run re-attempted the
same impossible delete and spent its full fifteen-minute timeout doing it.

Normally `destroy -target=module.alb` works because a targeted destroy also takes
everything that DEPENDS on the target, and `module.ecs` depends on it - so the
app SG and its rule go first. With `module.ecs` absent from state, that ordering
silently stops existing.

Cleared by deleting the three orphans by hand, in dependency order. The next
destroy finished in 57 seconds.

## Also found, not fixed

```text
GET does not check the kill switch. With the switch engaged, GET still answers
200 and issues a nonce; only POST refuses. infra/self-service/README.md says the
endpoint "refuses every request", which is not true. Harmless - a nonce spends
nothing and is useless without a POST - but the document states an intention as
a fact.

The kill-switch refusal still names the budget alarm whatever engaged it. Caught
verbatim while parking: "the account budget alarm has fired", with the honest
reason sitting in the store. Known since 19b, still open.

The page hardcodes ttlMinutes and dailyCap, which the endpoint already reports in
its GET reply. One definition, two hosts.

Every launch invocation is a cold start - the function is never warm, so a press
costs about a second rather than 360 ms. A property, not a defect.

One deployment package serves all three Lambdas, so any handler change
redeploys the watchdog and the kill switch too.
```

## The state the account is left in

Verified from the devbox with `sts get-caller-identity` first, every result
assigned under `set -e`, and a positive control in the same command:

```text
ecs, rds, alb, nat, eks, unattached EIPs, stage security groups, vpc   none
the three self-service Lambdas                                        present
```

The endpoint is **parked again**, by hand, with the reason recorded in the store:
the blunt path cannot engage while the lock is missing, and that is the state a
cancelled run leaves. `POST` refuses `kill_switch`; `GET` does not, per above.

Two of the three daily launches were used. `count#2026-08-05 = 2`.

## What 19c did not settle

```text
- whether the button stays anonymous. Asked twice by the owner before 19b,
  deferred on purpose, and still deferred - but it is no longer hypothetical:
  the button was live and public for about three hours today.
- the blunt-path gap above. It needs a decision, not a patch: record the
  dispatch attempt somewhere that survives a missing lock, or recreate the lock
  when resources are found without one. That is 19d, and it wants an ADR.
- the two "the endpoint says something untrue" fixes (kill-switch message,
  run_url), batched deliberately so one package build and one apply cover both.
```

## Cost

The two cycles and the orphaned environment together ran well under an hour of
ALB + RDS + Fargate. Measured cycles in this project have been $0.09 and $0.17;
this session is of that order, plus the standing ~$0.45/month of the
self-service level. Exact figures once Cost Explorer settles.
