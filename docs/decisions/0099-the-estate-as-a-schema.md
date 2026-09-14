# ADR-0099: The estate as a schema

## Status
Accepted (Phase 45, 2026-09-14), in slices; each slice's verification is
recorded under Consequences as it happens. Item 5 of the plan in **ADR-0094**,
placed before the manifest (item 6) on the owner's word. Builds on the board
of **ADR-0075** (the estate as observed tiles, going dark one noun at a time
by **ADR-0090**) and on the generated topology of **ADR-0040** and
**ADR-0052**; draws the lab's inside that **ADR-0097** put beyond
Terraform's sight.

## Context

The estate board is honest and flat. Every tile is an observed fact — the
noun, its state, its figures — but the board does not say what connects to
what: that the api's tasks stand behind a target group the balancer's rule
names, that the worker's role may consume one queue and publish to another,
that a pod on the lab reads its password from the same secret the RDS module
wrote. The owner asked first for a static picture of the lab's inside —
*ноды, поды и тд* — then for the same beside ECS, and then for the question
the two pictures raise together:

> может тогда имеет смысл эту схему делать сразу в эстейтс с интерактивным
> включением/выключением объектов? вместо последовательного ряда сервисов

A separate diagram would be a third opinion beside the board and the
topology, drawn by hand and stale by the next module change. The decision is
the opposite: the board gets a second layout, and the layout's graph is
generated from what the repository already declares, gated like the
topology, so a picture that lies is a red check and not a recruiter's
question.

## Decision

**D1. A second layout of the one board, not a second board.** The diagram's
nodes are the board's own nouns, by the same ids as `site/data/topology.json`;
their states, colours and figures are the board's, read from the same status
documents through the same code. The rows stay as the compact view and the
diagram is a way of laying the same tiles out — the visitor switches layout,
never truth.

**D2. Edges are generated, never drawn.** `scripts/generate-schema.py`
writes `site/data/schema.json` from three sources and nothing else: the
modules' inputs in `infra/envs/*` (a `module.alb.…` reference inside
`module "api"` is an edge api → alb, named by the argument), the IAM policies
whose role is one module's and whose resources another's — at the
environment level for ECS, in the eks module's IRSA file for the lab — and
`helm template` over the chart for the lab's inside: Ingress path → Service,
Service selector → Deployment, ServiceAccount → the IRSA role its annotation
names, `secretKeyRef` → the secret, `*_QUEUE_URL` → the queue. Every edge
carries the file and line it was read from. An edge without a source is a
refusal.

**D3. A finer grain inside the runtimes, observed like everything else.**
Parts under a noun: the tasks of each ECS service, the target groups behind
the balancer, the lab's control plane, node group, pods, Services, Ingress
and hooks, the two queues under the one tile. Each part names the path in
`status/<env>.json` it is coloured from — running against desired, ready
against desired, the queue's alarm — so the diagram's inside is as live as
its outside. A part nothing observes on its own — a Service, a hook, a
target group — is drawn dashed and says *declared*, never coloured on the
strength of the Deployment beside it; the parts are drawn from the module
and the chart, not typed. ECS and EKS are drawn
side by side by the same rules, so the two runtimes read as one architecture
with two insides.

**D4. Layers, not objects.** The visitor switches layers — runtime,
identity, data, network — never single tiles: a toggle per object is a
puzzle, a toggle per concern is a question answered. Layout is lanes
(network, edge, runtime, data, ops) and an order within each, as numbers the
generator assigns; the page turns numbers into pixels and never decides what
connects to what.

**D5. Before the manifest.** The renderer takes a graph. Today the graph's
source is the modules and the chart; when the services manifest (item 6)
exists it becomes the source of the same graph, and the page does not
change. The order is the owner's: *согласен, так и делаем*.

**D6. Gated like the topology.** `make schema` writes the file, `make
schema-check` regenerates and refuses on drift; it stands beside
`chart-check` in the gates registry and in CI, and like it needs helm and
says so rather than passing without the chart's half.

## Consequences

- Slice 5a, written 2026-09-14: the generator and the graph — stage 10
  nouns, 7 parts, 29 edges; prod 11, 7, 29; lab 7 nouns, 13 parts, 24 edges
  — 49 input edges, 16 policy edges, 9 network, 6 data, 2 identity across
  the three. The gate refuses a dropped edge (proven by dropping one). The
  page does not read the file yet.
- Slice 5b, written 2026-09-14: the board's `layout` switch - rows, the
  default and the compact view, or schema: one grid, a row per lane, the
  chosen ECS environment beside the lab so VPC sits beside VPC and the tasks
  beside the pods. The tiles are the rows' own elements from the same
  function; the parts inside a runtime tile are coloured from the counts the
  dashboard hands the map verbatim; the edges are drawn over the grid once
  the browser has laid it out, each leaving a tile through a port of its own
  in the colour of its layer, the argument and the source line on hover.
  Four layer switches dim a layer's tiles and hide its edges and remove
  nothing. The generator gives every noun, part and edge a layer, reads a
  level's own resources (prod's Route 53 record → the balancer) and names a
  Helm value by its `set` name: stage 29 edges, prod 31, lab 25. Proven
  locally over synthetic observations in both themes and stacked below
  1180px; a schema that fails to load leaves the rows as they are and the
  switch hidden.
- Slice 5c, written 2026-09-14: `tests/fixtures/page-schema/` with both
  runtimes up and a count in every part class, plus a `stale` state;
  `scripts/check-page-schema.mjs` holds the picture to the rows on seven
  claims (same ids and words in the schema's lanes; every part and edge,
  once, with a source; the counts as the documents say; a destroyed
  environment with none; a layer off dims and hides and removes nothing;
  the rows come back alone; a stale reading is grey). Its first run found
  two things: a part inside a tile no cycle had measured was dashed on the
  strength of the noun's missing record, over a count the bucket had taken
  - gone, the part says what the bucket says; and the claim mistook an
  absent tile's own dimming for the switch's. The contrast contract carries
  the three part states on the chip's own background and the schema grid as
  a fourth ancestry: 4.26:1 at worst, both themes. `page-schema-check`
  stands beside `page-inflight-check` in CI.
- Not yet: a cycle from `next` with the layout live over real observations
  (the merge rule of ADR-0093 D1), and the picture's routing - an edge from
  the runtime lane to the VPC crosses the balancer's tile on its way, which
  is legible and not pretty; a routed layout is a later slice if the owner
  wants one.
- What to watch: the generator reads Terraform by regular expression, not
  by parsing HCL; a module argument split over lines in a way the pattern
  does not expect would drop an edge silently rather than refuse. The gate
  catches the drift of the file, not the blindness of the reader — an
  edge-count floor per environment is the cheap guard if that ever bites.
