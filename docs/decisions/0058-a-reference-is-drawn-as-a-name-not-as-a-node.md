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

### D6 — The page is 2.9 screens by default, accepted with its figures

Measured on the devbox against the same instrument run on the previous page in
the same session — not against ADR-0050 and ADR-0052, whose figures ADR-0054
retired:

```text
  1920x1080, cuts closed    2039px (1.9 screens)  ->  3116px (2.9)
  1920x1080, cuts OPEN      8682px                ->  7979px
```

The second line is why this is accepted rather than fixed. **The total content
is 703px shorter.** Nothing was added; the estate came out from under a cut,
which is what ADR-0054 D5 asked for, and what grew is the view a visitor gets
without opening anything. The first screen itself is untouched: `p-env`,
`p-arch` and `p-run` sit where 20e.1 put them, and the map's packing is
unchanged at 813.75px in 4 columns.

Compaction was tried first and is in the number above: the environment tag
removed from every node under a header that already says `stage` (ADR-0047 D3),
and the four phase labels under each noun reduced to verb + phase number. It
bought **78px** — one row of tag across four estate rows — because estate height
is rows × card height, the row count comes from the 18.5rem step, and that step
is 20j's measured floor for a name not wrapping (295.58px, re-measured here and
unchanged).

Two levers remain and are DECLINED here with their figures, so that a later
session reverses this against numbers rather than against a feeling:

```text
  permanent back under a cut     ~ -290px   undoes ADR-0054 D5 in the phase
                                            that implements it
  a narrower estate step         ~ -260px   contradicts D4 above and 20j's
                                            measured floor; names begin to wrap
```

Neither reaches 1.9 screens, and together they reach about 2.4. 1.9 was a page
whose nouns were under a cut, which is the arrangement ADR-0054 retired.

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
- Every layout figure in ADR-0050 and ADR-0052 is retired by ADR-0054 and is
  replaced by D6 above and by the packing recorded in the session's log: the map
  at 813.75px in 4 columns with 1304.6px of air, and the floor at 143.69px for
  every word whole and 295.58px for every name unwrapped.
- One broken word survives and is a FALSE POSITIVE: `read-only` in
  `#suites .asserts`. The rule exempts fields marked `overflow-wrap: anywhere` -
  identifiers - and has no concept of a hyphen, so prose breaking at its own
  hyphen reads as a defect. `make measure-page` is a report and is not in
  `assets/gates.json`, so it reddens nothing. Recorded rather than answered with
  a non-breaking hyphen in the data.
- Four `live-state` cases lost their inherited resource nodes. Their notes were
  rewritten by hand to say what they now assert, because a case whose data
  changed and whose sentence did not is a document that has gone stale inside a
  gate.
- No AWS call, no cycle, nothing applied. The published page changes, so the
  next push republishes it.
