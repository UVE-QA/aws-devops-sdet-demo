# ADR-0056: A reference carries a verb, and exactly one verb draws

## Status
Accepted (Phase 22, 2026-08-10), and implemented in the same phase.

Completes **ADR-0054 D2**, which made the binding a reference and did not say
what a reference carries. Extends **ADR-0049 D6** — citation by id, with a build
that refuses a citation it cannot honour — to the phase→estate edge. Nothing is
superseded.

## Context

ADR-0054 D2 asks a phase to reference the estate nodes it acts on, and says in
passing that apply, provision, gate and destroy "each say so separately". Read
as a bare list of ids, that model type-checks and cannot be drawn: a node
referenced by four phases belongs to four phases, and the page has no way to
know which one is the box it goes in.

That is not a matter of taste, and Phase 22 found out because it counted. The
quality gate owns four suite nodes and references three estate nodes it asserts
against:

```text
                        own   referenced   drawn if every reference draws
stage-gate               4         3                  7   >= WIDE_AT (6)
```

Seven crosses `WIDE_AT`, the phase takes two columns instead of one, and
`layout.columns` goes from ten to eleven. The map reflows — in a phase whose
plan says in as many words that the page is not touched. Counted that way the
destroy phase reaches seventeen and the total is twelve, not ten.

The missing element was in the data, not in the renderer. A list of ids records
that an edge exists; it does not record what the edge is, and every consumer
then has to guess — which is one definition on four hosts, the shape this
repository keeps deleting.

## Decision

### D1 — A reference is `{node, verb}`, and the vocabulary is closed

```text
creates      this step is why the noun exists
pushes       an artifact goes into a permanent level
provisions   the step puts something into a thing that already exists
asserts      a suite reads it and judges it
destroys     the teardown deletes it
```

Five verbs, listed in the generator. A sixth is a red build, by name:

```text
site-data: REFUSED
phase stage-gate touches stage.alb with the unknown verb 'pokes'.
Known verbs: asserts, creates, destroys, provisions, pushes
```

An open vocabulary would let a verb be invented at the point of use, which is
how `observer` would have gone if ADR-0051 D3 had not fixed its three values.

### D2 — Only `creates` draws

A box inside a phase can honestly mean exactly one thing: *this step is why that
thing exists*. Every other verb is a relationship the phase HAS with a node
somebody else made, and drawing it would put `stage.rds` in four phases at once
— the picture ADR-0054 was written to end, arriving from the other side.

This is a rule about the DATA, not a layout preference. Phase 23 may decide to
draw an `asserts` edge as a line, a tint or nothing; it cannot decide it by
accident, which is what an unlabelled reference offered.

### D3 — One resolver, and every read site goes through it

```text
site/index.html    phaseNodes(p) - the map, the text under the cut, the paint
                   pass and the run-layer state machine
node-states.py     phase_of() applies the same rule to decide which phase a
                   measured resource's duration is reported under
```

The join has to agree with the page for a reason stronger than tidiness: a
phase's duration is measured over the nodes a reader is looking at inside it, so
a resource resolved into one phase in Python and drawn in another in JavaScript
puts a real number under the wrong heading. `index_members()` is the other half
and does not resolve at all — members are a property of the estate node, and a
touch is a reference, never a node the phase owns.

### D4 — The frozen snapshots keep every verb, not only the one that draws

`tests/fixtures/live-state/phases.json` is a snapshot of what the run-layer
state machine reads. It carries all five verbs on purpose. Pre-filtered to
`creates` it would ASSERT this ADR instead of testing it; with every verb in the
file, a resolver that forgets to filter lights fifteen resource nodes in the
teardown phase and five of twelve hand-written cases say so — measured by
deleting the filter and running the gate.

### D5 — The geometry is a measurement, not a hope

Under D2 the schema-3 map draws, phase by phase and in order:

```text
1, 7, 1, 4, 1, 8, 2, 2      wide = [stage-apply, prod-apply]      columns = 10
```

Identical to schema 2, node for node and in the same order — checked by lifting
`phaseNodes()` out of the built page and comparing its answer against the last
schema-2 `topology.json`. Any future change to D2 is a composition change and
belongs to a phase that says so.

## Consequences

- The page keeps one function where it would otherwise have had four opinions.
  `phaseNodes(p)` is the only place the two contours are joined, and it is
  inside the block `scripts/check-live-state.mjs` lifts, so the gate runs the
  resolver the visitor runs.
- `runLayerStates(observation, phases)` keeps its two-argument signature. The
  estate reaches the resolver through `useEstate()` rather than a third
  parameter, because the gate lifts that block and calls it with two arguments,
  and a third would have left the gate running code the browser does not.
- A reference that resolves to nothing cannot arrive from the generator — both
  ends of every id come from one read of `assets/topology-groups.json` — and the
  build refuses one anyway, by name, exercised on purpose.
- The five verbs are a vocabulary that will want extending. `adopts` is the
  obvious candidate the moment the orphan sweep gets a node. Adding one is a
  line in the generator and a sentence here; inventing one at a call site is a
  red build, which is the point.
- No AWS cost, no cycle. The published page changes, so the next push
  republishes it.
