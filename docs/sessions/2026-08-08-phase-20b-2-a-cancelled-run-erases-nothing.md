# 2026-08-08 — Phase 20b.2: a cancelled run erases nothing

The consumer half of 20b. The map's nodes now carry what a cycle measured, a run
that did not finish is SAID rather than silently drawn, and every resource a
cycle touches has to land somewhere. Written and gated at **$0**; the cycle has
not run.

## What this session established

**Writing the consumer changed the design of the producer.** 20b.1 published
`timeline/<env>/latest.json` and called it, in a comment, "the map's at-rest
source". Nothing drew it, so the description cost nothing. The moment a page
read it, it was wrong: `latest.json` is overwritten by every run whatever
happened, so ONE cancelled run would have replaced a dated, complete measurement
with a scatter of nodes that stopped mid-apply — and the page would have shown
the difference as absence, for a reason no visitor could see.

That is 20b.1's own claim turned against the page. *A run that dies mid-apply
must not be reported as a cycle that happened* was enforced in the fold and then
thrown away by the publish rule one step later. **ADR-0040** is the fix, and the
second half of it is a trap this repository has been caught by before.

```text
scripts/node-states.py        the join: one timeline onto the map's nodes
scripts/check-node-states.py  the gate
make node-states-check        it, and it runs in ci.yml
tests/fixtures/node-states/   4 cases folded from real terraform runs, 1
                              hand-written and saying so, and a stub topology
```

## Two objects, because there are two questions

```text
latest.json         what happened LAST, any status. Read for its status, never
                    for its numbers
nodes-apply.json    what the last cycle that FINISHED measured, joined onto the
nodes-destroy.json  map's nodes. Published only when the timeline is complete
```

The page draws the second and says the first: *the most recent run did not
finish; the figures below are from the last cycle that completed, dated …* —
which is more informative than either object alone, and is the sentence the fold
has been able to justify since 20b.1 with nowhere to say it.

It also gives 20b.2's live break test somewhere to be SEEN. A cancelled run
publishing INCOMPLETE stops being a JSON object someone has to fetch and becomes
a line on a public page.

## The join is on the runner, not on the page

The obvious home for "which resource belongs to which node" was the page, which
already fetches `topology.json`. It would then have existed in JavaScript there
and in Python in whatever gate checked it — the shape that cost this project a
scan of the wrong image, when `docker compose config --images app` filtered by
service on the devbox and ignored the filter on the runner from a byte-identical
recipe.

So the rule lives once, in Python, and the page is left a renderer:

```text
a node        the address is in some node's members, FOR THIS ENVIRONMENT, with
              every [...] stripped first. The environment filter is not
              tidiness: stage and prod are the same modules in two state levels
              and hold identical member addresses, so an unfiltered index would
              light half the map from the other environment's cycle. The stub
              topology carries a prod node with stage's members precisely so
              that removing the filter goes red
the teardown  action delete. That node stands for a whole state level and has no
              member list, so a delete is matched by environment
not shown     assigned to a group ADR-0039 D1 deliberately does not draw
unknown       nothing claims it. Printed in the apply log, carried onto the
              page, counted by the gate
```

## The module question, answered before the cycle rather than during it

20b.1 left one piece of Terraform's schema read from the documentation: what
`hook.resource.module` and an `addr` look like inside a module. Every resource in
`infra/` is inside one, so a wrong guess would have lit no node at all — and the
plan was to find out during the billable run.

It did not need to be. A local module holding `terraform_data` is as real a
terraform run as the other fixtures and costs the same nothing, so
`tests/fixtures/timeline/cases/apply-module` was added to `generate.sh` with
three address shapes:

```text
module.child.terraform_data.only      a plain resource inside a module
module.child.terraform_data.many[0]   count INSIDE a module - what
                                      aws_subnet.public actually is
module.pair[0].terraform_data.only    count on the MODULE. infra/ has none
                                      today, and a normalisation rule written
                                      for a shape nobody exercised is the class
                                      of thing this repository breaks on purpose
```

Its expectation was a PREDICTION, written in a chat session with no terraform on
it, and it named the exact address strings. Run on the devbox against terraform
1.15.8 it held to the character:

```text
addr    module.child.terraform_data.only        fully qualified by the module
        module.pair[0].terraform_data.many[0]   the MODULE's index as well as
                                                the resource's
module  module.pair[0] — redundant with addr, which is why the join reads addr
        alone. Empty at the root
```

The six existing fixtures regenerated to identical expectations and identical
event counts — 16, 15, 14, 10, 13, 13, as in 20b.1. The general form is worth
keeping: **a question about a tool's own output is usually answerable offline,
and answering it before the billable run turns a discovery into a
confirmation.**

## Smaller things, each of which would have been found late

