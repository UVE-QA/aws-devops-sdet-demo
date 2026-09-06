# Phases 34–36 — What a live cycle found that no gate could

**2026-09-06**, continuing the session that began 2026-09-05 and crossed
midnight. **ADR-0069**, **ADR-0070**, **ADR-0071**.

Three cycles were run for real. Everything below was found by running them and
by a person looking at the page while they ran; **the gates were 12/12 green
throughout and found none of it.**

## The cycles

```text
ss-4dbd0034  startup_failure   reusable workflow permissions
ss-3ef2676c  failure           hold job: OIDC identity
ss-2dda62c1  success           first clean public cycle, countdown held live
owner-232224 failure           watchdog ate a live stage; prod left running
by the owner success           all six jobs, nothing left behind
```

## Phase 34 — ADR-0069, a lock that protects nothing

A `startup_failure` strands the lock and consumes a daily launch. `release-lock`
is a JOB running `if: always()`, and `always()` cannot run when GitHub rejected
the file before any job existed. The watchdog does not help either: it reclaims
ENVIRONMENTS and that run created none.

Smaller than it first looked — `lock_is_expired()` lets the next press take over
once the deadline passes — but the button stays shut for a full TTL while
protecting nothing. **ADR-0068 made that worse without noticing**, raising
`ttl_minutes` 90 → 150 so the TTL would exceed the five job timeouts, and
silently lengthening the stranding window by an hour.

D1 (the watchdog releasing a lock when nothing is alive) is **not implemented**.
D2 and D3 are: the manual recovery is documented beside the kill switch, and the
variable now states both directions it is load-bearing in.

## Phase 35 — ADR-0070, a stale reading is a direction

The owner asked why every estate card was lit "as if they already existed" while
a cycle was starting. Nothing existed — a sweep returned 0 RDS, 0 ALB, 0 ECS. The
panel three inches above read UNKNOWN; the cards contradicted it.

`envTense()` returned `unknown` for any stale observation, and `unknown` renders
lit. Not only in flight: on the at-rest fixture, with both environments
**verified destroyed** and the observation seven hours old, all eight nodes came
back `node measured` and zero carried `gone`.

**A recorded decision said the opposite** and was narrowed rather than ignored:

> The map is not entitled to a firmer answer than the panel gives — so a stale
> `destroyed` must not grey the map.

Right principle, inverted application. It assumed grey means *destroyed*; this
page's own CSS says `absent` and `gone` look alike because what a reader needs
from both is **do not read this as live** — weaker than `unknown`, not firmer.
Lit is the firmer answer, and lit was being drawn.

A cycle is a transition, so a stale reading keeps its direction. Was destroyed →
not up *yet* → grey. Was up → not gone *yet* → lit. Only one direction was
wrong, so only one gets a name; symmetry would have dimmed a live prod the
moment a teardown started.

**The old rule's second half never held either** — "a stale `up` must not colour
it", while a stale `up` renders lit. The prose asserted a behaviour the code did
not have, and no gate could see it: `page-tense-check` checks the word a function
returns, never what that word is drawn as.

Implemented. 16 cases, 49 → 51 calls.

## Phase 36 — ADR-0071, the page describes a cycle that no longer exists

Two consequences of ADR-0068, both reported by the owner from the live page.

**"The step in flight" leads with steps that landed half an hour ago.** The panel
renders every job in order. With three jobs and one run, the first thing was the
live thing. With six, the live job is last, and the panel opened with
`launch — success · 14m 22s` while `destroy-prod` was running. Worse right after
the hold: the countdown removes itself exactly when the teardown it announced
begins, so the page goes from its loudest element to silence.

**`not reported` is the vocabulary of absence, used for a decision.** A public
cycle deliberately runs smoke only — the destructive regression suite would be
writing to the environment the visitor is watching. The page draws that as *"the
last run here did not report this suite"*, which is what it says when a report
went missing. `not_in_cycle` is the right vocabulary and does not reach: it is a
property of a SUITE, not of a KIND of cycle.

Proposed, nothing implemented. **No fixture can express the new shape** — every
page fixture is built from a cycle with one kind and three jobs — so the fixture
comes first or the fix gets checked against the world that made the bug.

## Four fixes from the previous phase, confirmed on live infrastructure

```text
launch_id empty          Launch='' — the watchdog left stage alone
                         (the day before it deleted a live one after 4 minutes)
contents: write          promote ran to completion; the release tag was created
continue-on-error        the net is in place (not needed this time)
destroy-prod: always()   fired, prod destroyed
```

Plus two from tonight: the quota showed an honest `3 of 3` for an owner-run
cycle, and the estate greyed correctly under a stale destroyed reading.

## Still unexplained, and left that way

The release tag failed with **HTTP 403** on 2026-09-05 and succeeded on
2026-09-06, from the same branch with the same declared permissions and the same
dispatch path. `default_workflow_permissions` is `read` at the repository, there
are no rulesets and no tag protection. Not diagnosed. `continue-on-error` means
it can no longer strand prod either way, which is why chasing it further was not
worth blocking on.

## And session-close was green over three unrecorded phases, again

The check compares the narrative's phase against the newest session file. With no
file for 34–36, both said 33 and agreed — about a record that had stopped. This
is the **second** occurrence in one session, the first having been written up in
the Phase 33 commit. A record that contradicts itself is caught; a record that
ends is not, and nothing here watches for that.

## Validation

```text
make gates                 12/12 green
page-tense-check           16 cases, 51 calls
page-inflight / freshness / contrast / live-state    all pass
cycle 34000704613          6/6 jobs success
AWS after                  0 RDS, 0 ALB, 0 ECS; endpoint gone
control store              lock released; public quota untouched (owner run)
```
