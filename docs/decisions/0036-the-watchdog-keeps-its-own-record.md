# ADR-0036: The watchdog keeps its own record, a failed destroy keeps the lock, and a stale state lock is broken by the system

## Status

Accepted (Phase 19d, 2026-08-05). Amends **ADR-0035** guardrails 1 and 5.

Written because 19c pressed the button for real and found a *state* rather than
a bug: recovery from an ordinary cancelled run needed a human holding an AWS
credential. A guardrail whose recovery is manual works only while someone is
watching, and the hours when nobody is watching are the whole reason the
watchdog exists.

## Context

19c cancelled a run mid-apply on purpose, to prove `if: always()` still tears the
environment down. It does. What it left behind was this, in order:

```text
1. the apply is killed. The S3 state lock stays held, and resources that were
   already created never reach the state file
2. `destroy` runs, and dies acquiring that state lock
3. `release-lock` runs anyway - it never asks how `destroy` went - and deletes
   the lock item, correctly by its own rule: the item IS this launch's
4. the watchdog observes live resources and no lock. `lock is None` sends it
   past the deadline check straight to `dispatch_destroy`, which dispatches
   destroy.yml - which dies on the same state lock
5. `dispatch_destroy` records the attempt ON THE LOCK, and returns early when
   there is no lock. `destroy_dispatched_at` stays 0
6. so every five minutes, indefinitely: dispatch, fail, forget. The grace period
   never starts, and the blunt path - written for exactly this case - can never
   engage
```

The log shows the shape with nothing to interpret: two `dispatched_destroy` five
minutes apart and no `waiting_for_destroy` between them. An ALB and an RDS
instance billed throughout. Getting out took `terraform force-unlock` plus three
unmanaged resources deleted by hand.

Three things are wrong here, and only the third was the one anybody noticed.

**The watchdog's memory lives on a record it does not own.** The lock belongs to
the launch: the Lambda creates it, `release-lock` deletes it, a later launch can
take it over. The watchdog only borrowed a field on it. So the watchdog forgets
what it did the moment the launch's bookkeeping breaks — and the launch's
bookkeeping breaking is the entire reason the watchdog exists. Its memory was
coupled to the thing it is there to distrust.

**A failed destroy erases the evidence that anything is in flight.** Worse than
losing the watchdog's record: it also unblocks the button. The next visitor takes
the lock, spends one of the day's three launches, and their apply dies on the
same state lock. The endpoint had entered a state where every press was
guaranteed to fail and to cost the presser their turn.

**The documented recovery cannot work.** `watchdog_handler.py` tells its reader
that after the blunt path the fix is to re-run destroy, "which reconciles what is
already gone". Re-running destroy takes the state lock first, and the state lock
is precisely what is stuck. Two full fifteen-minute timeouts were spent
discovering that the sentence was false. A recovery written in advance is only
worth having if it was written against the failure it names.

## Decision

### D1 — the watchdog's record is its own item, not a field on someone else's

A new item at the permanent level, `pk = "watchdog"`, written and deleted by the
watchdog and by nothing else:

```text
pk             "watchdog"
scope          the sorted, comma-joined Launch tag values it acted on
dispatched_at  when it asked Actions to destroy
ttl            now + 6h, so a forgotten record cannot outlive the situation
```

`destroy_dispatched_at` is removed from the lock. One definition, not two — and
`note_on_lock` loses its only caller and goes with it.

`scope` is what makes the record safe to keep: a record whose scope no longer
matches what is alive is not this situation's record, so the watchdog starts
again rather than inheriting a stranger's grace period. The record is cleared the
moment nothing is alive, so the next launch never meets it.

The gate that says "act now" is unchanged: live resources with **no lock at all**
is still an anomaly that skips the deadline. What changes is that having acted is
now remembered.

### D2 — `release-lock` releases only what `destroy` actually finished

The job keeps `if: always()` — it must still run after a cancellation — but it
now reads `needs.destroy.result` and releases only on `success`. On any other
result it refuses, says why, and leaves the lock in place:

```text
destroy succeeded    release the lock. The environment is gone
anything else        keep it. Something is alive that could not be destroyed,
                     the button must stay shut, and the watchdog needs the
                     record that a launch is in flight
```

Nothing is stuck forever by this: the lock still carries the TTL, an expired lock
can still be taken over, and the blunt path releases it after deleting what the
lock was guarding.

This removes the case that was observed. D1 removes the class — the lock can also
go missing because a human deleted it, which is exactly what 19c's own recovery
did.

### D3 — a state lock left by a run that has finished is broken by the system

