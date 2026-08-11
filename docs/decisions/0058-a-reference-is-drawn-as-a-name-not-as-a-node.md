# ADR-0058: A reference is drawn as a name, not as a node

## Status
Accepted (Phase 24, 2026-08-11). Implemented in the same session: the page
draws three contours, `phaseNodes()` returns a phase's own steps only, and
`scripts/check-live-state.mjs` gains the claim that follows from it.

Implements **ADR-0054** D1, D3, D4, D5 and D6, and finishes the composition
those decisions re-opened. Narrows **ADR-0056**'s second sentence — a phase
draws only what it `creates` — to: a phase draws no estate node at all, and
names every verb it carries. Supersedes **ADR-0047 D1**'s placement of the
permanent levels under a cut, which ADR-0054 D5 had already retired in
principle. Leaves **ADR-0039 D2b**'s second half, **ADR-0049 D6** and
**ADR-0051 D2** untouched; the last of them is the reason this ADR exists.

## Context

ADR-0054 named three contours and put the model for them in the data; Phase 22
built the data and deliberately did not draw it. So for one phase the page ran
on a compromise: a phase RESOLVED the estate nodes it `creates` and drew them
as children, which kept the geometry identical to schema 2 while the model
underneath it had already changed.

The compromise carried the defect the model was written to remove. `phaseNodes()`
was the single read site for the map, the paint pass, the text under the cut and
the run-layer state machine — and an estate node reached through it was handed a
RUN-LAYER state. That is the one source **ADR-0051 D2** forbids re-deriving an
observation from, and it is how `prod.rds` came to stand at full colour with the
previous cycle's figures for twelve measured minutes while prod was being
deleted: the destroy phase could not reach it, so nothing unlit it.

The open question was never whether to separate the contours. It was what a
phase says about a noun it no longer contains.

## Decision

### D1 — A phase draws its own steps; what it touches is NAMED beside them

`phaseNodes(p)` returns `p.nodes`. Nothing resolves, nothing is inherited by a
noun, and two phases — `Apply — stage` and `Apply — prod` — draw no node of
their own at all. That is not a hole. An apply IS the creation of the nouns it
names, and the line naming them is the whole content of the card.

The line is text, not boxes, and the difference is the point: a box inside a
phase means containment, and containment is exactly what ADR-0054 D2 took away.

### D2 — The reference is rendered from BOTH ends, out of one array

A phase names what it touches; an estate node names the steps that touch it.
Both are built from the same `touches` array in one pass (`useTouches()`), so
the two accounts cannot drift. This is the property nesting could not offer and
the reason D2 of ADR-0054 preferred a reference: `stage.rds` is created by one
step, provisioned by a second, asserted against by a third and destroyed by a
fourth, and on its own card all four are visible at once.

### D3 — ADR-0056's `creates`-only rule was about DRAWING, and it retires with drawing

ADR-0056 restricted a phase to its `creates` touches because counting every verb
made the quality gate cross `WIDE_AT` and took the map from ten columns to
eleven. That was a measurement of boxes. A named reference costs a line of small
text, so the restriction has no subject any more and every verb is named.

The closed vocabulary itself — `creates, pushes, provisions, asserts,
destroys`, a sixth is a red build — is unchanged and still enforced in the
generator.

### D4 — The estate contour is drawn at the map's floor, not the card's

`.estate-set` packs at `--node-min`, the map's legibility floor, and not at
`--card-min`, which the permanent and outside cards use. These are the same
objects the map used to draw; resizing them on the way across would have been a
second opinion about how big a resource node is, and this repository has paid
for two of those.

### D5 — The gate checks the consequence, not the implementation

`scripts/check-live-state.mjs` gains claim 4: **no estate id may appear in the
run layer's output at all**, checked against every case rather than against a
case written for it. Two refusals keep it from holding vacuously — a snapshot
with no `estate`, and an `estate` holding no nodes.

Claim 4 is not covered by the gate's existing both-directions comparison, and
the break test says so rather than assuming it: reverting `phaseNodes()` alone
fires both, so the second break also writes the seven resource nodes back into
an expectation. With the case agreeing with the machine, `compare()` is silent
and claim 4 is the only thing that speaks.

## Consequences

- `layout.columns` falls from 10 to 8 and `layout.wide` is empty. Both are
  computed; the two wide phases were wide because of resource nodes that left.
- Two of 20m's three findings are now unrepresentable rather than fixed, which
  is what ADR-0054 predicted. The node renderer cannot consult the run layer
  for a noun because the run layer no longer holds one.
- **The contrast gate's ancestry is the map's, and there is now a second one.**
  `assets/contrast-contract.json`'s `chain` is `main > .cycle > .phase > .set`;
  estate nodes are drawn under `.contour > .estate-env > .set.estate-set`. No
  new node STATE appears — the six the contract measures are the six the page
  draws — and no ancestor in either chain paints a background, so the computed
  colours should be identical. Should is not measured. Supporting two chains is
  a schema change to the contract and a change to the script that reads it, and
  it is written down here rather than smuggled into this phase.
- Every layout figure in ADR-0050 and ADR-0052 is retired by ADR-0054 and has
  NOT been replaced by this session: `make measure-page` needs the pinned
  browser, which is on the devbox.
- Four `live-state` cases lost their inherited resource nodes. Their notes were
  rewritten by hand to say what they now assert, because a case whose data
  changed and whose sentence did not is a document that has gone stale inside a
  gate.
- No AWS call, no cycle, nothing applied. The published page changes, so the
  next push republishes it.
