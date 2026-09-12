# ADR-0086: What the page says while a cycle is running, and the six things it got wrong

## Status
Accepted (Phase 40, 2026-09-12). Reverses the premise of **ADR-0077**'s D4
narrowing, turns **ADR-0083**'s union into a sum, and removes the phase binding
**ADR-0068** made unsatisfiable. Narrows **ADR-0062 D1**: *published by the run
in flight* is not the same question as *still true*. Does not touch ADR-0026's
rate budget, ADR-0043's per-step bindings or ADR-0076's shelf life.

## Context

One self-service cycle was launched to look at the page rather than at the
pipeline — [#34641497290](https://github.com/UVE-QA/aws-devops-sdet-demo/actions/runs/34641497290),
2026-09-11, 52 minutes, six jobs green, both environments verified destroyed
afterwards. The pipeline did everything it claims. The page said six things that
were not true while it did, and the owner caught two of them from a screenshot
before this file did.

**1. `created`, over resources that did not exist.** At 19:57, two minutes into
the stage apply, the board said *RDS PostgreSQL — created* and *Secrets Manager —
created*. The document behind it:

    stage.rds      measured    2 of 2 observed complete   (of 4 blocks)
    stage.secrets  measured    1 of 1 observed complete   (of 2 blocks)

The subnet group and the security group had finished; the database had not
started. `measured` from a partial fold means *everything that has started has
finished*, which ADR-0077 recorded as correct and not a defect — and it is
correct, as a statement about the fold. Drawn as the word **created** over a
picture of a database, it is a lie, and it was on the board for six minutes of
every apply this project has ever run.

ADR-0077 said the denominator did not exist:

> `resources_observed` is not how many resources a node has. It is how many have
> **started** [...] **Nothing knows how many there will be until the apply is
> over**, which is what *being created* means.

The first half is true and the conclusion is false. `terraform apply -json
<saved plan>` emits one `planned_change` per resource INSTANCE — `count` and
`for_each` already expanded — and emits every one of them **before the first
`apply_start`**. It is in the fixture this repository has had since Phase 20b:
`tests/fixtures/timeline/cases/apply-from-plan` folds four `planned_change`
events, `gamma[0]` and `gamma[1]` among them, ahead of any work. The total was in
the stream the whole time and nothing read it.

**2. The map went to sleep between two jobs of one cycle.** At 20:09:53, with
forty minutes of the cycle left, every qualifier on the map went out at once:
`from the previous run` off the suites, `these figures are from the cycle before
this one` off both teardowns, and the sentence above the map dating the running
cycle as *the last cycle that finished*. The panel two inches above had it right
in the same second — *Run #20 is queued and has not reported yet*.

`figuresAreOlder()` named two statuses, `in_progress` and `waiting`. A run
between one of its own jobs finishing and the next leaving the queue is
`queued`, and a self-service cycle has four such gaps. The page reads GitHub
every 148 s, so the window is most of each gap.

**3. prod read UP, with a live link, while it was being deleted.** The owner
sent the screenshot: badge **UP**, a link to `https://app.demo.uveapp.net`, and
underneath it the run panel showing `destroy-prod / destroy` five minutes into
`Destroy ALB first`. The load balancer behind that link was already gone.

The staleness rule could not see it. It asks whether the newest run has reported,
and here the newest run *is* the one that reported — from the job that built the
thing this job is now deleting. Both halves of the page had the answer and
neither could use it: the panel knows what a state word means, the map knows
which job of the run in flight is bound to `destroy.prod`, and nothing carried
that one fact across.

**4. Sixteen minutes of teardown that took eleven.** The owner again, on the
Destroy phase: *16 min isn't real time — probably coupled with other count*. It
was. Phase 8 binds two jobs and the clock ran from the first one's start:

    destroy (stage)     20:23:56 → 20:33:08
    hold (five minutes) 20:33:12 → 20:38:21     <- not teardown
    destroy-prod        20:38:25 → still going

ADR-0083 chose the union deliberately, so the at-rest figure would measure what
the live clock measured. The two agreed. They were both counting a hold as
teardown, and at rest the same phase read *21m 59s* over the same eleven minutes
of work.

Beside it sat the second half of the same defect: `last time 7m 43s`, where
7m 43s was **this** run's stage teardown, published twenty minutes earlier by a
job that had already ended. `last time` was hung on *is a run in flight*, which
is a question about the page, not about the figure.

**5. A cycle that had not finished, dated as the one that finished.** The estate's
opening line read *measured by the cycle that finished 2026-09-11 — so they are
the previous cycle's*, three lines above a row header reading *these figures are
from the cycle under way*. Both sentences were generated, and they contradicted
each other, because the date came from the newest RECORD and a record is
published when a JOB ends.

**6. `approve`, in a pipeline where nobody approves.** The map drew phase 5 —
*a human, in the prod environment* — as **done**, and the node as *finished in
this run*, in a cycle no person touched. The `prod` GitHub environment carries no
required reviewers; the rule was taken off in **ADR-0068** in Phase 33, and that
ADR listed what it cost, first, in its own Context:

> lost      the `approve` in `deploy -> test -> approve -> promote -> destroy`.

The phase binding was `when: waiting`, which is satisfied by *the run is waiting
for review*; with no reviewer rule a run never waits, so the binding fell through
to its other branch and read `finished`. Six days earlier **ADR-0085** had built
a gate to make three copies of the verb chain agree — and its first run caught a
copy that had dropped `approve` and put it back. A check that one fact is stated
identically in three places cannot tell you the fact is false. It made the page
more consistently wrong, which is exactly what it is for and exactly why it is
not enough.

## Decision

**D1. A run is in flight until it is `completed`.** `figuresAreOlder()` and
`bindingState()` ask that, rather than listing the statuses a run has while a job
of it is moving. The list was never the question; *has this finished* is.

**D2. The denominator is the plan.** `fold-timeline.py` collects every
`planned_change` into `planned`, `node-states.py` classifies those addresses by
the same four-bucket rule as everything else and publishes
`resources_planned` per node, and a node is `measured` only when as many
instances have finished as the run said it would create. The tile draws
`2 of 5 created` and the bar is a real proportion of a number that does not grow.
`null` where a stream carried no plan, and there the wording and the
indeterminate bar of ADR-0077 stand unchanged — `null` and `0` are different
answers and the join keeps them apart.

The page carries the same test a second time: a tile never says `created` while
its own document names more planned than complete. The join can only be right
about documents it wrote; this covers the ones already in the bucket.

**D3. An environment a job is deleting says so, in both halves.** The map owns
the binding from job to environment, so the map answers the question — and sends
the answer to the panel through a `cycle:teardown` event, the mirror of
`cycle:observed` and carrying as little: an environment and a timestamp. The
panel decides what it means: badge **being destroyed**, the reading marked as
taken before the teardown began, and no link to an application that is being
dismantled. The map reads its own conclusion back through the panel's word, so
the badge and the row still cannot disagree.

**D4. A phase's clock counts work, never the gap between two jobs.** The live
clock adds the finished bound jobs' own spans and ticks from the running one's
start; the merged record adds the two published spans instead of spanning them.
Both ends are kept for reference. ADR-0083's principle — the two numbers must
measure the same thing — is unchanged and is now satisfied over something true.

**D5. A figure is labelled by the run that published it.** `last time` appears
only when the record names a run other than the one in flight. And while a cycle
is under way, the map's opening sentences date the PUBLISHING rather than
claiming a cycle finished: *a cycle is under way; the newest figures below were
published 2026-09-11, and each row says whether what it carries is this cycle's
or the one before it.*

**D6. The verb chain drops `approve`, and the phase stays on the map saying why.**
Three copies, all three rewritten together and still under ADR-0085's gate:

    deploy -> test -> promote -> destroy

Phase 5 declares `never_runs` instead of a `live` binding — a phase that cannot
run says so and says what took it away, and the generator refuses a phase that
declares both. It is drawn dashed, with no clock and no verdict, carrying the
sentence in full; its node reads **removed** through a new `observer: "nothing"`,
which is a different statement from `observer: "actions"` — that one says the
step runs and no timeline can carry it, this one says there is no step. Deleting
the phase was the alternative and it is worse: a pipeline that never had an
approval gate and one that lost it look identical on a map that draws neither.

## Consequences

- **A gate that proves consistency proves nothing about truth.** ADR-0085 is kept
  and its Consequences now say this out loud. It is worth what it costs — it
  caught a real drift within an hour — and it cannot ever be the thing that
  makes a claim true.
- `tests/fixtures/live-state/phases.json` is a FROZEN snapshot and still carries
  the approval's two `when: waiting` cases. That path is now unreachable from the
  live map, and the code stays: a reviewer rule can be put back in the GitHub UI
  in a minute, and unbound code that is exercised is cheaper than code that is
  silently missing. `refresh.py` would drop both cases; read the diff before
  running it.
- **The partial document is now a source of a drawn NUMBER**, not only of a word.
  `resources_planned` comes from the same fold on the same runner, so nothing new
  is trusted — but a plan that changes mid-apply (a `-target`, a retried job with
  a different plan) would move the denominator under a bar. The bar is drawn from
  one document at a time and the shelf life of ADR-0076 still applies.
- **The `cycle:teardown` event is the first message the map sends the dashboard.**
  It is one-way, carries no identifiers, and fires on every paint including the
  quiet ones — a teardown ending has to be as loud as a teardown starting.
- Two new gates hold the new numbers: `synthetic-partial` in
  `tests/fixtures/node-states/` is a fold taken mid-apply and is the second
  hand-written case in this repository, and `check-page-inflight.mjs` gains *a
  node short of its plan says how many of how many*, which refuses to pass if the
  fixture ever stops containing such a node.
- `break-phase-span-merge.sh` asserts the SUM now: 678 s + 725 s = 23m 23s, where
  the union of the same two spans reads 32m 8s. The 525 seconds between them are
  the hold, and the break test names them.
- **Two break tests have stopped biting, and it is not this ADR that stopped
  them.** Run against the previous commit as a control:
  `break-estate-hoisted-note` is 3 of 4 and `break-page-inflight-sequence` is 5
  of 7, and both were recorded green when they were written. The variants that
  no longer reproduce anything all need the same thing: an environment the run in
  flight is touching, drawing a figure from the cycle BEFORE it. The in-flight
  fixture stopped containing one when ADR-0076's progress feed arrived — a node
  the cycle is building shows what the cycle has done, not a leftover — so the
  page can no longer be made to commit the defect those variants describe. The
  gate is not wrong and the claims still hold; what is missing is a fixture state
  where a run touches an environment it is NOT rebuilding, which is what a
  self-service cycle does to prod for its first fifteen minutes. Named here,
  queued, not fixed in this pass.

- Nothing in this ADR was found by a gate. All six came from watching one cycle,
  and two of the six came from the owner looking at the screen. That is the same
  finding as Phase 39's and it is the reason a cycle is watched at all.