```text
MAXDUR        every bar on the map was scaled by the constant 261 - a figure
              measured once by hand and written into the page that ADR-0039 made
              generated. Now computed from whatever cycle is on the page
step binding  the live pulse binds a phase to a workflow STEP, because every
              workflow here has one job. A renamed step would break it silently,
              so generate-topology.py REFUSES a binding naming a step, job or
              workflow that does not exist. Made red both ways
one reader    the map does not call the Actions API. The dashboard script on the
              same page already does, and 60 anonymous requests an hour is the
              whole budget (ADR-0026); the observation is handed over as a DOM
              event, so neither script learns the other's identifiers
the guard     nodeEl gained an `incomplete` branch for a state the publish rule
              currently prevents from reaching it. Kept deliberately: the
              alternative to the guard is not "nothing renders", it is
              `undefined` seconds on a public page - which is what happened in
              20a the last time a state arrived with no branch for it
```

## Two findings in the session machinery, both invisible from inside

**`make session-open` had been naming the wrong phase for a day.** ADR-0033 made
it the thing that prints the phase from the cursor rather than from memory, and
it read *the last data row of the status table* — which is the FURTHEST-OUT
phase, not the next one. Since 20.0 added 20b.2, 20c and 20d in one go it
announced `20d — blocked on 20b` to every session that opened, including this
one. Green, specific, and pointing at the wrong box: the same shape as 20a's
layout check measuring the document instead of the node.

Reading the status column instead does not work in the other direction either —
the first row that is not done is phase 8, open and deliberately parked since
July. The status column says how a phase ended, never which one is next. It now
reads the last `- Next allowed step:` line and the `###` heading above it: the
line the document already writes for exactly this purpose, and the one the
primer tells a chat to name itself from. Derived from the structure rather than
duplicated into a field somebody has to remember to update.

**And the first fix pointed at a different wrong row.** `/^#{2,3} /` looks
obviously right and is an interval quantifier; under the devbox's mawk 1.3.4 it
matched `## Completion criteria & validation` and not one of the thirty-three
`### Phase` headings. Plain `/^### /` is what a phase section is. Caught by
running it rather than by reading it, which is the whole argument for running it.

## What has NOT happened

```text
no cycle          nothing has been applied and no AWS API has been called
no object         no timeline and no node states exist in the bucket
the workflow half if: always() folding a CANCELLED RUN is still proven against
                  fixtures, not against GitHub. That is the live break test,
                  and it is the reason the cycle is worth $0.03
```

## Validation

All of it on the devbox, 2026-08-08, and `ci.yml` green on the push — with the
new step confirmed to have EXECUTED rather than the run merely being green.

```bash
tests/fixtures/timeline/generate.sh   # terraform 1.15.8, 7 cases
make timeline-check                   # 7/7
make node-states-check                # 5 cases, 4 from real terraform runs
make site-data-check
make site-page-check
make docs-check
```

Six break tests, all red, both controls green, tree committed first and exit
codes taken directly rather than through a pipe. Evidence:
`docs/sessions/2026-08-08-phase-20b-2-break-tests.log`.

```text
1  a live binding names a step the job does not have
2  a live binding names a job the workflow does not have
3  the environment filter removed from the node index
4  the index stripping stops seeing count
5  a hidden group forgets which addresses it hides
6  the fixture directory emptied — it refuses rather than passing 0/0
0/6  controls: the untouched tree, before and after
```

Case 3 said more than it was aimed at: the synthetic case reddened too, so the
environment filter is asserted by a hand-written fixture as well as by a real
one.

## Files

```text
scripts/node-states.py                       new
scripts/check-node-states.py                 new
tests/fixtures/node-states/                  new: stub topology, 4 cases, 1
                                             synthetic
tests/fixtures/timeline/generate.sh          the apply-module case
tests/fixtures/timeline/cases/apply-module/  new: expected.json
scripts/generate-topology.py                 live bindings, checked; not_shown
                                             carries its members
scripts/publish-status.sh                    publishes node states, complete only
assets/topology-groups.json                  the live bindings
assets/index.template.html                   the run layer
site/index.html                              rebuilt
site/data/topology.json                      regenerated
Makefile                                     node-states-check
.github/workflows/ci.yml                     node-states-check
.github/workflows/deploy-stage.yml           the join step
.github/workflows/promote-prod.yml           the join step
.github/workflows/destroy.yml                the join step
.github/workflows/self-service.yml           the join step, in both jobs
scripts/session-open.sh                      the cursor, read from the line
                                             that means it
docs/sessions/...-break-tests.log            new: the evidence
docs/decisions/0040-...                      new
docs/architecture.md                         the third source, in full
docs/phase-gates.md                          20b.2 section, cursor row
docs/next-phases.md                          what moved to the $0 half
README.md                                    the CI check list
```