`scripts/break-stale-state-lock.sh <environment>` runs as a preflight in both
teardown paths — `destroy.yml` and the self-service `destroy` job — and refuses
in every case where the answer is not certain:

```text
no .tflock object                     nothing to break. Exit 0, the normal path
`Who` is not this job's runner user   REFUSE. A devbox apply writes ubuntu@...,
                                      and a human's lock is never the system's
                                      to break
any other run of this repository is   REFUSE. If something is running, something
in progress                           may legitimately hold it
the lockfile has no readable ID       REFUSE. Breaking a lock we cannot name is
                                      not a controlled operation
otherwise                             print the lockfile in full, then
                                      `terraform force-unlock -force <ID>`
```

The discriminator is `Who`, not age. Terraform writes `user@host` into the
lockfile; a GitHub-hosted runner is `runner@…` and this project's devbox is
`ubuntu@…`, so the check is a fact about the holder rather than a guess about how
long an apply ought to take. A future self-hosted runner with a different user
makes the script refuse — the safe direction.

The two conditions are ANDed on purpose. `Who` alone would break the lock of a
*live* runner; "no run in progress" alone would break a devbox lock while the
owner is mid-apply and the account is otherwise quiet.

The bucket and key are read out of the environment's own `backend.tf` rather than
repeated in the script: one definition, and the script fails loudly if it cannot
find it there.

## Considered and rejected

```text
recreate the lock from the resources' tags when one is missing
  The tags already carry launch id and deadline, so it is possible. It is also
  worse: the reconstructed lock would be WITHIN its deadline, which silences the
  "alive with no lock, act now" signal and buys the orphan another 90 minutes of
  billing. The record the watchdog needs is not the launch's record.

let release-lock always release, and rely on the TTL
  The status quo, and it is what left the button in a state where every press was
  guaranteed to fail. 90 minutes is the bound on a RUNNING launch, not an
  acceptable bound on an endpoint that is broken.

force-unlock unconditionally at the start of every destroy
  Two writers on one state file is a failure this project has never had, and this
  would be a self-inflicted one. A control that cannot refuse is not a control.

break the lock on age alone, above some threshold
  An age threshold is an assumption about how long an apply takes, measured
  against nothing. `deploy-stage.yml` and `promote-prod.yml` declare no
  `timeout-minutes` at all, so the honest threshold derived from the workflows is
  six hours - long enough to be useless. `Who` is evidence; age is a guess.

make the watchdog delete the .tflock object directly
  One S3 delete, and it would work with Actions completely dead. Rejected for now
  because it puts a second implementation of "is this lock stale" somewhere with
  no terraform binary to do it properly, and because the blunt path already
  handles the money in that scenario. The state lock can wait for the next
  Actions run; the ALB cannot.
```

## Consequences

- The watchdog's decision moves into `infra/self-service/src/sweep.py`, a module
  that imports no AWS SDK, for the same reason `control.py` does not: every
  branch — including the one that only happens when the lock is gone — becomes an
  in-process assertion instead of something that needs a cancelled run to see.
  `watchdog_handler.py` keeps observation and execution and stops deciding.
- The control table gains a fourth kind of item. No IAM change: the watchdog's
  policy is already table-wide, and the callback role's leading-key condition
  still names `lock` and only `lock`.
- `release-lock` can now finish green having released nothing, and its output has
  to say so plainly, because "released" and "deliberately not released" are
  otherwise indistinguishable in a passing check.
- `destroy.yml` and `self-service.yml` gain `actions: read`, to see whether any
  run is in progress.
- The preflight runs on **every** teardown, prod's included. Its no-op branch is
  therefore exercised continuously, and that is the branch that must never do
  anything.
- The recovery sentence in `watchdog_handler.py` is corrected rather than
  deleted: re-running destroy does reconcile the state, *after* the preflight has
  cleared the lock standing in front of it.

## Break tests

Nothing here is believed until it has been seen refusing or firing. Three are
in-process and land with this ADR; the fourth needs a real cancelled run and is
the closing criterion of Phase 19c.

```text
1. the record survives the lock         in-process: dispatch, delete the lock,
                                        run again -> waiting_for_destroy, and
                                        after the grace period -> blunt teardown
2. a record from another scope is       in-process: the record names launch A,
   not inherited                        the resources are launch B -> dispatch
                                        again, and the grace period restarts
3. the preflight refuses                all four refusals, on fixtures: no
                                        lockfile, a devbox `Who`, a run in
                                        progress, an unreadable lockfile
4. a cancelled run cleans up with no    live: cancel an apply, then touch
   human in the loop                    nothing afterwards
```

Break test 4 is the one that matters and the one that cannot be faked: this ADR
exists because three things that were each green in isolation combined into a
state none of them could see.
