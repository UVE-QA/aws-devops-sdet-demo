# ADR-0076: A partial fold is a correct reading of an unfinished cycle

## Status
Accepted (Phase 39, 2026-09-08). Delivers what **ADR-0075**'s Consequences said
it could not. Applies **ADR-0054 D3**'s rule — *a noun is answered by observation
and by nothing else* — in the direction it was written and not against it.
**ADR-0062 D1**'s predicate is reused verbatim. **ADR-0044**'s correspondence is
satisfied without a new prefix. Nothing in `fold-timeline.py` or
`node-states.py` changes.

## Context

ADR-0075 drew the estate as a board of service marks and said out loud that the
thing it was drawn for was missing: the marks do not light up **as each resource
is created**. Node states are published once, by `publish-status.sh`, after
`terraform apply` has already returned, so a whole environment changes at once
when its job ends. What the owner asked for — *"загорается именно в момент
создания, а не когда всё уже поднялось"* — needs a reading taken while the apply
is running, and there was none.

### The reading already exists; nothing was publishing it

`tf-stream.sh` tees terraform's `-json` stdout to a file as it goes, so that file
is always readable and always a **prefix** of the finished stream. Folding a
prefix is not a degraded operation:

* `fold-timeline.py` records a resource whose `apply_start` was never answered as
  `incomplete`, with the timestamp it does have. That branch has existed since
  ADR-0039 for a *killed* apply.
* `node-states.py` reports a node whose members have not all finished as
  `incomplete`, with `resources_complete` under `resources_observed`. Its own
  comment calls the alternative "a plausible-looking half-truth".

Those are exactly the three states a board needs, and the repository already
contains the fixture proving it — `tests/fixtures/node-states/cases/apply-killed`
is one node, `incomplete`, 1 of 2 complete.

    absent from `nodes`   no member of it has started
    `incomplete`, 3 of 8  some member started, not all have finished
    `measured`            every member finished

So the guard that says *"no `.rc` means terraform never returned"* is not weakened
here and is not asked to change. **It is right about what it refuses.** What was
missing is that a reading correct about an unfinished cycle was never published.

## Decision

**D1. A second publisher, and a document that says what it is.**
`scripts/publish-progress.sh` writes `status/progress/<environment>.json`: the
join's own output, wrapped, carrying `partial: true`, the run producing it, and
the moment it was taken. `scripts/watch-progress.sh` runs the existing fold and
the existing join on a timer and calls it. The join rule stays in one place —
a follower maintaining node membership incrementally would be that rule in a
second implementation, which is this project's `docker compose config --images`
trap.

It writes one object and **invalidates nothing**. Thirty invalidations per apply
is a billed request past the monthly allowance, to republish a document that says
`no-cache` and is revalidated at the edge anyway. It also fails at nothing: an
apply must not fail because the instrument watching it did, so every iteration is
wrapped, failures are counted, and the loop exits 0 whatever happened.

**No new prefix.** It writes under `status/`, which `publish-site.sh` already
excludes from its `--delete` sync — so ADR-0044's correspondence holds without a
line anybody has to remember. The checker enforcing that correspondence named one
publisher by hand and would have been blind to this one; it reads every
`scripts/publish-*.sh` now. That is the *same* defect ADR-0044 was written for,
found in the checker written to prevent it.

**D2. The deploy role is not widened.** The watcher needs to write to the site
bucket; the job running the apply holds the deploy role, and this project splits
the credential that can change infrastructure from the credential that writes the
page reporting on it. Adding `s3:PutObject` to a role that can create an RDS
instance for the sake of an instrument was refused.

A background process keeps the environment it was started with. So
`.github/actions/watch-progress` assumes the **publish** role, starts the loop,
and hands the foreground back to the deploy role — the watcher goes on holding
the narrow credential while every step after it holds the wide one. That is a
subtlety, which is why it is a composite action and not six lines in three
workflows: written inline it would be three copies of it, and the day one lost a
line the symptom would be a board that quietly stopped lighting up.

