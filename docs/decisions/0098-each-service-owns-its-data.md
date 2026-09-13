# ADR-0098: Each service owns its data

## Status
Accepted (Phase 44, 2026-09-13), in slices; each slice's verification is
recorded under Consequences as it happens. Item 4 of the plan in **ADR-0094**.
Pays the debt **ADR-0096 D1** took (the worker writing the api's table) and
closes the gap **ADR-0096 D2** named (the publish after the commit). Does not
touch the API contract a client sees.

## Context

Two services, two containers, one seam — and one table. The worker stamped
`processed_at` on the api's `demo_items`, which made the queue an
optimisation rather than a boundary: either service could have read the
other's rows, and the fact that neither did was a habit. The plan's fourth
step is the sentence *microservices is a statement about data, not about the
number of containers*, and this record is that sentence made true in the
smallest way that is still true.

The owner's decisions, taken before a line was written:

> по всем пунктам как рекомендуешь, одна плитка

on: the projection through a second queue rather than a read of the other
service's schema; ownership by schema now and by database user later; the
outbox with its relay inside the api's process; contracts as JSON Schema
held by unit tests on both sides; one tile for both queues.

## Decision

**D1. The worker owns what it did; the api owns what the client sees.** The
worker gets a schema, `worker`, with one table, `receipts` — one row per
item, first delivery wins, no foreign key to the api's table: an item's
existence is the api's fact and a receipt for an item the api has since
deleted is a true statement about what the worker did. The api's
`demo_items` loses the two columns revision 0004 lent to the worker and
gains `item_processing`, a projection the api writes when it hears what the
worker reported. The client's `processed_at` and `processed_by` come from
that projection through the same two fields of the same response: the API
contract did not move, the ownership did, and the 54 contract tests did not
change.

**D2. They meet only through the queues, in both directions.** The worker
publishes `item.processed` to a second queue, `results`, with its own
dead-letter queue and alarm from the same module; the api consumes it. No
service reads another's schema, and the `worker` schema is the only thing in
the database the api's migrations do not know. Ownership is by schema and by
code today; by database user — one role per service with rights on its own
schema alone — is the next hardening and is named, not taken: a second
secret, roles created by a master migration, and two more places for the
task roles and IRSA to change.

**D3. The outbox closes the gap.** `item.created` is written into `outbox`
in the same transaction as the item it is about, and a relay — a thread of
the api's own process, started and stopped with the application — sends
what is unpublished, oldest first, twenty at a time, `FOR UPDATE SKIP
LOCKED` so two replicas never wait on each other. A send that fails leaves
the row with the attempt counted; a process that dies between the send and
the mark sends the row again. At-least-once, said so, and what the worker's
receipt is written against. What was a gap is a delay of about a second.

**D4. The worker's message is its outbox.** The receipt and the report are
two writes to two systems, and the worker does not need a table to bridge
them: it deletes the message only after the report is sent, so a worker that
dies in between finds its receipt on the next delivery — first delivery
wins — and reports again from it, with the original time and name. The api
records a report once (`ON CONFLICT DO NOTHING`), and a report about an item
it has since deleted meets the foreign key and is dropped as *gone*, which
is not an error.

**D5. The contracts are files, and both ends are held to them.**
`contracts/item.created.v1.json` and `contracts/item.processed.v1.json` are
JSON Schema with the schema's own examples and counter-examples. Neither
service validates against them at runtime — the parsers are strict by hand,
and a runtime dependency would be a third thing to keep in step — but
`tests/unit/test_contracts.py` validates every builder's output against its
schema, runs every parser over the schema's examples and requires it to
refuse every counter-example as poison, and checks that the counter-examples
are the schema's and not merely the parser's. A producer that changes a
meaning bumps `version` and breaks here, in process, in a second.

**D6. Each service migrates its own history.** The worker gets its own
Alembic — `worker/alembic`, a version table inside its own schema — run by
its own image as a one-off task on ECS and a Helm hook on the lab, exactly
as the api's is. Two services migrating one database is two histories, not
one, and the api's `alembic_version` and the worker's never see each other.

**D7. One tile.** *SQS + dead-letter queue* becomes the seam in both
directions — two queues, two dead-letter queues, two alarms — as the owner
chose: a second tile would draw a fact about count where the board draws
facts about reasons.

## Consequences

- Slice one, locally, 2026-09-13: the api's migration 0005 and the worker's
  0001 applied; the relay and the consumer up in the api's process; 54
  contract tests green through the projection with no change to a test; 31
  items created by the suite, 31 outbox rows published with none left, 31
  worker receipts and reports, the api recording two and dropping the rest
  as *gone* because the suite deletes what it makes; the poison path still
  green on the items queue; 143 unit tests, twelve of them the contracts and
  the relay's branches.
- One thing the first run found beside the seam: nginx resolves `app` once,
  at startup, so recreating the api container turned every request through
  the local web container into a 502 until nginx was restarted. The local
  proxy include resolves per request now.
- Slice two, written 2026-09-13: the queue module takes a name and is
  instantiated twice in every environment; the api's and the worker's task
  roles and IRSA roles each gain the mirror permission on `results`; both
  services carry both URLs on ECS and in the chart; the worker's migration
  runs as a one-off task from the worker's task definition in every
  workflow that provisions a database, and as a Helm hook on the lab; the
  observation reads both queues; the adoption map knows the second pair; the
  board's one tile is *SQS — items and results* and the panel shows both.
  Validated on nine levels, checkov 544/0, the chart renders eleven objects.
  **A cycle from `next` is the proof.**
