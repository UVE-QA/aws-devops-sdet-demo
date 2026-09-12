# Phase 40 — Six things the page said while a cycle ran

**2026-09-11 → 2026-09-12**, one session.
**ADR-0086**, one record, six decisions.

The cycle was launched to watch the PAGE, not the pipeline — the owner's words
were *lets run e2e test and look what we have and what needs improved*. The
pipeline did everything it claims. The page said six things that were not true
while it did.

## The cycle

```text
#34641497290  2026-09-11  success  52m  launch, promote, destroy, hold,
                                        destroy-prod, release-lock — six green
```

Both environments verified `destroyed` afterwards, both progress documents gone,
≈ $0.09 by the page's own fold. Snapshots of all five parts were taken every
75 s through the whole cycle, which is how most of this was seen at all.

## What the page got wrong

**`created`, over a database nobody had started building.** Two minutes into the
stage apply the board said *RDS PostgreSQL — created*. Behind it: `measured`,
two of two observed complete — the subnet group and the security group. The
database instance had not started. Same for Secrets Manager at one block of two,
and for the ALB at two of five during prod's apply.

ADR-0077 had looked straight at this in Phase 39, called it *not a defect*, and
concluded that **nothing knows how many there will be until the apply is over**.
That conclusion is false, and the counter-example was already in this
repository's fixtures: `terraform apply -json <saved plan>` emits one
`planned_change` per resource INSTANCE, `count` and `for_each` expanded, before
the first `apply_start`. `tests/fixtures/timeline/cases/apply-from-plan` has
folded four of them since Phase 20b. The denominator was in the stream the whole
time and nothing read it.

**The map went to sleep four times per cycle.** At 20:09:53, with forty minutes
of cycle left, every qualifier went out at once and the text above the map dated
the running cycle as *the last cycle that finished*. GitHub reports a run as
`queued` between one of its own jobs ending and the next leaving the queue;
`figuresAreOlder()` named `in_progress` and `waiting` and not that. The panel two
inches above had it right in the same second: *Run #20 is queued and has not
reported yet*.

**prod read UP, with a live link, while it was being deleted.** The owner's
screenshot, five minutes into `Destroy ALB first`. The staleness rule asks
whether the newest run has reported — and here the newest run *is* the one that
reported, from the job that built what this job is now deleting. Both halves of
the page had what was needed and neither could use it.

**Sixteen minutes of teardown over eleven minutes of work.** Also the owner:
*16 min isn't real time — probably coupled with other count*. Phase 8 binds two
jobs and the five-minute hold sits between them; the clock ran from the first
job's start and the at-rest record spanned the same way, by ADR-0083, on purpose,
so that the two numbers would agree. They agreed. Both counted a hold as
teardown.

**`last time`, on a figure this run published.** 7m 43s was this cycle's stage
teardown, twenty minutes old, labelled as the previous cycle's — because the
label asked *is a run in flight*, which is a question about the page rather than
about the figure.

**`approve`, with nobody approving.** Phase 5 read **done** and its node read
*finished in this run* in a cycle no person touched. The `prod` environment
carries no required reviewers: ADR-0068 removed the rule in Phase 33 and listed
it, first, under what that cost. Six days ago ADR-0085 built a gate to keep three
copies of the verb chain identical, and its first run caught a copy that had
dropped `approve` — and put it back.

> A check that one fact is stated identically in three places cannot tell you the
> fact is false.

## What was done

Six decisions, all in ADR-0086: a run is in flight until it is `completed`; the
denominator is the plan; an environment a job is deleting says so in both halves,
through the map's first message back to the dashboard; a phase's clock counts
work and never the gap between two jobs; a figure is labelled by the run that
published it; and the chain is now `deploy → test → promote → destroy`, with
phase 5 kept on the map declaring `never_runs` and saying what took it away.

Deleting phase 5 was the alternative and it is worse: a pipeline that never had
an approval gate and one that lost it look identical on a map that draws neither.

## What holds it

- `synthetic-partial` — a fold taken mid-apply, the second hand-written fixture
  in this repository, holding the exact shape that put `created` over a database:
  four planned, two complete, nothing in flight.
- `check-page-inflight.mjs` gains *a node short of its plan says how many of how
  many*, which refuses to pass if the fixture stops containing such a node.
- Four timeline fixtures now name their planned count; `null` where a stream
  carried no plan, which is a different answer from zero.
- `break-phase-span-merge.sh` asserts the sum — 678 + 725 = 23m 23s — where the
  union of the same two spans reads 32m 8s. The 525 seconds between them are the
  hold.
- `break-run-in-flight-statuses.sh`, six variants: the run moved through
  `queued`, `waiting` and `requested`, and the old two-status predicate restored
  with the run `queued` — seven stage nodes printing undated figures, the page of
  20:09 reproduced. The verification cycle's own sampling missed that gap by
  seconds, so the fixture is what holds it.
- `make gates` 13/13, the three browser gates green, contrast unchanged.

## The verification cycle

[#34661102791](https://github.com/UVE-QA/aws-devops-sdet-demo/actions/runs/34661102791),
2026-09-12, six jobs green, both environments verified `destroyed`, ≈ $0.09.
Watched against the published page, all five parts every 75 s. What it showed,
in the order it happened:

```text
00:20  stage.rds   being created · 2 of 4 created     (would have read `created`)
       stage.secrets                1 of 2 created
       stage.alb                    2 of 4 created    - four, not five: stage has
                                                        no HTTPS listener, and the
                                                        plan knows that
00:25  all seven stage nodes `created`, once the plan and the fact agreed
00:33  prod.alb    2 of 5 created                     - five here, same code
00:47  stage       BEING DESTROYED, no link, `observed before that began`
01:00  prod        the row and all eight tiles grey, on a FRESH load
01:01  phase 8     9m 42s                             (the old clock: 17m 01s)
       phase 2     7m 39s, with no `last time` on it  - this run's own figure
```

One defect found by the cycle and fixed inside it: the panel's badge went to
BEING DESTROYED while the seven tiles under it stayed at full colour, because
the map's copy of the environment list was the one built before it answered.
Thirty seconds of that on every fresh load; the dashboard now hands the map its
own answer back on the same render.

One left open, and it is the same shape one layer up: for one read window after a
cycle ENDS, the sentence over the map and the estate's caption can disagree —
*at rest* against *a cycle is under way*. Both are generated from
`figuresAreOlder()`, both are in the redraw signature, and they still came apart
once, for about ninety seconds. Not reproduced since; named rather than guessed
at.

## Still open, from the same cycle

The owner's list, not yet done: the run panel showing `Post …`/`Complete job` for
every finished job; the two suites self-service deliberately does not run, drawn
in the vocabulary of a lost report; the `Recent lifecycle runs` heading, broken
when Phase 39 flattened it out of a `<details>`; the ECS stability wait counted
as Provision; both environments yellow `UNKNOWN` while an apply is visibly
building one; the cost box carrying stage alone mid-cycle. And the board going
dark as a teardown proceeds — the mirror of what Phase 39 built for the apply,
which the same `planned_change` work now makes cheap.

**Nothing here was found by a gate.** All six came from watching one cycle, and
two of the six came from the owner looking at the screen — which is the same
finding as Phase 39's, one phase later.
