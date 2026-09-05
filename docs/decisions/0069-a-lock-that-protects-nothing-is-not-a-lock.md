# ADR-0069: A lock that protects nothing is not a lock

## Status
Proposed (Phase 34, 2026-09-05). Extends **ADR-0035** guardrail 1, and corrects a
consequence **ADR-0068** introduced without noticing. Decision recorded; the
implementation needs a Lambda package rebuild and an apply of
`infra/self-service`, and is not in this commit.

## Context

The first unattended launch after ADR-0068 died as `startup_failure`: a reusable
workflow's permissions must be a subset of its caller's, and the caller granted
less. GitHub rejects a workflow file like that **before any job exists**.

That is a state ADR-0035 has no rule for. Guardrail 1 is `release-lock`, a JOB
that runs `if: always()` — and `always()` cannot run when there are no jobs. So:

```text
the Lambda      took the lock and consumed one of three daily launches. It did
                nothing wrong: the dispatch was accepted, HTTP 202, a run was
                created. From the endpoint's side the launch happened.
the workflow    never started. No jobs, no log, no annotation.
release-lock    could not run. It is a job.
the watchdog    saw nothing to sweep. It reclaims ENVIRONMENTS, and this run
                created none.
```

The lock then sat until its own deadline, because `lock_is_expired()` treats a
lock past its deadline as no lock and the next press takes over.

**Two harms, and the second is smaller than it first looked:**

- the button is shut for up to a full TTL, protecting nothing
- one of three daily launches is spent on a run that did nothing

The second is deliberate and stays: `decide_launch()` says so in its own
docstring — *"a launch that got far enough to hold the lock has already had its
turn, and a refund path is a second place for the cap to leak."* That reasoning
survives this ADR untouched.

**The first was made worse by ADR-0068 and nobody noticed at the time.** That
phase raised `ttl_minutes` from 90 to 150 so the TTL would exceed the sum of the
five job timeouts. It also, silently, lengthened by sixty minutes the window in
which a stranded lock keeps the button shut. The two numbers were coupled in one
direction and nobody checked the other.

Recovery today is a manual `delete-item`, which is written down **nowhere** —
the same shape this project already paid for with the kill switch, where
engaging was automated and disengaging was undocumented for a whole phase.

## Decision

### D1 — the watchdog releases a lock that is protecting nothing

A new rule in the watchdog's existing decision, using only evidence it already
gathers:

```text
IF   a lock is held
AND  it was acquired more than LOCK_GRACE_MINUTES ago
AND  observe() finds NOTHING alive for the environments it watches
THEN release the lock.
```

No environment exists, so there is nothing for the lock to serialise against.
The grace period is what separates this from a cycle whose `terraform apply` has
not created its first resource yet — the watchdog already has that constant and
already uses it for the same kind of question.

**It does NOT ask Actions whether the run is alive**, and that is the point. The
watchdog's header says it decides "without asking Actions anything", and it is
the out-of-band half of a guarantee whose in-band half already depends on
Actions being up. A lock-release path that needed the Actions API would fail in
exactly the outage the watchdog exists to survive.

**The daily counter is not refunded.** `decide_launch()`'s reasoning holds and
this ADR does not reopen it.

### D2 — the manual recovery is documented, because D1 is not immediate

The watchdog runs on a schedule, so D1 shortens the window rather than closing
it. Somebody will still want the button back now, and `infra/self-service/README.md`
gains the command beside the kill switch's, for the same reason that one is
there: engaging a control is automated, releasing it is a decision, so it stays
manual — but manual and *undocumented* are different things.

```bash
aws dynamodb delete-item \
  --table-name aws-devops-sdet-demo-self-service-control \
  --key '{"pk":{"S":"lock"}}'
```

### D3 — the coupling that caused this is written down

`ttl_minutes` is now load-bearing in two directions and its description says only
one of them. It must **exceed** the sum of the job timeouts, or the watchdog
tears down a cycle that is still working. It is also the **ceiling on how long a
stranded lock keeps the button shut**, so raising it has a cost that has nothing
to do with the cycle's length. Both belong in the variable's description, where
the next person to change the number will read them.

## Consequences

- The watchdog gains a reason to release a lock that is not "the blunt teardown
  finished". That is a second path to the same write, and the two must not
  disagree; the rule above is narrow enough that they cannot both apply — one
  requires something alive, the other requires nothing alive.
- A cycle whose apply is slower than `LOCK_GRACE_MINUTES` and which has created
  no billable resource yet would be misread as dead and have its lock released.
  Whether that is reachable depends on the grace value against a real apply's
  first-resource time, and **this ADR does not claim it is not** — it is the
  thing to measure before implementing, not after.
- Not fixed: a `startup_failure` still consumes a launch. Three a day means the
  third failure of the day closes the public path until UTC midnight with
  nothing running and nothing to see. Named, and left.
- The implementation is a Python change in `infra/self-service/src/`, a
  `make self-service-package`, and an apply of a permanent level. None of it is
  in this commit, and the ADR is Proposed rather than Accepted until it is.
