# Phase 45 — The estate as a schema

**2026-09-14**, the night after the four phases of the 13th, on `next`.
**ADR-0099**, one record, six decisions, three slices, one gate — and no
cycle yet: the code is on `next`, the merge waits for the owner's word and a
green cycle, as ADR-0093 D1 has it.

Item 5 of the plan, decided the evening before in three lines of the owner's:
a static picture of the lab's inside — *ноды, поды и тд* — then the same
beside ECS, then the question whether that picture should not simply be the
estate board with things switched on and off, instead of a row of services.
*согласен, так и делаем.*

## What was decided

One board with a second layout, not a second board: the diagram's nodes are
the board's own nouns, by the same ids, carrying the same words through the
same code, and the rows stay as the compact view. Edges generated and never
drawn — the modules' inputs, the IAM policies at the environment level and
in the eks module's IRSA file, the balancer's listener rule, `helm template`
over the chart — every one with the file and line it was read from. A finer
grain inside the runtimes, observed like the nouns: tasks against desired,
pods against desired, a queue's depth and its alarm, each part naming the
path in the status document it is coloured from; a part nothing observes on
its own says *declared* and is dashed. Layers, never objects: network,
runtime, data, identity. Before the manifest, because the renderer takes a
graph. Gated like the topology.

## Slice 5a — the graph

`scripts/generate-schema.py` writes `site/data/schema.json`: per environment
the nouns with a lane and an order, the parts with their observation paths,
the edges with their sources. It refuses an edge without a source, a part
hanging off nothing, a noun without a lane. `make schema-check` regenerates
and refuses drift — proven by dropping one edge — and stands beside
`chart-check` in the gates and in CI, needing helm for the chart's half and
saying so.

## Slice 5b — the picture

The board's `layout` switch. One grid, a row per lane, the chosen ECS
environment beside the lab so VPC sits beside VPC and the tasks beside the
pods; the tiles from the same function the rows use; the parts inside each
runtime tile coloured from the counts the dashboard now hands the map
verbatim; the edges drawn over the grid once the browser has laid it out,
each leaving a tile through a port of its own — eleven edges into the VPC's
bottom centre are one line, eleven ports along its bottom are eleven — in the
colour of its layer, the argument and the source line on hover. Four layer
switches dim a layer's tiles and hide its edges and remove nothing. Proven
locally over synthetic observations, both themes, stacked below 1180px. The
generator learned three things on the way: a layer for every noun, part and
edge; a level's own resources as edges (prod's Route 53 record → the
balancer); a Helm value named by its `set` name rather than the word `value`.

## Slice 5c — the gate

`tests/fixtures/page-schema/` holds both runtimes up with a count in every
part class — stage's worker at 0/1, a dead letter on its results queue, the
lab's worker pod at 0/1 — and a `stale` state where the lab's document was
written by an older run. `scripts/check-page-schema.mjs` renders the built
page over it, switches the board and holds the picture to the rows on seven
claims. Its first run found two things, which is what a first run is for: a
part inside a tile no cycle had measured was dashed on the strength of the
noun's missing record, over a count the bucket had actually taken — the
rule is gone, the part says what the bucket says; and the claim mistook an
absent tile's own dimming for the switch's — it compares each tile with
itself now. The contrast contract carries the three part states on the
chip's own background and the schema grid as a fourth ancestry: 4.26:1 at
worst, both themes.

## Figures

```text
schema   stage 10 nouns / 7 parts / 29 edges   prod 11 / 7 / 31   lab 7 / 13 / 25
gate     2 states, 17 tiles, 20 parts, 54 edges in the picture, every claim holds
gates    13/13 locally, 36 in the registry; contrast 10 states, 4 ancestries
```

## What is still open

A cycle from `next`, on the owner's word — the first look at the picture
over real observations, and the condition for the merge. The picture's
routing: an edge from the runtime lane to the VPC crosses the balancer's
tile on its way, legible and not pretty; a routed layout is a later slice
if wanted. The services manifest after it (item 6), which becomes the
graph's source without the page changing. Per-service database users
(ADR-0098 D2). The Cycle map for a `next` cycle, on the owner's condition.
From before: the lab site, the two blunted break tests, the release-tag 403.
