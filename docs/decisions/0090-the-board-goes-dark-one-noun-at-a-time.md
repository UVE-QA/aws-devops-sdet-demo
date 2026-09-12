# ADR-0090: The board goes dark one noun at a time

## Status
Accepted (Phase 40, 2026-09-12). Completes **ADR-0076**'s live board for the
other direction and narrows the sentence in it that said a teardown has nothing
to publish. Narrows **ADR-0086 D3**: the row-level *being destroyed* stays, and
stops being the only thing a teardown can say. Uses **ADR-0086 D2**'s plan
denominator unchanged.

## Context

ADR-0086 D3 gave the panel and the estate row a word for an environment a job is
deleting. The owner watched the next cycle and said what it looked like:

> прод погас одновременно

All eight tiles went grey in the same instant, at the start of a nine-minute
teardown, and nothing moved again until it was over. What the apply had since
Phase 39 — a board that lights up node by node as Terraform creates them — the
teardown did not have at all, and the page could not have shown it: a destroy
publishes no progress document, because `destroy.yml` never started the watcher.

The reason it never did is written in `self-service.yml`:

> The LAUNCH job only. The teardown job below folds the same way and its join
> names one node, `destroy.stage`, which is not a noun on the estate board - a
> delete is matched by environment and not by address, because the destroy nodes
> are whole levels. There is nothing for a watcher to publish there.

Every clause of that is true about the JOIN, and the conclusion does not follow.
A delete carries an address like any other resource, and that address names a
tile. The join was throwing the information away, not lacking it.

## Decision

**D1. A delete is read twice.** It still belongs to the destroy node, matched by
environment, and `nodes` is unchanged — `destroy.<env>` stands for the whole
level and keeps its own figures. Beside it, `node-states.py` now also matches the
delete by ADDRESS against the same `members` the apply uses, and publishes the
result under a separate key, `deleting`. Two readings of one fact, in one place,
rather than a second rule somewhere else.

**D2. The teardown gets the same denominator as the apply.** The plan of a
destroy names every instance it will remove before it removes any — the
`planned_change` events ADR-0086 D2 already collects — so a tile says
`3 of 4 destroyed` and its bar is a real proportion.

**D3. `destroy.yml` starts the watcher, on the same terms as the apply.** The
composite action of ADR-0076, publish role for the watcher and deploy role for
everything after it, and the stop step AFTER the swap to the publish role —
which is where self-service.yml learned to put it on 2026-09-08, the hard way.

**D4. Four words, and the first one is about AWS rather than about the run.** A
tile the teardown has not reached says **still standing**; one being removed says
**being destroyed** with its fraction; one that is gone says **destroyed —
removed by the cycle under way**. The row's word and the panel's badge are
unchanged, and they now describe something that is visibly happening rather than
standing in for it.

**D5. A record of the apply does not supersede a reading of the teardown.** The
supersede rule of ADR-0076 D6 asks whether the record was published by the run in
flight. In a self-service cycle ONE run publishes both: the launch job writes the
environment's node figures, and forty minutes later the destroy job publishes a
partial reading of itself — same run id, opposite direction. Under the old rule
the second would have been called stale on the strength of the first and the
board would have stayed lit through the teardown. What supersedes a partial
reading is a record of the SAME KIND, so the record now carries its `kind` the
way it already carries `published_by`.

## Consequences

- The estate board is live in both directions, which is what Phase 39 set out to
  build and got half of.
- The record of a teardown grows by one key. It is published, because it is a
  record and that is what happened; the page does not READ it at rest, where the
  estate's word comes from the environment's own observation — AWS answering
  rather than a run claiming.
- `check-node-states.py` compares `deleting` where a case names it, and
  `destroy-cycle` names it. Proven to bite: with the second reading removed the
  gate reports *deleting is named by the case and the join produced none*. It
  used to be a KeyError and a traceback, which reads like a broken gate rather
  than a caught defect; a missing key is a finding now.
- A teardown now writes to the site bucket every fifteen seconds for nine
  minutes, from a job that previously wrote twice. Same instrument, same shelf
  life, same removal at the end, and the same rule that it may never fail the job
  it watches.
- The owner's sentence is the third defect in two days that a gate could not have
  found and a person looking at the screen did. That is not an argument against
  gates; it is the reason cycles are watched.
