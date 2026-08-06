# 2026-08-05 — Phase 19d: the record, the lock, and the state lock

19c proved everything it set out to prove and did not close, because cancelling
a run left a state from which the only exit was a human with an AWS credential.
This session decided that state rather than patching around it: **ADR-0036**,
three parts, plus the four "the endpoint says something untrue" items 19c had
deliberately batched.

Nothing has been applied. The live half — a cancelled run that cleans itself up
with nobody in the loop — is the remaining criterion of both 19c and this phase.

## What was actually wrong

Three defects, each green in isolation, combining into one state:

```text
1. the watchdog wrote `destroy_dispatched_at` onto the LOCK, and skipped the
   write entirely when there was no lock. The lock belongs to the LAUNCH: the
   Lambda writes it, release-lock deletes it, a later launch takes it over. So
   the watchdog's memory was stored on a record owned by the thing it exists to
   distrust, and it forgot every dispatch in exactly the case it was written for
2. release-lock deleted the lock without ever asking how destroy went. That did
   not only lose the record - it reopened the button, so the next visitor would
   have spent one of the day's three launches on an apply guaranteed to die on
   the same state lock
3. the recovery written down in watchdog_handler.py - "re-run destroy" - cannot
   work, because re-running destroy takes the state lock first and the state
   lock is what is stuck. Two fifteen-minute timeouts were spent finding that
   out on 19c
```

The observed symptom, `dispatched_destroy` every five minutes with no
`waiting_for_destroy` between, was reproduced here from the OLD logic rather
than remembered from the log:

```text
a cancelled run: resources alive, lock deleted by release-lock
  t+ 0m  dispatched_destroy
  t+ 5m  dispatched_destroy
  t+10m  dispatched_destroy
  t+15m  dispatched_destroy
  t+20m  dispatched_destroy
  t+25m  dispatched_destroy
```

The blunt path is unreachable on that trace at any t. It is not slow; it is
absent.

## The decision (ADR-0036)

```text
D1  the watchdog's record is its own item, `pk = "watchdog"`, scoped by the
    launch ids it acted on and carrying a ttl. `note_on_lock` loses its only
    caller and goes. The decision itself moves to
    infra/self-service/src/sweep.py, which imports no AWS SDK - so the blunt
    path, which costs a launch and fifteen minutes to reach for real, costs a
    dictionary to reach in a test
D2  release-lock reads `needs.destroy.result` and releases only on success. It
    keeps `if: always()`, because it must still run after a cancellation; what
    changes is what it does when it gets there
D3  scripts/break-stale-state-lock.sh, a preflight in destroy.yml AND in the
    self-service destroy job, stage and prod in the same commit. It breaks a
    lock whose holder is this job's own runner user when no other run of the
    repository is in progress, and refuses in every other case
```

The discriminator in D3 is `Who`, not age. Terraform writes `user@host` into the
lockfile; a hosted runner is `runner@…` and this devbox is `ubuntu@…`, so the
check is evidence about the holder rather than a guess about how long an apply
ought to take. An age threshold derived honestly from the workflows would be six
hours, because `deploy-stage.yml` and `promote-prod.yml` declare no timeout at
all.

Rejected, and written down with the reasons: recreating the lock from the
resources' tags (it would be within its deadline, which silences the "alive with
no lock" signal and buys the orphan another 90 minutes), an unconditional
force-unlock, and letting the watchdog delete the `.tflock` object itself.

## Batched with it

All four of 19c's "did not settle" items, because they share one package build
and one apply:

```text
the kill switch reports the `source` it was thrown with, instead of naming the
  budget alarm whichever way it was engaged - which it did every time this
  project parked the endpoint between phases
it refuses GET as well as POST. It used to refuse only POST while the README
  said it "refuses every request", so a parked endpoint went on writing a store
  item per press for anyone who asked. Of the two, the README was right
run_url is removed from the `locked` refusal. It was read in one place and
  written in none: the lock is taken BEFORE the dispatch, and workflow_dispatch
  returns no run id, so there is no moment at which the code could know it
the dashboard adopts ttl_minutes and daily_cap from the endpoint's GET reply
  rather than hardcoding them
```

The kill-switch refusal reports the source and **not** the recorded reason: the
budget path's reason is an SNS message with the account's budget in it, and the
refusal goes to the public internet. Same rule that made the budget email a
secret in Phase 15.

## Findings, three of them from running

```text
- the first version of the D1 assertion asserted `dispatched_destroy` where the
  code correctly answered `within_deadline`. The test had modelled a cancelled
  run that was already past its deadline; a cancellation leaves an environment
  well INSIDE its 90 minutes, and it is the missing lock that makes it an
  anomaly. The test measured the author's assumption, not the code - the same
  shape as a break test that fails to break
- the preflight aborted with `GITHUB_REPOSITORY: unbound variable` under
  `set -u` when run outside Actions. Exit 1, for the wrong reason, with a
  message naming a shell variable instead of the refusal - and outside Actions
  is exactly where someone will run it while debugging a stuck lock
- its positive branch was first measured through a pipe into `tail`, which
  reported `exit=0` over a `terraform: command not found`. The primer has
  carried that trap since 2026-07-28 and it still cost a wrong reading; the
  re-measurement with the output redirected to a file took seconds
- CKV/skip lists, IAM and the table schema all needed nothing: the watchdog's
  policy is already table-wide and the callback role's leading-key condition
  still names `lock` and only `lock`. The one genuinely new permission is
  `actions: read`, on two workflows
```

## Validated in the chat sandbox

```text
tests/unit                     41 passed (28 before, 13 new)
the preflight's five refusals  each fired, output kept:
                                 no lockfile        exit 0, "nothing to break"
                                 devbox holder      exit 1, names both users
                                 a run in progress  exit 1, names the count
                                 no readable ID     exit 1
                                 cannot tell        exit 1, refuses to guess
the positive branch            reaches force-unlock; terraform is not installed
                               in the sandbox, so it finishes on the devbox
```

`terraform fmt`, `tf-validate`, `iac-scan`, `docs-check` and `action-pins` are
the devbox's, per the 19a precedent: an approximate check written in the sandbox
measures the sandbox.

## Cost

**$0 so far.** No AWS API was called by this session. The live break test costs
one cycle of the order already measured — $0.09 and $0.17 — and it spends the
last of today's three launches.