**D3. An apply, and nothing else.** `node-states.py` matches a `delete` by
*environment* rather than by address, deliberately — the destroy nodes are whole
levels, and `destroy.stage` stands for all thirty blocks. A teardown's join
therefore names one node and it is not a noun, so a progress document from one
has nothing to say about any tile on the board. Read anyway, every tile would
report *the teardown has not reached it* for the whole teardown: inert, and said
seven times. The page refuses a document whose `kind` is not `apply`, and the
watcher is wired into the two apply paths only.

**D4. The bar is a count, not a forecast.** `3 of 8 resource blocks` is a fact
about this cycle. A bar against the previous cycle's duration would be a claim
about how long the remaining five take — and would have nothing to say at all on
a first run, which is the objection the owner raised of the prototype. It cannot
lie on a first cycle because it has no history in it, and the sentence beside it
is the same count in words, so the bar adds a shape and never a number.

**D5. This is observation, not the run layer.** ADR-0054 D3 keeps the run layer
away from the estate because it *infers*: a phase is running, therefore its seven
resources might be. This document is Terraform's own event stream and it **names
the resource**. `check-live-state.mjs` is untouched and still fails the build if
an estate id reaches `runLayerStates()`; `n.run` is still cleared for every
estate node.

**D6. A partial reading is read only by the run that wrote it, and the record
supersedes it.** The document is removed when the job ends, but a removal that
failed or an edge that has not revalidated leaves one describing an environment
torn down since. So the page consults it only when it names the run the page is
already watching — ADR-0062 D1's predicate exactly: not *is a run touching this
environment* but *does this document belong to the run in flight*. `flightHere()`
answers `true` when a run cannot be identified, which deliberately equals nothing.

And once `published_by` on a node record names the run in flight, that job has
reported this environment — real durations, real identifiers — and the partial
reading has nothing to add. Without that the board went on saying *being created*
over an environment the same run had already reported complete. It was
`page-inflight-check`'s sequence pass that said so.

**D7. The tile says which cycle it is a reading of, in the DOM.**
`claimFiguresDated()` requires a numeric state drawn during a run to say which
cycle measured it, and read `being created · 2 of 5 resource blocks` as an undated
leftover. It is the opposite — a count taken by the run on the page, seconds ago.
The page sets `data-observed="cycle-under-way"` where it read the document, and
the claim reads that. A gate matching on the wording would be the page's
vocabulary in a second place.

The new claim is two-sided, because the negative half alone is satisfied by a page
that never reads the document — the vacuous green this file has caught in itself
twice. `scripts/break-progress-attribution.sh` runs seven variants.

## Consequences

**The at-rest case turned out to be defended twice, and that is a finding.**
Neither guard removed alone lets a finished cycle's document light the board:
`flightHere()` answers null, and a document naming a run can never equal null. The
first break variant targeted the run-id comparison, passed, and proved a line that
was not protecting the case. It removes both now and says why.

**Not verified live.** Everything here is green against a fixture holding a cycle
mid-apply and against seven break variants, and none of that is a cycle. Three
things can only be answered by running one: whether CloudFront's edge revalidates
a `no-cache` document fast enough for a fifteen-second cadence to be visible;
whether a background process really keeps its credential across a
`configure-aws-credentials` step that replaces it in the foreground; and what the
fold costs on a runner while an apply is competing for it. The first is the one
most likely to disappoint, and the page's own poll interval sits under it.

**The page still polls on its GitHub budget.** The progress document costs no
GitHub API request, so the board could be re-read far more often than the
dashboard's derived interval (ADR-0062 D2, floor 60 s). It is not, yet: two
clocks in one page is a decision of its own and this one is unmeasured. Until it
is taken, the sequence a reader sees is sampled about once a minute — the states
are right and the *animation* is coarse.

`deploy-stage.yml` is deliberately not wired. It is the owner's path, it has the
same three steps available to it, and adding a fourth call before the first has
run once would be three untested copies instead of two.
