# Phase 44 — Each service owns its data

**2026-09-13**, the same session, its fourth phase.
**ADR-0098**, one record, seven decisions, two slices, one cycle — and three
things the owner's screen said while it ran.

Item 4 of the plan, the sentence *microservices is a statement about data,
not about the number of containers*, made true in the smallest way that is
still true: the worker stops writing the api's table, the two services meet
only through queues, in both directions, and the contract between them is a
file both are held to.

## What was decided

The owner's line — *по всем пунктам как рекомендуешь, одна плитка* — settled
four things. The projection through a second queue rather than a read of
the other service's schema: the worker publishes `item.processed` to
`results`, the api consumes it into `item_processing`, and the client's two
fields come from there through the same response, so the 54 contract tests
did not change. Ownership by schema now — `worker.receipts`, the worker's own
Alembic with its version table inside its own schema — and by database user
later, named and not taken. The outbox with its relay inside the api's
process, `FOR UPDATE SKIP LOCKED`, at-least-once and said so; the worker's
message as its own outbox, deleted only after the report is sent. Contracts
as JSON Schema with the schema's own examples and counter-examples, both
builders validated, both parsers run over them. One tile for both queues.

## Slice one, locally

The api's migration 0005 and the worker's 0001; the relay and the results
consumer as threads of the api; 54 contract tests green through the
projection; the suite's 31 items became 31 outbox rows published with none
left, 31 receipts and reports, the api recording two and dropping the rest
as *gone* because the suite deletes what it makes; the poison path green;
143 unit tests, twelve of them the contracts and the relay's branches. One
thing beside the seam: nginx resolves `app` once at startup, so recreating
the api container turned every request through the local web container into
a 502 — the local proxy resolves per request now.

## Slice two, in AWS

The queue module named and instantiated twice in every environment; the
mirror permissions on both task roles and both IRSA roles, nothing on `*`;
both URLs on ECS and in the chart; the worker's migration as a one-off task
from its own task definition in three workflows and as a Helm hook on the
lab; both queues observed, adopted and drawn on the one tile *SQS — items
and results*. Validated on nine levels, checkov 544/0, the chart eleven
objects.

## The cycle

```text
#31  34787213122  22:34  success   68 m — launch 20, lab 20 (spot), promote 16,
                                   destroy 12, destroy-lab 14, hold 5,
                                   destroy-prod 11, release-lock
```

The seam in both directions on ECS and on EKS; the worker's migration on
every runtime; the async suite through the projection in all three
environments; both queue pairs swept clean; and, from the evening before,
the lab's nodes as spot — `capacity_type = "SPOT"` in the apply stream, the
apply in 921 s, no slower than on-demand.

## What the owner's screen said

Three things, each fixed and gated before the cycle ended. **The anonymous
GitHub budget ran out**: two list requests per poll had left no headroom, and
the tab read *Run history unavailable — HTTP 403*; the released line's own
list is read once per ten minutes now and merged with each poll's `main`
runs. **The button stood open with no run history**: it closes on the
bucket's pulse — the watcher's progress document, younger than three minutes
— and when GitHub cannot be read it closes and says so; a `blind` fixture
state answers 403 to everything and holds it closed. **The lab panel's
*latest published* report was an S3 AccessDenied**: the lab job published no
report directory, and the page linked a `latest` that had never existed;
both self-service publishes pass the report now, the publisher asks the
bucket by listing whether a `latest` is there, and the page links only what
is.

Also decided on the way: the estate as a schema is plan item 5 — a second
layout of the board with edges and a finer grain inside each runtime, tasks
and pods side by side, layers to switch rather than objects — before the
manifest, because the renderer takes a graph whose source can change. The
built items and their tiles left the plan band, which ADR-0095 and ADR-0096
should have done in their day.

## The merge

`main` fast-forwarded to `next` on the owner's *да, вливай*: nine commits,
Phase 44, the spot nodes, three page fixes. The estate is 216 resource
blocks across nine levels; the suites count 213 tests; the plan band holds
two items.

## What is still open

The estate as a schema, next. The services manifest after it, with five
lists of service names to reconcile. Per-service database users, named in
ADR-0098 D2. The Cycle map for a `next` cycle, on the owner's condition.
From before: the lab site, the two blunted break tests, the release-tag 403.
