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
documents through the same code, at the rows' own tile size — the marks do
not shrink; a picture that does not fit scrolls. The rows stay as the
compact view and the diagram is a way of laying the same tiles out — the
visitor switches layout, never truth. *Amended 2026-09-14, after the owner
saw the first picture (two boards side by side, five lanes, every edge):*
one environment at a time, read left to right the way a request travels —
edge, runtime, data — with the VPC drawn as the box everything sits in and
the cluster as a second box inside the runtime column, the ops nouns in a
strip below, outside the VPC.

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
and the chart, not typed. ECS and EKS are drawn by the same rules in the
same three columns, one environment at a time, so a switch from stage to
the lab reads as one architecture with two insides.

**D4. Layers, not objects.** The visitor switches layers, never single
tiles: a toggle per object is a puzzle, a toggle per concern is a question
answered. *Amended 2026-09-14:* the layers are the generator's list, with a
default each — **traffic** (the balancer's rule to the tasks, the Ingress to
the Service to the pods) and **data** (who reads the database and the
secret, who publishes to and consumes from each queue) on; **identity** (the
policies and the IRSA roles), **network** (VPC, subnets, security groups,
the target group's registration, the DNS alias) and **ops** (the log
groups) off. A layer off draws none of its edges and hides the nouns that
are its alone — the lab's two IRSA-role groups — rather than dimming them:
a dimmed tile still takes its room. Lanes (network, edge, runtime, data,
ops) and an order within each are the generator's numbers; the page turns
them into columns and boxes and never decides what connects to what.

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
- **Redrawn 2026-09-14, the same night.** The owner's verdict on the first
  picture — *мелко, громозда, ничего не понятно, стало хуже чем просто в
  ряд* — was right: two boards in half the width, tiles carrying the rows'
  block counts and verbs, 54 edges of which half said "it is in the VPC".
  A mock was drawn first and agreed (*давай вариант 1, сначала макет*; the
  marks never smaller, scroll rather than shrink), then the render: one
  environment, the VPC as a frame, edge → runtime → data, the cluster as a
  frame with its pods as tiles and its hooks as a strip, the ops nouns
  outside, 8 of 33 edges drawn by default on stage and 11 of 25 on the lab.
  The generator names the environment variables a service is given as data
  edges (`ITEMS_QUEUE_URL` → the items queue), which the first graph lacked
  for ECS, and gives every part a place. The gate's claims follow the new
  geometry — one board per environment, a layer switched on adds its edges
  and its nouns and moves nothing else — and hold on both states; the
  contrast contract's schema ancestry is the frame's columns.
- **Verified by cycle #32 (34796443184, 2026-09-14, 67 minutes, every job
  green - launch 20 m, lab 20 m, promote 16 m, destroy 12 m, destroy-lab
  13 m, hold 5 m, destroy-prod 12 m)**: the `next` page rendered over the
  live bucket while stage and then the lab were up drew the picture from
  real observations - stage's three services at 1/1 running behind the
  balancer's rule, both queues empty with the alarm OK, the cluster at 15 m
  59 s with its control plane active, two spot t3.small nodes and the three
  Deployments at 1/1 ready, the Ingress active, the parts' words the rows'
  words. Three status files say `destroyed` and name #32. Two things the
  owner's screen said meanwhile, neither this record's: the anonymous
  GitHub budget is shared per IP with the zero-trust-lab dashboard (a
  decision taken - the run history will be published to the bucket by the
  cycle itself, after this phase), and prod's public name answered blank
  for the first minute after `up` (negative DNS caching and target
  registration, which the panel already says).
- **Tried and reverted the same hour, 2026-09-14.** The owner, on the live
  picture with every layer on: the tiles cover the lines and the arrows
  lose their direction. An orthogonal routing was drawn - tiles in columns,
  lines through corridors between the columns, an arrow half-way along each
  run - and the owner's verdict was immediate: *гораздо хуже, верни
  обратно*. Reverted; the curved lines under the tiles stand, and the
  complaint stands with them, to be answered another way. What did stay
  from the same pass: the database said as such - the rds module's admitted
  security groups drawn from the client to the database on the data layer,
  the credentials edge at Secrets Manager, and in the lab the Deployments
  holding `DATABASE_URL` connecting themselves.
- What to watch: the generator reads Terraform by regular expression, not
  by parsing HCL; a module argument split over lines in a way the pattern
  does not expect would drop an edge silently rather than refuse. The gate
  catches the drift of the file, not the blindness of the reader — an
  edge-count floor per environment is the cheap guard if that ever bites.
- The picture's translucency (tiles at 70%, absent at 45%, mid-line arrows)
  was left to the owner's eye for a few days on 2026-09-14; on 2026-09-15
  the word was *leave as is for now*. It stands, and stays open to a later
  verdict.
