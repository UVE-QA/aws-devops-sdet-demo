# ADR-0096: A queue and a worker

## Status
Accepted (Phase 42, 2026-09-13). Item 2 of the plan in **ADR-0094**. Builds on
**ADR-0095**'s per-service module and three-way release; takes on a debt that
plan item 4 pays. Does not touch ADR-0006 (no NAT), ADR-0005 (no plaintext
secrets) or ADR-0025's suite split.

## Context

Two services behind one load balancer, routed by path, is a boundary — and
still a synchronous one: every request the interface makes is answered before
it returns. The plan's second step adds the seam every interview asks about
and every home project skips: a message published by one service and consumed
by another, later, with the failure modes that come with *later* — a message
delivered twice, a message that can never be processed, a consumer that is
down when the message arrives.

The application is deliberately boring so that the machinery around it can be
the subject. The worker is boring on purpose too; what it produces is a fact
the client can observe through the api, and that fact is the whole test.

The owner's decisions, taken before a line was written:

> processed_at ок, прямая публикация с дырой, alarm без action, ElasticMQ ок

## Decision

**D1. The event is `item.created`, and the worker's mark is on the api's
row.** `POST /api/items` publishes `{type, version, item: {id, name,
created_at}, request_id}` after the commit; the worker consumes it and stamps
`processed_at` and `processed_by` on `demo_items`. The api never writes those
two columns and the worker writes nothing else. A client sees the seam as two
nulls turning into values some time after the 201, and the contract suite
waits for exactly that — a deadline, never a sleep — so a worker that is down,
a queue nobody configured or a publish that was lost all fail the same test.
The worker writing the api's table is a shared database, and it is the debt
plan item 4 is for: taken knowingly, so that this step's story is the
asynchronous seam and that one's is data ownership.

**D2. Direct publish after the commit, and the gap is named.** The row is
committed first and the event sent second, with no transaction across them. A
process that dies between the two, or a queue that refuses the send, leaves an
item that exists and an event that never went — the item then stays
unprocessed for ever, and D1's test is what makes that visible. The
transactional outbox that closes the gap is a second process (a relay) for a
gap this project can currently see and measure; it arrives with item 4, where
the worker stops writing this table and the relay has a home. A failed send
does nothing to the response: the item was created and 201 is the truth about
that; the failure is logged at error level with the item id, and the client
is bounded to three seconds of waiting on a dead queue (2 s connect, 3 s read,
one retry).

**D3. At-least-once, idempotent by construction, poison left for the
dead-letter queue.** A standard queue, not FIFO: ordering is nothing here needs
and a FIFO's throughput ceiling and name suffix are a price for it. The
worker's one statement is `UPDATE … WHERE id = ? AND processed_at IS NULL`, so
a second delivery updates nothing and is deleted like a first. A message the
worker can never act on — not JSON, the wrong type, the wrong version, no
positive integer id — is *poison*: logged with the reason and **left**, so the
queue's redrive policy carries it to the dead-letter queue after three
receipts. Deleting poison would make a dead-letter queue that can never fill
and an alarm that can never fire. A transient failure (the database away) is
left too, for the opposite reason: the next delivery may succeed.

**D4. The alarm has no action.** `ApproximateNumberOfMessagesVisible ≥ 1` on
the dead-letter queue, one minute, no `alarm_actions`: there is nobody to page,
and an action bound to nothing would be the appearance of one. Its state is
what `observe-environment.sh` reads and the environment panel prints, beside
the queue's depth and the dead-letter queue's — the same rule as every other
noun on the page: observed in AWS, not inferred from a green run.

**D5. The worker is the third service of the same module, behind nothing.**
`modules/ecs-service` learned a service with no port: no ingress rule, no
target group, no `load_balancer` block, and a health check on a heartbeat file
the loop touches on every pass — a process that is up and stuck is what that
tells apart from one that is up and working. The worker refuses to start
without a queue URL and a database URL: a worker with nothing to consume or
nowhere to write is a process that exists to make `describe-services` say
ACTIVE. Its own image, its own dependencies, none of the api's code — the two
share a message contract and, for now, a table.

**D6. The task roles get their first real permissions, one each.** The api's
task role may `SendMessage` to the one queue; the worker's may
`ReceiveMessage`, `DeleteMessage`, `GetQueueAttributes` and
`ChangeMessageVisibility` on the same one. Nothing on `*`, and neither may do
the other's half. The worker's execution role reads the database secret the
way the api's does, by a second policy named for the worker; RDS admits the
worker's security group beside the api's, by group and never by CIDR. The
deploy role names six ECS roles now, and `sqs:*` beside `ecs:*`.

**D7. A release is three digests.** The pointer becomes `{api, web, worker}`,
written in one put; a pointer holding two names is the shape ADR-0095 wrote
and is reported *not armed* — a set missing one is not the set — exactly as a
bare digest was. The release tag goes into three registries; the worker's
repository, `aws-devops-sdet-demo-worker`, joins the permanent level.

**D8. ElasticMQ stands in for SQS on the devbox, and the code has no local
branch.** Compose runs `softwaremill/elasticmq-native` with the same two queues
and the same redrive `worker/local/elasticmq.conf` declares; the api and the
worker are pointed at it by `SQS_ENDPOINT_URL` and nothing else changes. The
visibility timeout is 5 s there and 30 s in AWS, deliberately: the poison
break test waits for three receipts, and ninety seconds is a test nobody runs.
`scripts/break-poison-message.sh` sends one body that is not an event and
refuses unless it reaches the dead-letter queue, leaves the main queue, and is
refused by the worker exactly three times — counted by message id, because the
log carries every earlier run too.

**D9. The board draws the queue as one tile and the worker as a third
service.** *SQS + dead-letter queue* holds the queue, its dead-letter queue and
the alarm — three resources that exist for one reason; *ECS — worker* sits
beside api and web; the `Build` phase gains a third node. The greyed plan
tiles for web, api, the queue and the worker leave the band: a tile leaves the
day the board draws the thing, which ADR-0095 should have done and did not.
The environment panel gains a `worker service` row and a `queue` row.

## Consequences

- Locally: 54 api contract tests (52 + 2 asynchronous), the poison path
  exercised end to end, 126 unit tests including every branch of the worker's
  parser and the api's own message builder run through it, three images
  scanning with nothing fixable. Two whole-row comparisons in the contract
  suite raced the worker's stamp on the first run and now compare the fields
  the api owns — the suite's first lesson in eventual consistency.
- `scripts/queue.py` was renamed `sqs_tool.py` on its first run: a script
  named `queue.py` shadows the standard library's `queue` for urllib3
  underneath boto3.
- SQS queues have no kind in their ARN; `scripts/arns.py` names it `queue`,
  the sweep confirms one by `get-queue-url`, and the adoption imports one by
  its URL. The dead-letter alarm is reported by the sweep and not adopted,
  exactly as the 5xx alarm always was.
- The estate is 163 resource blocks, 86 per cycle; the cycle grows by a
  third build, a third service's stability and one Fargate task's worth of
  cost; the queue itself bills per million requests and a cycle makes a few
  hundred.
- Three lists now know the services by name — the module instances,
  `adopt_orphans.py`, the deploy role — and a fourth in every workflow. Plan
  item 5 is where they meet.
- Not covered: the `being torn down` tense for the worker follows ADR-0086's
  rule like every other noun; the outbox is item 4's; a second worker would
  need nothing here changed and is not run, because one is what the story
  needs.
- **Not yet verified by a cycle.** The worker's repository and the deploy
  role's six names are permanent levels applied by hand under `demo-admin`
  with the owner's word; the first cycle from `next` is the proof.
